"""Async existence-checking and downloading of ARM quicklook PNG images.

The ARM plot server exposes no usable directory listing, so a day's quicklook PNG
URL is constructed directly (see :func:`datastream.build_quicklook_url`). This
module checks whether that URL exists and downloads the image to a local
directory so the existing image-handling code (``BaseModel.validate_image`` /
``encode_image``) can be reused unchanged.
"""

import asyncio
import os
from datetime import date
from typing import List, Optional
from urllib.parse import unquote, urlparse

import aiohttp

from config import config
from datastream import Datastream, build_quicklook_url


async def list_day_pngs(
    session: aiohttp.ClientSession, ds: Datastream, day: date
) -> List[str]:
    """Return the quicklook PNG URL(s) for a datastream on a given day.

    The expected URL is constructed directly and probed with a HEAD request
    (falling back to GET if HEAD is not supported by the server).

    Args:
        session: An open aiohttp session.
        ds: The parsed datastream.
        day: The day whose quicklook image to check.

    Returns:
        A single-element list containing the PNG URL if it exists, or an empty
        list if the server reports it missing (a non-200 status). An empty list
        means a *confirmed* absence, not a failed check.

    Raises:
        aiohttp.ClientError, asyncio.TimeoutError: if the existence check could
            not be completed (network failure, timeout, etc.). The caller should
            treat this as "unknown" and distinct from a confirmed absence, rather
            than silently reporting "no data for this day".
    """
    url = build_quicklook_url(ds, day)
    async with session.head(url, allow_redirects=True) as response:
        if response.status == 200:
            return [url]
        # Some servers reject HEAD; confirm with a GET before giving up.
        if response.status in (405, 501):
            async with session.get(url) as get_response:
                if get_response.status == 200:
                    return [url]

    return []


def cached_pngs(day_dir: str) -> List[str]:
    """Return sorted local PNG paths already present in ``day_dir``.

    Used by the opt-in per-day picture cache to detect a cache hit: a non-empty
    result means a previous run already downloaded this day's quicklook image(s)
    into ``day_dir`` (see :func:`download_pngs`, which writes ``NNN_<name>.png``).

    Args:
        day_dir: The day's cache directory.

    Returns:
        Sorted local PNG paths in ``day_dir``, or an empty list if the directory
        does not exist or contains no PNGs.
    """
    if not os.path.isdir(day_dir):
        return []
    names = sorted(n for n in os.listdir(day_dir) if n.lower().endswith(".png"))
    return [os.path.join(day_dir, n) for n in names]


def _filename_from_url(url: str) -> str:
    """Return a safe local filename derived from a URL's path basename."""
    name = unquote(os.path.basename(urlparse(url).path)) or "image.png"
    # Keep the basename only; strip any residual path separators just in case.
    return os.path.basename(name)


async def download_pngs(
    session: aiohttp.ClientSession,
    urls: List[str],
    dest_dir: str,
    max_images: Optional[int] = None,
) -> List[str]:
    """Download PNG URLs into ``dest_dir`` and return the local file paths.

    Failed downloads are skipped with a warning rather than aborting the batch.

    Args:
        session: An open aiohttp session.
        urls: Absolute PNG URLs to download.
        dest_dir: Directory to write images into (must already exist).
        max_images: Optional cap on the number of images to download.

    Returns:
        The local paths of successfully downloaded images, in input order.
    """
    if max_images is not None:
        urls = urls[:max_images]

    semaphore = asyncio.Semaphore(config.MAX_CONCURRENT_MODELS)

    async def _download(index: int, url: str) -> Optional[str]:
        # Prefix with the index to avoid collisions if two URLs share a basename.
        local_path = os.path.join(dest_dir, f"{index:03d}_{_filename_from_url(url)}")
        try:
            async with semaphore:
                async with session.get(url) as response:
                    if response.status != 200:
                        print(f"Warning: failed to download {url} (HTTP {response.status})")
                        return None
                    data = await response.read()
            with open(local_path, "wb") as handle:
                handle.write(data)
            return local_path
        except Exception as exc:
            print(f"Warning: error downloading {url}: {exc}")
            return None

    tasks = [_download(i, url) for i, url in enumerate(urls)]
    results = await asyncio.gather(*tasks)
    return [path for path in results if path is not None]
