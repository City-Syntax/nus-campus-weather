# 🌦️ nus-campus-weather

Python package for the **NUS Campus Meteorological Network** dataset — hourly observations from 40 automatic weather stations across the National University of Singapore (NUS) main campus, Singapore, for the full calendar year 2025.

> **Dataset repo:** [nus-campus-weather-paper](https://github.com/City-Syntax/nus-campus-weather-paper)  
> **PyPI:** `pip install nus-campus-weather`

---

## 📦 Installation

**From PyPI:**
```bash
pip install nus-campus-weather
```

**From source:**
```bash
git clone https://github.com/City-Syntax/nus-campus-weather.git
cd nus-campus-weather
pip install -e .
```

**Dependencies:** `pandas`, `numpy`, `matplotlib`, `seaborn`  
Optional (for map backgrounds): `contextily`

---

## 🚀 Quick Start

```python
import nus_campus_weather as ncw

# Just use it — the dataset auto-downloads from Zenodo on first call
# (~100 MB, one-time), then cached for future use.
df = ncw.load_station("WS01")
fig = ncw.plot_climatology()
```

### Optional — explicit fetch

```python
ncw.fetch_dataset()   # download/cache now instead of on first load
```

### Optional — bring your own copy

If you have a local clone of the [dataset repo](https://github.com/City-Syntax/nus-campus-weather-paper)
(useful for development or offline work), point the loader at it:

```python
ncw.set_data_dir("/path/to/nus-campus-weather-paper")
# Or via env var:
# export NUS_WEATHER_DATA="/path/to/nus-campus-weather-paper"
```

The auto-fetch caches to your platform cache dir (`~/Library/Caches/nus_campus_weather/`
on macOS, `~/.cache/nus_campus_weather/` on Linux, `%LOCALAPPDATA%\nus_campus_weather\`
on Windows). Override with the `NUS_WEATHER_CACHE` environment variable.

### Dataset version

```python
ncw.DATASET_VERSION   # '1.0.0'
ncw.DATASET_DOI       # '10.5281/zenodo.20477761'
```

---

## 📂 Loading Data

### Single station

```python
# Raw sensor data
df = ncw.load_station("WS01")

# Gap-filled data (includes _flag columns)
df = ncw.load_station("WS01", imputed=True)
```

Each CSV has columns: `Datetime`, `Latitude`, `Longitude`, `Elevation (m)`, `Type`, and six meteorological variables (plus `Rain Tot (mm)` at WS02, WS16, WS35). Imputed files add a `_flag` column per variable:

| Flag | Meaning |
|---|---|
| `0` | Original observation |
| `1` | Stage 1 linear interpolation (short gaps) |
| `2` | Stage 2 XGBoost spatial regression |
| `3` | Not measured / not imputed (left empty) |

### Observed values only

```python
# Gap-filled file, but every filled value (flag 1-3) returned as NaN
df  = ncw.load_station("WS01", imputed=True, observed_only=True)
wsp = ncw.load_all(variable="WindSpeed Ave (m/s)", imputed=True, observed_only=True)
```

> ⚠️ **Wind:** gap-filled wind speed and direction have little skill at intra-campus scale. Use `observed_only=True` (or filter `flag == 0`) for wind analyses; the package warns if filled wind values are loaded.

### All 40 stations

```python
# Wide format — one column per station (8760 rows × 40 cols)
temp = ncw.load_all(variable="AirTemp Ave (C)", imputed=True)

# Long format — all stations stacked
long_df = ncw.load_all(imputed=True)
```

### Station metadata

```python
meta = ncw.station_metadata()
# Returns a DataFrame indexed by station (WS01..WS40) with columns:
# lat, lon, elevation_m, type (Ground / Roof / Roof-3axis)
```

---

## 📊 Plot Functions

All plot functions use the data directory set via `set_data_dir()` and save figures to a `figures/` subfolder within it.

| Function | Output |
|---|---|
| `ncw.plot_completeness()` | Completeness bubble map and monthly heatmap (cf. paper Fig. 4) |
| `ncw.plot_climatology()` | Diurnal × seasonal climatology (cf. paper Fig. 6) |
| `ncw.plot_radials()` | Annual radial climatology, five variables (cf. paper Fig. 9) |
| `ncw.plot_imputation_examples()` | Representative gap-fill examples (cf. paper Fig. 10) |

```python
ncw.plot_completeness()
ncw.plot_climatology()
ncw.plot_radials()
ncw.plot_imputation_examples()
```

---

## 🗂️ Dataset Variables

| Column | Units | Notes |
|---|---|---|
| `AirTemp Ave (C)` | °C | Ground stations 2–3 m above ground; 8 rooftop stations |
| `RelHum Ave (%)` | % | |
| `AtmPress Ave (hPa)` | hPa | |
| `GlobalRad Ave (W/m2)` | W m⁻² | Global horizontal irradiance at the sensor, including local shading |
| `WindSpeed Ave (m/s)` | m s⁻¹ | |
| `WindDir Ave (degrees)` | ° | 0–360° |
| `Rain Tot (mm)` | mm | WS02, WS16, WS35 only |

### ⚠️ Known issues

From dataset v1.1.0, faulty sensor values are removed by rule-based quality control; every removal is listed in `data_quality_assessment/qc_log.csv` of the dataset repository.

- **Global irradiance not available (flag 3, not imputed)** at WS38 (no pyranometer, fully shaded site) and WS32, WS39 (pyranometers non-functional).
- **Global irradiance removed for some months** at WS07, WS19, WS23 and WS26 (corrupted channel; spurious night-time readings).
- **WS17** — pressure removed for January–April (faulty sensor) and wind for 20–26 December (sensor malfunction); these gaps are filled like any other.
- **Wind speed/direction** — spatially decorrelated at intra-campus scale; use only flag = 0 observations for wind analyses (`observed_only=True`).

---

## 📄 Citation

If you use this package or dataset, please cite:

> Lim, J. et al. *An hourly meteorological dataset from a high-density 40-station campus weather network in tropical Singapore.* Scientific Data (under review).
>
> Dataset: Zenodo, https://doi.org/10.5281/zenodo.20477760 (all versions)

---

## 📜 Licence

Code (this package): [MIT](https://opensource.org/licenses/MIT) — see `LICENSE`.  
Dataset: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) — see the [dataset repository](https://github.com/City-Syntax/nus-campus-weather-paper).
