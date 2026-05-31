"""
nus-campus-weather
==================
Hourly meteorological data from 40 weather stations at the National University
of Singapore (NUS) campus, 2025.

Quick start
-----------
>>> import nus_campus_weather as ncw
>>> df = ncw.load_station("WS01")   # downloads from Zenodo on first call
>>> fig = ncw.plot_climatology()

To work against a local copy instead of auto-fetching, point the loader at it::

    ncw.set_data_dir("/path/to/nus-campus-weather-paper")
"""

from ._config import set_data_dir, get_data_dir
from ._fetch  import fetch_dataset, DATASET_VERSION, DATASET_DOI
from ._loader import load_station, load_all, station_metadata
from ._plots  import (
    plot_completeness,
    plot_climatology,
    plot_radials,
    plot_imputation_examples,
)

__version__ = "1.1.0"
__all__ = [
    "set_data_dir",
    "get_data_dir",
    "fetch_dataset",
    "DATASET_VERSION",
    "DATASET_DOI",
    "load_station",
    "load_all",
    "station_metadata",
    "plot_completeness",
    "plot_climatology",
    "plot_radials",
    "plot_imputation_examples",
]
