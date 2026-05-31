import matplotlib.cm as cm
import numpy as np

FONT           = "Palatino Linotype"
EXPECTED_HOURS = 8760
PRESSURE_OUTLIER = "WS17"

_viridis = cm.viridis
_vc = [_viridis(x) for x in np.linspace(0.08, 0.92, 6)]

# (column_name, display_label, unit, line_color, colormap)
VARS = [
    ("AirTemp Ave (C)",       "Air Temperature",   "\u00b0C",   _vc[0], cm.YlOrRd),
    ("RelHum Ave (%)",        "Relative Humidity", "%",         _vc[1], cm.YlGnBu),
    ("WindSpeed Ave (m/s)",   "Wind Speed",        "m/s",       _vc[2], cm.BuGn),
    ("AtmPress Ave (hPa)",    "Atm. Pressure",     "hPa",       _vc[3], cm.PuBu),
    ("GlobalRad Ave (W/m2)",  "Solar Radiation",   "W/m\u00b2", _vc[4], cm.afmhot),
    ("WindDir Ave (degrees)", "Wind Direction",    "\u00b0",    _vc[5], cm.twilight_shifted),
]

VARS_NO_WD = [v for v in VARS if v[0] != "WindDir Ave (degrees)"]

# Dark-end colormap colours used for mean lines (consistent across all figures)
MEAN_COLORS = {
    "AirTemp Ave (C)":      "#bd0026",
    "RelHum Ave (%)":       "#225ea8",
    "WindSpeed Ave (m/s)":  "#006d2c",
    "AtmPress Ave (hPa)":   "#023858",
    "GlobalRad Ave (W/m2)": "#e05c00",
}

VAR_BOUNDS = {
    "AirTemp Ave (C)":      (15.0, 45.0),
    "RelHum Ave (%)":       (0.0,  100.0),
    "WindSpeed Ave (m/s)":  (0.0,  20.0),
    "AtmPress Ave (hPa)":   (980.0, 1040.0),
    "GlobalRad Ave (W/m2)": (0.0,  1400.0),
}

RCPARAMS = {
    "font.family":        FONT,
    "axes.spines.top":    False,
    "axes.spines.right":  False,
    "axes.linewidth":     0.7,
    "xtick.major.width":  0.7,
    "ytick.major.width":  0.7,
    "figure.dpi":         150,
    "savefig.facecolor":  "white",
}
