# 🌦️ nus-campus-weather

Python package for the **NUS Campus Meteorological Network** dataset — hourly observations from 40 automatic weather stations across the National University of Singapore (NUS) main campus, Singapore, for the full calendar year 2025.

> **Dataset repo:** [nus-campus-weather-paper](https://github.com/City-Syntax/nus-campus-weather-paper)  
> **PyPI:** `pip install nus-campus-weather` *(once published)*

---

## 📦 Installation

**From PyPI** *(once published)*:
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

Each CSV has columns: `Datetime`, `Latitude`, `Longitude`, and six meteorological variables. Imputed files add a `_flag` column per variable (`0` = original, `1` = linear interpolation, `2` = XGBoost).

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
# Returns a DataFrame indexed by station (WS01..WS40) with columns: lat, lon
```

---

## 📊 Plot Functions

All plot functions use the data directory set via `set_data_dir()` and save figures to a `figures/` subfolder within it.

| Function | Output |
|---|---|
| `ncw.plot_completeness()` | Bubble map (Fig 4) + monthly heatmap (Fig 5) |
| `ncw.plot_climatology()` | Diurnal × seasonal climatology (Fig 6b) |
| `ncw.plot_radials()` | Annual radial climatology, all variables (Fig 6a, 8a–f) |
| `ncw.plot_imputation_examples()` | Representative gap-fill examples (Fig 10) |

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
| `AirTemp Ave (C)` | °C | 2 m height |
| `RelHum Ave (%)` | % | 2 m height |
| `AtmPress Ave (hPa)` | hPa | |
| `GlobalRad Ave (W/m2)` | W m⁻² | Global horizontal irradiance |
| `WindSpeed Ave (m/s)` | m s⁻¹ | 2 m height |
| `WindDir Ave (degrees)` | ° | 0–360° |
| `Rain Tot (mm)` | mm | WS02, WS16, WS35 only |

### ⚠️ Known issues

- **WS17 atmospheric pressure** — faulty sensor; `AtmPress Ave (hPa)` is `NaN` in both raw and imputed files.
- **WS38 global irradiance** — complete pyranometer failure; imputed values are spatially reconstructed, treat with caution.
- **Wind speed/direction** — spatially decorrelated at intra-campus scale; use only flag = 0 observations for wind analyses.

---

## 📄 Citation

If you use this package or dataset, please cite:

> [Authors]. *World's densest campus weather network: a 40-station hourly meteorological dataset from tropical Singapore.* Scientific Data [year]. DOI: [to be assigned]

---

## 📜 Licence

Code (this package): [MIT](https://opensource.org/licenses/MIT) — see `LICENSE`.  
Dataset: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) — see the [dataset repository](https://github.com/City-Syntax/nus-campus-weather-paper).
