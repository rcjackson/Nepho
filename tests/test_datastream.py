"""Offline tests for datastream parsing and quicklook URL building."""

import os
import sys
from datetime import date

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datastream import (
    Datastream,
    DatastreamParseError,
    build_directory_url,
    build_quicklook_url,
    parse_datastream,
)


def test_parse_basic():
    ds = parse_datastream("sgpmetE13.b1")
    assert ds.fac == "sgp"
    assert ds.instrument == "met"
    assert ds.site == "E13"
    assert ds.level == "b1"
    assert ds.facinstrument == "sgpmet"
    assert ds.raw == "sgpmetE13.b1"


def test_parse_central_facility():
    ds = parse_datastream("nsametC1.b1")
    assert ds.fac == "nsa"
    assert ds.instrument == "met"
    assert ds.site == "C1"
    assert ds.facinstrument == "nsamet"


def test_parse_instrument_with_digits():
    # Non-greedy instrument must still bind the trailing [A-Z]\d+ to the site.
    ds = parse_datastream("sgptwr10xC1.b1")
    assert ds.fac == "sgp"
    assert ds.instrument == "twr10x"
    assert ds.site == "C1"
    assert ds.level == "b1"
    assert ds.facinstrument == "sgptwr10x"


def test_parse_strips_whitespace():
    ds = parse_datastream("  enametC1.b1  ")
    assert ds.raw == "enametC1.b1"
    assert ds.fac == "ena"


@pytest.mark.parametrize("bad", [
    "",
    "notadatastream",
    "sgpmetE13",          # missing level
    "sgpmet.b1",          # missing sitecode
    "SGPmetE13.b1",       # uppercase fac
    "sgpmete13.b1",       # lowercase sitecode (no uppercase letter)
    "sgpmetE13.B1",       # uppercase level
])
def test_parse_invalid_raises(bad):
    with pytest.raises(DatastreamParseError):
        parse_datastream(bad)


def test_build_directory_url():
    ds = parse_datastream("sgpmetE13.b1")
    url = build_directory_url(ds, date(2023, 1, 1))
    assert url == "https://plot.adc.arm.gov/PLOTS/sgp/sgpmet/20230101/"


def test_build_directory_url_other():
    ds = parse_datastream("nsametC1.b1")
    url = build_directory_url(ds, date(2024, 12, 31))
    assert url == "https://plot.adc.arm.gov/PLOTS/nsa/nsamet/20241231/"


def test_build_quicklook_url():
    ds = parse_datastream("sgpmetE13.b1")
    url = build_quicklook_url(ds, date(2023, 1, 1))
    assert url == (
        "https://plot.adc.arm.gov/PLOTS/sgp/sgpmet/20230101/"
        "sgpmetE13.b1.meteogram.20230101.png"
    )


def test_build_quicklook_url_other():
    ds = parse_datastream("nsametC1.b1")
    url = build_quicklook_url(ds, date(2024, 12, 31))
    assert url == (
        "https://plot.adc.arm.gov/PLOTS/nsa/nsamet/20241231/"
        "nsametC1.b1.meteogram.20241231.png"
    )
