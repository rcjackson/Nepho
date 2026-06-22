"""Data quality (DQ) pipeline for ARM datastream quicklook images.

Given a datastream name and a date window, this iterates over each day, fetches
that day's quicklook PNGs, sends them all in a single batched call to every
available model (via :class:`chatbot.ParallelChatbot`), and parses each model's
free-text response into a structured DQ verdict.
"""

import asyncio
import json
import os
import shutil
import tempfile
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any, Dict, List, Optional

import aiohttp

from chatbot import ParallelChatbot
from config import config
from datastream import Datastream, build_quicklook_url, parse_datastream
from quicklook_fetcher import cached_pngs, download_pngs, list_day_pngs

_VALID_SEVERITIES = {"Good", "Indeterminate", "Bad"}
# Lowercase lookup -> canonical capitalized severity, so model responses are
# matched case-insensitively but always reported in canonical form.
_SEVERITY_BY_LOWER = {s.lower(): s for s in _VALID_SEVERITIES}


@dataclass
class DQVerdict:
    """A single model's data quality verdict for one day."""

    model_name: str
    day: str
    issues_found: Optional[bool]  # None => response could not be parsed as JSON
    severity: Optional[str]
    summary: str
    issues: List[str]
    raw_response: str
    response_time: float
    error: Optional[str] = None


@dataclass
class DayResult:
    """The DQ results for a single day across all models."""

    day: str
    image_count: int
    image_urls: List[str]
    verdicts: List[DQVerdict] = field(default_factory=list)
    skipped: bool = False
    note: Optional[str] = None
    # True when the day was skipped because the existence check failed (network,
    # timeout, etc.), as opposed to a confirmed absence of images.
    fetch_error: bool = False
    # True when this day's images were served from the local picture cache rather
    # than downloaded fresh.
    from_cache: bool = False


@dataclass
class DQReport:
    """The full DQ report for a datastream over a date window."""

    datastream: str
    start: str
    end: str
    models: List[str]
    days: List[DayResult] = field(default_factory=list)


def build_dq_prompt(ds: Datastream, day: date, image_count: int) -> str:
    """Build the DQ prompt for a day's batch of quicklook images."""
    return config.DQ_DEFAULT_PROMPT.format(
        datastream=ds.raw,
        day=day.strftime("%Y-%m-%d"),
        count=image_count,
    )


def parse_dq_response(text: str) -> Dict[str, Any]:
    """Parse a model's free-text response into a structured DQ dict.

    Attempts to extract and decode a JSON object. On any failure, falls back to
    a dict with ``issues_found=None`` and the raw text as the summary.

    Args:
        text: The raw model response.

    Returns:
        A dict with keys ``issues_found``, ``severity``, ``summary``, ``issues``.
    """
    fallback = {
        "issues_found": None,
        "severity": None,
        "summary": (text or "").strip(),
        "issues": [],
    }

    if not text:
        return fallback

    stripped = text.strip()

    # Strip a leading/trailing markdown code fence if present.
    if stripped.startswith("```"):
        stripped = stripped[3:]
        if stripped.lower().startswith("json"):
            stripped = stripped[4:]
        if stripped.endswith("```"):
            stripped = stripped[:-3]
        stripped = stripped.strip()

    # Brace-scan from the first '{' to its matching '}'.
    start = stripped.find("{")
    if start == -1:
        return fallback

    depth = 0
    end = -1
    for i in range(start, len(stripped)):
        char = stripped[i]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                end = i
                break

    if end == -1:
        return fallback

    try:
        parsed = json.loads(stripped[start : end + 1])
    except (ValueError, TypeError):
        return fallback

    if not isinstance(parsed, dict):
        return fallback

    issues_found = parsed.get("issues_found")
    if not isinstance(issues_found, bool):
        issues_found = None

    severity = parsed.get("severity")
    if isinstance(severity, str):
        severity = _SEVERITY_BY_LOWER.get(severity.strip().lower())
    else:
        severity = None

    summary = parsed.get("summary")
    summary = summary.strip() if isinstance(summary, str) else fallback["summary"]

    issues = parsed.get("issues")
    if isinstance(issues, list):
        issues = [str(item) for item in issues]
    else:
        issues = []

    return {
        "issues_found": issues_found,
        "severity": severity,
        "summary": summary,
        "issues": issues,
    }


