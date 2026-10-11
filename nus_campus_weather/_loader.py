import os
import glob
import warnings

import numpy as np
import pandas as pd

from ._config import get_data_dir
from ._constants import FLAG_OBSERVED, WIND_VARS

_META_CACHE = None
_FILE_GLOB  = "NUS_CAMPUS_WS*_2025_Hourly.csv"
_IMP_GLOB   = "NUS_CAMPUS_WS*_2025_Hourly_imputed.csv"
_META_COLS  = {"Latitude", "Longitude", "station"}
_WIND_WARNED = False


def _station_from_path(path: str) -> str:
    return os.path.basename(path).split("_")[2]


def _all_paths(imputed: bool = False) -> list:
    data_dir = get_data_dir()
    subdir   = os.path.join("data", "imputed" if imputed else "raw")
    pattern  = os.path.join(data_dir, subdir, _IMP_GLOB if imputed else _FILE_GLOB)
    return sorted(glob.glob(pattern))


def _flag_col(var: str) -> str:
    return var.split()[0] + "_flag"


def _apply_observed_only(df: pd.DataFrame) -> pd.DataFrame:
    """Set every value that is not an original observation (flag != 0) to NaN."""
    df = df.copy()
    for col in list(df.columns):
        fcol = _flag_col(col)
        if col.endswith("_flag") or fcol not in df.columns:
            continue
        df.loc[df[fcol] != FLAG_OBSERVED, col] = np.nan
    return df


def _warn_wind(df: pd.DataFrame) -> None:
    global _WIND_WARNED
    if _WIND_WARNED:
        return
    flagged = [v for v in WIND_VARS
               if _flag_col(v) in df.columns and (df[_flag_col(v)] != FLAG_OBSERVED).any()]
    if flagged:
        warnings.warn(
            "Gap-filled wind values (flag 1-2) are included. Wind is poorly predicted "
            "from neighbouring stations at intra-campus scale; use observed_only=True "
            "(or keep only rows with flag == 0) for wind analyses.",
            UserWarning, stacklevel=3)
        _WIND_WARNED = True


def station_metadata() -> pd.DataFrame:
    """Return a DataFrame (index=station) with columns lat, lon, elevation_m, type."""
    global _META_CACHE
    if _META_CACHE is not None:
        return _META_CACHE
    records = []
    for path in _all_paths():
        ws  = _station_from_path(path)
        row = pd.read_csv(path, nrows=1)
        elev_col = "Elevation (m)" if "Elevation (m)" in row.columns else "Elevation"
        records.append({
            "station": ws,
            "lat": float(row["Latitude"].iloc[0]),
            "lon": float(row["Longitude"].iloc[0]),
            "elevation_m": float(row[elev_col].iloc[0]) if elev_col in row.columns else np.nan,
            "type": row["Type"].iloc[0] if "Type" in row.columns else None,
        })
    _META_CACHE = pd.DataFrame(records).set_index("station").sort_index()
    return _META_CACHE


def load_station(station: str, imputed: bool = False,
                 observed_only: bool = False) -> pd.DataFrame:
    """Load all variables for a single station.

    Parameters
    ----------
    station : str
        Station ID, e.g. ``'WS01'``.
    imputed : bool
        If True, load the gap-filled dataset from the ``imputed/`` subdirectory.
    observed_only : bool
        With ``imputed=True``, return only original observations: values with
        flag 1 (linear interpolation), 2 (XGBoost) or 3 (not imputed) are set
        to NaN. Recommended for wind analyses.

    Returns
    -------
    pd.DataFrame
        Index = Datetime, columns = meteorological variables + flag columns
        (flag columns only present in imputed files; 0 = observed,
        1 = linear interpolation, 2 = XGBoost, 3 = not measured / not imputed).
    """
    data_dir = get_data_dir()
    fname    = f"NUS_CAMPUS_{station}_2025_Hourly{'_imputed' if imputed else ''}.csv"
    subdir   = os.path.join("data", "imputed" if imputed else "raw")
    path     = os.path.join(data_dir, subdir, fname)
    if not os.path.exists(path):
        raise FileNotFoundError(f"File not found: {path}")
    df = pd.read_csv(path, parse_dates=["Datetime"]).set_index("Datetime")
    drop = [c for c in _META_COLS if c in df.columns]
    df = df.drop(columns=drop)
    if imputed and observed_only:
        df = _apply_observed_only(df)
    elif imputed:
        _warn_wind(df)
    return df


def load_all(variable: str = None, imputed: bool = False,
             stations: list = None, observed_only: bool = False) -> pd.DataFrame:
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
    observed_only : bool
        With ``imputed=True``, keep only original observations (flag 0); all
        filled values are set to NaN. Recommended for wind analyses.

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
        if imputed and observed_only:
            df = _apply_observed_only(df)
        df["station"] = ws
        frames.append(df)

    combined = pd.concat(frames)
    if imputed and not observed_only and (variable is None or variable in WIND_VARS):
        _warn_wind(combined)

    if variable is not None:
        if variable not in combined.columns:
            avail = [c for c in combined.columns if c != "station"]
            raise ValueError(
                f"Variable '{variable}' not found. Available: {avail}"
            )
        wide = (combined.reset_index()
                .pivot(index="Datetime", columns="station", values=variable))
        wide.columns.name = "station"
        return wide

    return combined
