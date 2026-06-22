"""Parsing of ARM datastream names and building of quicklook directory URLs.

ARM datastream names follow the convention ``facinstrumentSITECODE.level``,
for example ``sgpmetE13.b1``:

* ``fac``          - the three-letter site/facility prefix (``sgp``)
* ``instrument``   - the instrument class (``met``)
* ``site``         - the SITECODE, an uppercase letter followed by digits (``E13``)
* ``level``        - the data level following the dot (``b1``)

The quicklook images for a datastream live under a directory named with only the
``facinstrument`` portion (the datastream name with the SITECODE and level
stripped), e.g. ``sgpmet``.

ARM's plot server exposes no usable directory listing, so the exact quicklook PNG
URL must be constructed directly. The filename is currently geared to the ``met``
instrument's meteogram, ``<datastream>.meteogram.<YYYYMMDD>.png`` (configurable
via ``config.DQ_FILENAME_TEMPLATE``).
"""

from dataclasses import dataclass
from datetime import date
import re

from config import config

# Non-greedy ``instrument`` so the trailing ``[A-Z]\d+`` binds to the SITECODE.
_DATASTREAM_RE = re.compile(
    r"^(?P<fac>[a-z]{3})(?P<instrument>[a-z0-9]+?)(?P<site>[A-Z]\d+)\.(?P<level>[a-z0-9]+)$"
)


class DatastreamParseError(ValueError):
    """Raised when a datastream name does not match the expected format."""


@dataclass
class Datastream:
    """A parsed ARM datastream name."""

    raw: str
    fac: str
    instrument: str
    site: str
    level: str

    @property
    def facinstrument(self) -> str:
        """Return the ``facinstrument`` directory name (no SITECODE or level)."""
        return f"{self.fac}{self.instrument}"


def parse_datastream(name: str) -> Datastream:
    """Parse a datastream name like ``sgpmetE13.b1`` into a :class:`Datastream`.

    Args:
        name: The datastream name in ``facinstrumentSITECODE.level`` format.

    Returns:
        The parsed :class:`Datastream`.

    Raises:
        DatastreamParseError: If ``name`` does not match the expected format.
    """
    match = _DATASTREAM_RE.match(name.strip())
    if not match:
        raise DatastreamParseError(
            f"Invalid datastream name '{name}'. "
            "Expected format like 'sgpmetE13.b1' (facinstrumentSITECODE.level)."
        )

    return Datastream(
        raw=name.strip(),
        fac=match.group("fac"),
        instrument=match.group("instrument"),
        site=match.group("site"),
        level=match.group("level"),
    )


def build_directory_url(ds: Datastream, day: date) -> str:
    """Build the quicklook directory URL for a datastream on a given day.

    Args:
        ds: The parsed datastream.
        day: The day whose quicklook directory to build.

    Returns:
        The directory URL, e.g.
        ``https://plot.adc.arm.gov/PLOTS/sgp/sgpmet/20230101/``.
    """
    return config.DQ_PATH_TEMPLATE.format(
        base=config.DQ_BASE_URL.rstrip("/"),
        fac=ds.fac,
        facinstrument=ds.facinstrument,
        yyyymmdd=day.strftime("%Y%m%d"),
    )


def build_quicklook_url(ds: Datastream, day: date) -> str:
    """Build the full quicklook PNG URL for a datastream on a given day.

    The URL is the day's directory (:func:`build_directory_url`) joined with the
    filename rendered from ``config.DQ_FILENAME_TEMPLATE``. The default filename
    is the ``met`` instrument's meteogram.

    Args:
        ds: The parsed datastream.
        day: The day whose quicklook image to build.

    Returns:
        The PNG URL, e.g.
        ``https://plot.adc.arm.gov/PLOTS/sgp/sgpmet/20230101/sgpmetE13.b1.meteogram.20230101.png``.
    """
    filename = config.DQ_FILENAME_TEMPLATE.format(
        datastream=ds.raw,
        yyyymmdd=day.strftime("%Y%m%d"),
    )
    return build_directory_url(ds, day) + filename