class DataQualityPipeline:
    """Orchestrates DQ analysis of a datastream's quicklook images."""

    def __init__(
        self,
        chatbot: ParallelChatbot,
        datastream: str,
        model_names: Optional[List[str]] = None,
        max_images: Optional[int] = None,
        cache_dir: Optional[str] = None,
        refresh_cache: bool = False,
    ):
        self.chatbot = chatbot
        self.datastream = parse_datastream(datastream)
        self.model_names = model_names
        self.max_images = (
            max_images if max_images is not None else config.DQ_MAX_IMAGES_PER_DAY
        )
        # When ``cache_dir`` is set, downloaded images persist there (keyed by
        # datastream + day) and are reused on later runs. ``refresh_cache`` forces
        # a re-download even when a cache hit is available.
        self.cache_dir = cache_dir
        self.refresh_cache = refresh_cache

    async def run(self, start: date, end: date) -> DQReport:
        """Run the DQ pipeline over the inclusive date window ``[start, end]``."""
        report = DQReport(
            datastream=self.datastream.raw,
            start=start.strftime("%Y-%m-%d"),
            end=end.strftime("%Y-%m-%d"),
            models=self.chatbot.list_models(),
        )

        # When caching, images live under the persistent cache dir (never wiped).
        # Otherwise use an ephemeral temp dir removed at the end of the run.
        if self.cache_dir is not None:
            image_root = self.cache_dir
            cleanup_root = False
        else:
            image_root = tempfile.mkdtemp(prefix="nepho_dq_", dir=config.DQ_TEMP_DIR)
            cleanup_root = True

        timeout = aiohttp.ClientTimeout(total=config.REQUEST_TIMEOUT)
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                day = start
                while day <= end:
                    result = await self._run_day(session, image_root, day)
                    report.days.append(result)
                    day += timedelta(days=1)
        finally:
            if cleanup_root:
                shutil.rmtree(image_root, ignore_errors=True)

        return report

    def _day_dir(self, image_root: str, day: date) -> str:
        """Return the directory holding ``day``'s images.

        When caching, the path is namespaced by datastream so different
        datastreams sharing the cache root do not collide.
        """
        yyyymmdd = day.strftime("%Y%m%d")
        if self.cache_dir is not None:
            return os.path.join(image_root, self.datastream.raw, yyyymmdd)
        return os.path.join(image_root, yyyymmdd)

    async def _run_day(
        self, session: aiohttp.ClientSession, image_root: str, day: date
    ) -> DayResult:
        """Fetch (or load from cache) and analyze a single day's quicklook images."""
        day_str = day.strftime("%Y-%m-%d")
        day_dir = self._day_dir(image_root, day)

        # Cache hit: reuse previously downloaded images, skipping the network
        # existence check and download entirely. Only positive results (actual
        # images) are cached, so a hit always means at least one image exists.
        from_cache = False
        if self.cache_dir is not None and not self.refresh_cache:
            cached = cached_pngs(day_dir)
            if cached:
                local_paths = cached[: self.max_images]
                from_cache = True
                urls = [build_quicklook_url(self.datastream, day)]

        if not from_cache:
            try:
                urls = await list_day_pngs(session, self.datastream, day)
            except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
                return DayResult(
                    day=day_str,
                    image_count=0,
                    image_urls=[],
                    skipped=True,
                    note=f"Error checking for quicklook images: {exc}",
                    fetch_error=True,
                )

            if not urls:
                return DayResult(
                    day=day_str,
                    image_count=0,
                    image_urls=[],
                    skipped=True,
                    note="No quicklook images found for this day.",
                )

            os.makedirs(day_dir, exist_ok=True)
            local_paths = await download_pngs(
                session, urls, day_dir, max_images=self.max_images
            )

            if not local_paths:
                return DayResult(
                    day=day_str,
                    image_count=0,
                    image_urls=urls,
                    skipped=True,
                    note="Quicklook images were listed but none could be downloaded.",
                )

        prompt = build_dq_prompt(self.datastream, day, len(local_paths))
        responses = await self.chatbot.chat_parallel(
            prompt, local_paths, self.model_names
        )

        verdicts: List[DQVerdict] = []
        for response in responses:
            # ``chat_parallel`` returns a sentinel ChatResponse(model_name="none")
            # when there are no usable models; surface it as an error verdict.
            if response.error is not None:
                verdicts.append(
                    DQVerdict(
                        model_name=response.model_name,
                        day=day_str,
                        issues_found=None,
                        severity=None,
                        summary="",
                        issues=[],
                        raw_response=response.response,
                        response_time=response.response_time,
                        error=response.error,
                    )
                )
                continue

            parsed = parse_dq_response(response.response)
            verdicts.append(
                DQVerdict(
                    model_name=response.model_name,
                    day=day_str,
                    issues_found=parsed["issues_found"],
                    severity=parsed["severity"],
                    summary=parsed["summary"],
                    issues=parsed["issues"],
                    raw_response=response.response,
                    response_time=response.response_time,
                )
            )

        return DayResult(
            day=day_str,
            image_count=len(local_paths),
            image_urls=urls,
            verdicts=verdicts,
            from_cache=from_cache,
        )
