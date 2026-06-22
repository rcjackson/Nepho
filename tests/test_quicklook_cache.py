"""Offline tests for the per-day quicklook picture cache helper."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from quicklook_fetcher import cached_pngs


def test_missing_dir_returns_empty(tmp_path):
    assert cached_pngs(str(tmp_path / "does_not_exist")) == []


def test_empty_dir_returns_empty(tmp_path):
    assert cached_pngs(str(tmp_path)) == []


def test_lists_pngs_sorted_ignoring_non_pngs(tmp_path):
    # Create out of order to confirm sorting; include a non-PNG to confirm it's ignored.
    (tmp_path / "001_b.png").write_bytes(b"x")
    (tmp_path / "000_a.png").write_bytes(b"x")
    (tmp_path / "notes.txt").write_text("ignore me")

    result = cached_pngs(str(tmp_path))

    assert result == [
        os.path.join(str(tmp_path), "000_a.png"),
        os.path.join(str(tmp_path), "001_b.png"),
    ]


def test_png_extension_is_case_insensitive(tmp_path):
    (tmp_path / "000_a.PNG").write_bytes(b"x")
    result = cached_pngs(str(tmp_path))
    assert result == [os.path.join(str(tmp_path), "000_a.PNG")]
