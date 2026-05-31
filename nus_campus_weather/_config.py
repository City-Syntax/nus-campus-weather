import os

_DATA_DIR = None


def set_data_dir(path: str) -> None:
    """Pin the loader to a local directory containing the NUS-WS CSV files.

    Use this when working from a local clone of the dataset repository
    (e.g. for development) instead of letting the package auto-fetch from
    Zenodo on first use.
    """
    global _DATA_DIR
    _DATA_DIR = os.path.expanduser(str(path))


def get_data_dir() -> str:
    """Return the directory that the loader should read from.

    Resolution order:
      1. Path passed to ``set_data_dir()``.
      2. ``NUS_WEATHER_DATA`` environment variable.
      3. Auto-fetch from Zenodo (downloads on first call, then cached).
    """
    if _DATA_DIR is not None:
        return _DATA_DIR
    env = os.environ.get("NUS_WEATHER_DATA")
    if env:
        return env
    from ._fetch import fetch_dataset
    return fetch_dataset()
