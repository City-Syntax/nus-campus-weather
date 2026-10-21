"""Auto-fetch the NUS campus weather dataset from Zenodo.

The dataset is published as a versioned Zenodo archive. On first use the
zip is downloaded (~120 MB), checksum-verified, and unpacked into the user's
platform cache directory. Subsequent calls return the cached path instantly.
"""

from pathlib import Path

import pooch

# Zenodo record for nus-campus-weather-paper v1.1.0
DATASET_VERSION = "1.1.0"
DATASET_DOI = "10.5281/zenodo.23535609"
DATASET_CONCEPT_DOI = "10.5281/zenodo.20477760"

_ASSET = "City-Syntax/nus-campus-weather-paper-v1.1.0.zip"
_REGISTRY = {_ASSET: "md5:50f88f96ef3e1ce1a41087187f0b8a34"}

_FETCHER = pooch.create(
    path=pooch.os_cache("nus_campus_weather"),
    base_url="https://zenodo.org/records/23535609/files/",
    version=DATASET_VERSION,
    env="NUS_WEATHER_CACHE",
    registry=_REGISTRY,
)


def fetch_dataset(verbose: bool = True) -> str:
    """Download (or return cached path to) the NUS campus weather dataset.

    Returns
    -------
    str
        Filesystem path to the dataset root (the directory containing
        ``data/raw/``, ``data/imputed/``, ``figures/``, etc.).

    Notes
    -----
    The first call downloads ~120 MB from Zenodo (DOI 10.5281/zenodo.23535609)
    into the user's platform cache directory. Subsequent calls return the
    cached path instantly. Override the cache location with the
    ``NUS_WEATHER_CACHE`` environment variable.
    """
    if verbose and not _is_cached():
        print(
            f"nus_campus_weather: downloading dataset v{DATASET_VERSION} "
            f"from Zenodo (DOI {DATASET_DOI}, ~120 MB, one-time)..."
        )
    extracted = _FETCHER.fetch(_ASSET, processor=pooch.Unzip())

    for path in extracted:
        p = Path(path)
        while p.parent != p:
            if (p / "data" / "raw").is_dir():
                return str(p)
            p = p.parent

    raise RuntimeError(
        "Could not locate dataset root in extracted Zenodo archive — "
        "expected a 'data/raw/' subdirectory."
    )


def _is_cached() -> bool:
    """True if the zip is already cached locally (no download needed)."""
    cache_path = _FETCHER.abspath / _ASSET
    return cache_path.is_file()
