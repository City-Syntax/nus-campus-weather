import os
import glob
import pandas as pd
from ._config import get_data_dir

_META_CACHE = None
_FILE_GLOB  = "NUS_CAMPUS_WS*_2025_Hourly.csv"
_IMP_GLOB   = "NUS_CAMPUS_WS*_2025_Hourly_imputed.csv"
_META_COLS  = {"Latitude", "Longitude", "station"}


def _station_from_path(path: str) -> str:
    return os.path.basename(path).split("_")[2]


def _all_paths(imputed: bool = False) -> list:
    data_dir = get_data_dir()
    subdir   = os.path.join("data", "imputed" if imputed else "raw")
    pattern  = os.path.join(data_dir, subdir, _IMP_GLOB if imputed else _FILE_GLOB)
    return sorted(glob.glob(pattern))


def station_metadata() -> pd.DataFrame:
    """Return a DataFrame (index=station) with columns lat, lon."""
    global _META_CACHE
    if _META_CACHE is not None:
        return _META_CACHE
    records = []
    for path in _all_paths():
        ws  = _station_from_path(path)
        row = pd.read_csv(path, nrows=1)
        records.append({
            "station": ws,
            "lat": float(row["Latitude"].iloc[0]),
            "lon": float(row["Longitude"].iloc[0]),
        })
    _META_CACHE = pd.DataFrame(records).set_index("station").sort_index()
    return _META_CACHE


def load_station(station: str, imputed: bool = False) -> pd.DataFrame:
    """Load all variables for a single station.

    Parameters
    ----------
    station : str
        Station ID, e.g. ``'WS01'``.
    imputed : bool
        If True, load the gap-filled dataset from the ``imputed/`` subdirectory.

    Returns
    -------
    pd.DataFrame
        Index = Datetime, columns = meteorological variables + flag columns
        (flag columns only present in imputed files).
    """
    data_dir = get_data_dir()
    fname    = f"NUS_CAMPUS_{station}_2025_Hourly{'_imputed' if imputed else ''}.csv"
    subdir   = os.path.join("data", "imputed" if imputed else "raw")
    path     = os.path.join(data_dir, subdir, fname)
    if not os.path.exists(path):
        raise FileNotFoundError(f"File not found: {path}")
    df = pd.read_csv(path, parse_dates=["Datetime"]).set_index("Datetime")
    drop = [c for c in _META_COLS if c in df.columns]
    return df.drop(columns=drop)


def load_all(variable: str = None, imputed: bool = False,
             stations: list = None) -> pd.DataFrame:
    """Load data for all (or selected) stations.

    Parameters
    ----------
    variable : str, optional
        If provided, return a wide pivot with one column per station.
        If None, return a long-form DataFrame with a ``station`` column.
    imputed : bool
        Load gap-filled data when True.
    stations : list of str, optional
        Subset of station IDs to load.

    Returns
    -------
    pd.DataFrame
        Wide (Datetime × station) when *variable* is given,
        long-form otherwise.
    """
    paths = _all_paths(imputed=imputed)
    if stations:
        paths = [p for p in paths if _station_from_path(p) in stations]
    if not paths:
        raise FileNotFoundError("No data files found. Check set_data_dir().")

    frames = []
    for path in paths:
        ws = _station_from_path(path)
        df = pd.read_csv(path, parse_dates=["Datetime"]).set_index("Datetime")
        drop = [c for c in _META_COLS - {"station"} if c in df.columns]
        df   = df.drop(columns=drop)
        df["station"] = ws
        frames.append(df)

    combined = pd.concat(frames)

    if variable is not None:
        if variable not in combined.columns:
            avail = [c for c in combined.columns if c != "station"]
            raise ValueError(
                f"Variable '{variable}' not found. Available: {avail}"
            )
        return combined.pivot_table(
            index=combined.index, columns="station",
            values=variable, aggfunc="first"
        )

    return combined
