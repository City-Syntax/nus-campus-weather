import warnings
import calendar
import os

import matplotlib.cm as cm
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.patches as mpatches
import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib.colors import Normalize
from matplotlib.lines import Line2D

from ._constants import (FONT, EXPECTED_HOURS, PRESSURE_OUTLIER,
                          VARS, VARS_NO_WD, MEAN_COLORS, RCPARAMS)
from ._loader import load_all, load_station, station_metadata

MONTH_ABBR = [calendar.month_abbr[m] for m in range(1, 13)]
_HOUR_CMAP = cm.twilight_shifted
_R_IN, _R_OUT = 0.30, 0.90   # inner/outer radius of data ring


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _apply_style():
    plt.rcParams.update(RCPARAMS)


def _save(fig, save_path):
    if save_path:
        fig.savefig(save_path, dpi=200, bbox_inches="tight")


# ── Radial helpers ────────────────────────────────────────────────────────────

def _doy_to_theta(doy):
    return (np.asarray(doy, float) - 1) / 365 * 2 * np.pi


def _to_radius(val, vmin, vmax):
    frac = np.clip((np.asarray(val, float) - vmin) / (vmax - vmin), 0, 1)
    return frac * (_R_OUT - _R_IN) + _R_IN


def _setup_polar(ax):
    ax.set_theta_zero_location("N")
    ax.set_theta_direction(-1)
    ax.set_ylim(0, 1.15)
    ax.set_yticks([]); ax.set_xticks([])
    ax.spines["polar"].set_visible(False)
    ax.set_facecolor("white")
    tc = np.linspace(0, 2 * np.pi, 360)
    ax.plot(tc, np.full(360, _R_IN),  color="#dddddd", lw=0.5, ls="--", zorder=1)
    ax.plot(tc, np.full(360, _R_OUT), color="#dddddd", lw=0.5, ls="--", zorder=1)


def _add_month_labels(ax, fontsize=6.5, r_text=1.035):
    for m in range(1, 13):
        doy_m = pd.Timestamp(f"2025-{m:02d}-01").timetuple().tm_yday
        t = _doy_to_theta(doy_m)
        ax.text(t, r_text, MONTH_ABBR[m - 1], ha="center", va="bottom",
                fontsize=fontsize, fontfamily=FONT, color="#666666", zorder=9)
        ax.plot([t, t], [_R_OUT, _R_OUT + 0.025], color="#bbbbbb", lw=0.7, zorder=7)


def _annotate_scale(ax, vmin_v, vmax_v, unit):
    # Oct position (right side of ring, less crowded)
    t_ref = _doy_to_theta(274)
    ax.text(t_ref, _R_IN - 0.065, f"{vmin_v:.1f} {unit}",
            ha="center", va="center", fontsize=5.2, fontfamily=FONT,
            color="#888888", zorder=10)
    ax.text(t_ref, _R_OUT + 0.055, f"{vmax_v:.1f} {unit}",
            ha="center", va="center", fontsize=5.2, fontfamily=FONT,
            color="#888888", zorder=10)


def _add_panel_legend(ax, lc, line_label, has_band=True, mean_color=None):
    mc = mean_color if mean_color is not None else lc
    handles = [Line2D([0], [0], color=mc, lw=1.3, alpha=0.85, label=line_label)]
    if has_band:
        handles.append(
            mpatches.Patch(facecolor=mc, alpha=0.28, label="\u00b11 s.d. (40 stations)")
        )
    ax.legend(
        handles=handles,
        bbox_to_anchor=(0.5, -0.03), loc="upper center",
        fontsize=5.2, framealpha=0.92, edgecolor="#dddddd", fancybox=False,
        ncol=len(handles), columnspacing=0.7,
        handlelength=1.2, handletextpad=0.4, borderpad=0.4,
        prop={"family": FONT},
    )


def _draw_wind_rose(ax, src_df, n_sectors=16):
    ax.set_theta_zero_location("N")
    ax.set_theta_direction(-1)
    ax.set_facecolor("white")
    ax.set_yticks([]); ax.set_xticks([])
    ax.spines["polar"].set_visible(False)

    sector_deg = 360 / n_sectors
    wd = src_df[["hour", "WindDir Ave (degrees)"]].dropna().copy()
    wd["sector"] = (wd["WindDir Ave (degrees)"] / sector_deg).astype(int) % n_sectors
    total = len(wd)
    pivot = (wd.groupby(["hour", "sector"]).size()
               .unstack(fill_value=0)
               .reindex(index=range(24), columns=range(n_sectors), fill_value=0)
               / total * 100)

    sector_theta = np.deg2rad(np.arange(n_sectors) * sector_deg + sector_deg / 2)
    bar_width    = np.deg2rad(sector_deg * 0.90)
    bottoms = np.zeros(n_sectors)
    for h in range(24):
        heights = pivot.loc[h].values
        ax.bar(sector_theta, heights, width=bar_width, bottom=bottoms,
               color=_HOUR_CMAP(h / 23), alpha=0.88, edgecolor="none", zorder=3)
        bottoms += heights

    max_freq = bottoms.max()
    r_max    = max(np.ceil(max_freq / 2) * 2, 4)
    ax.set_ylim(0, r_max * 1.30)

    tc = np.linspace(0, 2 * np.pi, 360)
    for pct in np.arange(2, r_max + 0.1, 2):
        ax.plot(tc, np.full(360, pct), color="#e8e8e8", lw=0.5, zorder=1)
    for pct in np.arange(4, r_max + 0.1, 4):
        ax.text(np.deg2rad(12), pct, f"{pct:.0f}%",
                fontsize=4.8, fontfamily=FONT, color="#aaaaaa",
                ha="left", va="bottom", zorder=6)
    for lbl, ang in zip(["N","NE","E","SE","S","SW","W","NW"],
                         [0, 45, 90, 135, 180, 225, 270, 315]):
        ax.text(np.deg2rad(ang), r_max * 1.20, lbl,
                ha="center", va="center", fontsize=6.5,
                fontfamily=FONT, fontweight="bold", color="#555555", zorder=7)

    r_inner = r_max * 0.13
    ax.fill(tc, np.full(360, r_inner), color="white", zorder=5)
    ax.text(0, 0, "Wind\nDirection\n(% freq.)",
            ha="center", va="center", fontsize=6.5,
            fontfamily=FONT, color="#333333",
            multialignment="center", zorder=10)


def _draw_radial(ax, doy, hour, val, vmin, vmax, lc,
                 std=None, show_mean=True, mean_mask=None, mean_color=None):
    thetas = _doy_to_theta(doy)
    r      = _to_radius(val, vmin, vmax)
    ax.scatter(thetas, r, c=hour, cmap=_HOUR_CMAP, vmin=0, vmax=23,
               s=0.9, alpha=0.68, lw=0, zorder=3, rasterized=True)

    if show_mean or (std is not None):
        df_tmp = pd.DataFrame({
            "doy": doy, "val": val,
            "std": std if std is not None else np.zeros(len(doy))
        })
        df_m = df_tmp[mean_mask] if mean_mask is not None else df_tmp
        dg   = df_m.groupby("doy").agg(
            mv=("val", "mean"), ms=("std", "mean")
        ).reset_index()
        mv_loop = np.append(dg["mv"].values, dg["mv"].values[0])
        ms_loop = np.append(dg["ms"].values, dg["ms"].values[0])
        t_loop  = np.append(_doy_to_theta(dg["doy"].values),
                             _doy_to_theta(dg["doy"].values[0]))
        if std is not None:
            r_lo = _to_radius(mv_loop - ms_loop, vmin, vmax)
            r_hi = _to_radius(mv_loop + ms_loop, vmin, vmax)
            bc   = mean_color if mean_color is not None else lc
            ax.fill_between(t_loop, r_lo, r_hi, color=bc, alpha=0.22, zorder=2)
        if show_mean:
            ax.plot(t_loop, _to_radius(mv_loop, vmin, vmax),
                    color=mean_color if mean_color is not None else lc,
                    lw=0.9, alpha=0.85, zorder=4)

    tc = np.linspace(0, 2 * np.pi, 360)
    ax.fill(tc, np.full(360, _R_IN), color="white", zorder=5)


_RADIAL_CFG = {
    "AirTemp Ave (C)":      dict(center=["Air Temp.", "(\u00b0C)", "inner=min, outer=max"],
                                  line_label="Network daily mean",
                                  has_band=True, show_mean=True, daytime_only=False),
    "RelHum Ave (%)":       dict(center=["Rel. Humidity", "(%)", "inner=min, outer=max"],
                                  line_label="Network daily mean",
                                  has_band=True, show_mean=True, daytime_only=False),
    "WindSpeed Ave (m/s)":  dict(center=["Wind Speed", "(m/s)", "inner=min, outer=max"],
                                  line_label="Network daily mean",
                                  has_band=True, show_mean=True, daytime_only=False),
    "AtmPress Ave (hPa)":   dict(center=["Atm. Pressure", "(hPa)", "inner=min, outer=max"],
                                  line_label="Network daily mean",
                                  has_band=True, show_mean=True, daytime_only=False),
    "GlobalRad Ave (W/m2)": dict(center=["Solar Rad.", "(W/m\u00b2)", "inner=min, outer=max"],
                                  line_label="Daytime mean  07\u201318h",
                                  has_band=True, show_mean=True, daytime_only=True),
    "WindDir Ave (degrees)":dict(center=["Wind Dir.", "(\u00b0)", "radius = direction",
                                          "0\u00b0/360\u00b0=N  90\u00b0=E",
                                          "180\u00b0=S  270\u00b0=W"],
                                  line_label=None,
                                  has_band=False, show_mean=False, daytime_only=False),
}


# ─────────────────────────────────────────────────────────────────────────────
# Public plot functions
# ─────────────────────────────────────────────────────────────────────────────

def plot_completeness(save_dir: str = None):
    """Bubble map and monthly completeness heatmap.

    Parameters
    ----------
    save_dir : str, optional
        Directory to save PNG files. Filenames are auto-generated.

    Returns
    -------
    fig_map, fig_heat : matplotlib.figure.Figure
    """
    try:
        import contextily as ctx
    except ImportError:
        ctx = None

    _apply_style()
    import copy
    from matplotlib.patches import Patch
    from matplotlib.ticker import FormatStrFormatter

    MAKO = sns.color_palette("mako", as_cmap=True)

    # ── Load ─────────────────────────────────────────────────────────────────
    long_df  = load_all()
    meta     = station_metadata()
    stations = sorted(long_df["station"].unique())
    VAR_COLS = [v[0] for v in VARS if v[0] in long_df.columns]

    station_meta_local = {}
    monthly_data       = {}

    for ws in stations:
        sub  = long_df[long_df["station"] == ws]
        lat  = meta.loc[ws, "lat"]
        lon  = meta.loc[ws, "lon"]
        overall = sub[VAR_COLS].notna().all(axis=1).sum() / EXPECTED_HOURS * 100
        station_meta_local[ws] = {"lat": lat, "lon": lon, "overall": overall}

        sub = sub.copy()
        sub["month"] = pd.to_datetime(sub.index).month if not isinstance(sub.index, pd.DatetimeIndex) else sub.index.month
        monthly = {}
        for m in range(1, 13):
            expected = calendar.monthrange(2025, m)[1] * 24
            pct = sub[sub["month"] == m]["AirTemp Ave (C)"].notna().sum() / expected * 100
            monthly[m] = round(min(pct, 100), 2)
        monthly_data[ws] = monthly

    orig_lons = [station_meta_local[ws]["lon"] for ws in stations]
    orig_lats = [station_meta_local[ws]["lat"] for ws in stations]
    vals      = [station_meta_local[ws]["overall"] for ws in stations]
    sizes     = [max(((v / 100) ** 2.2) * 700 + 65, 220) for v in vals]

    # ── Fig 1 — Bubble Map ────────────────────────────────────────────────────
    fig_map, ax1 = plt.subplots(figsize=(11, 9))
    fig_map.patch.set_facecolor("white")

    pad_lon, pad_lat = 0.004, 0.004
    ax1.set_xlim(min(orig_lons) - pad_lon, max(orig_lons) + pad_lon)
    ax1.set_ylim(min(orig_lats) - pad_lat, max(orig_lats) + pad_lat)

    if ctx is not None:
        try:  # tiles need internet access; the map still renders without them
            ctx.add_basemap(ax1, crs="EPSG:4326",
                            source=ctx.providers.CartoDB.Positron,
                            alpha=0.45, zorder=0, attribution=False)
        except Exception as e:
            warnings.warn(f"Basemap not drawn ({type(e).__name__}).", stacklevel=2)

    sc = ax1.scatter(orig_lons, orig_lats, s=sizes, c=vals,
                     cmap=MAKO, vmin=65, vmax=100,
                     edgecolors="white", linewidths=0.9,
                     zorder=3, alpha=0.88)

    for lon, lat, ws, val in zip(orig_lons, orig_lats, stations, vals):
        txt_col = "white" if val < 88 else "#1a1a1a"
        ax1.text(lon, lat, f"#{ws.replace('WS','')}\n{val:.0f}%",
                 ha="center", va="center", zorder=5,
                 fontsize=5.2, fontweight="bold", linespacing=1.35,
                 color=txt_col, fontfamily=FONT)

    cbar = fig_map.colorbar(sc, ax=ax1, fraction=0.028, pad=0.02, aspect=30)
    cbar.set_label("Overall Data Completeness (%)", fontsize=10,
                   fontfamily=FONT, labelpad=10)
    cbar.ax.tick_params(labelsize=8.5)

    leg_handles = [
        ax1.scatter([], [], s=((p/100)**2.2)*700+65, c="#888888",
                    alpha=0.7, edgecolors="white", linewidths=0.8)
        for p in [75, 88, 100]
    ]
    ax1.legend(leg_handles, ["75%", "88%", "100%"],
               title="Completeness", title_fontsize=9,
               fontsize=8.5, loc="upper left", framealpha=0.93,
               edgecolor="#cccccc", fancybox=False,
               labelspacing=1.8, handletextpad=1.4, borderpad=1.1)
    ax1.xaxis.set_major_formatter(FormatStrFormatter("%.4f"))
    ax1.yaxis.set_major_formatter(FormatStrFormatter("%.4f"))
    ax1.set_xlabel("Longitude (\u00b0E)", fontsize=10.5, fontfamily=FONT, labelpad=8)
    ax1.set_ylabel("Latitude (\u00b0N)",  fontsize=10.5, fontfamily=FONT, labelpad=8)
    ax1.tick_params(labelsize=8.5)
    ax1.set_title(
        "Spatial Distribution and Data Completeness of the NUS Campus\n"
        "Meteorological Observation Network (2025)",
        fontsize=12.5, fontfamily=FONT, fontweight="bold", pad=16, loc="left"
    )
    fig_map.tight_layout()

    # ── Fig 2 — Monthly Heatmap ───────────────────────────────────────────────
    matrix = pd.DataFrame(
        {ws: [monthly_data[ws][m] for m in range(1, 13)] for ws in stations},
        index=MONTH_ABBR
    ).T
    overall_vals = [station_meta_local[ws]["overall"] for ws in stations]
    row_order = [stations[i] for i in np.argsort(overall_vals)[::-1]]
    matrix = matrix.loc[row_order]

    mako_nd = copy.copy(MAKO)
    mako_nd.set_bad("#d4d4d4")
    masked = np.ma.masked_where(matrix.values < 5, matrix.values)

    fig_heat, ax2 = plt.subplots(figsize=(14, 12))
    fig_heat.patch.set_facecolor("white")
    im = ax2.imshow(masked, aspect="auto", cmap=mako_nd,
                    vmin=35, vmax=100, interpolation="nearest", alpha=0.92)

    ax2.set_xticks(range(12)); ax2.set_xticklabels(MONTH_ABBR, fontsize=9.5, fontfamily=FONT)
    ax2.set_yticks(range(len(row_order)))
    ax2.set_yticklabels(row_order, fontsize=8.5, fontfamily=FONT)

    for i in range(len(row_order)):
        for j in range(12):
            v = matrix.values[i, j]
            if v < 5:
                ax2.text(j, i, "N/A", ha="center", va="center",
                         fontsize=5.8, fontweight="bold", color="#555555", fontfamily=FONT)
            elif v < 95:
                ax2.text(j, i, f"{v:.0f}%", ha="center", va="center",
                         fontsize=6.0, fontweight="bold",
                         color="white" if v < 75 else "#1a1a1a", fontfamily=FONT)

    ax2.set_xticks(np.arange(-0.5, 12, 1), minor=True)
    ax2.set_yticks(np.arange(-0.5, len(row_order), 1), minor=True)
    ax2.grid(which="minor", color="white", linewidth=1.0)
    ax2.tick_params(which="minor", length=0)
    cbar2 = fig_heat.colorbar(im, ax=ax2, fraction=0.022, pad=0.015, aspect=35)
    cbar2.set_label("Monthly Data Completeness (%)", fontsize=10,
                    fontfamily=FONT, labelpad=10)
    cbar2.ax.tick_params(labelsize=8.5)
    ax2.legend(handles=[Patch(facecolor="#d4d4d4", edgecolor="#aaaaaa",
                               linewidth=0.5, label="No data (<5%)")],
               loc="lower right", fontsize=8.5, framealpha=0.93,
               edgecolor="#cccccc", fancybox=False)
    ax2.set_xlabel("Month", fontsize=10.5, fontfamily=FONT, labelpad=10)
    ax2.set_ylabel("Weather Station", fontsize=10.5, fontfamily=FONT, labelpad=10)
    ax2.set_title(
        "Monthly Data Completeness Across the NUS Campus\n"
        "Meteorological Observation Network (2025)",
        fontsize=12.5, fontfamily=FONT, fontweight="bold", pad=16, loc="left"
    )
    fig_heat.tight_layout()

    if save_dir:
        fig_map.savefig( os.path.join(save_dir, "completeness_map.png"),  dpi=200, bbox_inches="tight")
        fig_heat.savefig(os.path.join(save_dir, "completeness_heat.png"), dpi=200, bbox_inches="tight")

    return fig_map, fig_heat


def plot_climatology(save_path: str = None):
    """Diurnal × seasonal climatology heatmap (5 variables, month × hour).

    Parameters
    ----------
    save_path : str, optional
        File path to save the figure (PNG or PDF).

    Returns
    -------
    matplotlib.figure.Figure
    """
    _apply_style()
    long_df = load_all()
    long_df = long_df.copy()
    long_df.loc[long_df["station"] == PRESSURE_OUTLIER, "AtmPress Ave (hPa)"] = np.nan

    if not isinstance(long_df.index, pd.DatetimeIndex):
        long_df.index = pd.to_datetime(long_df.index)
    long_df["month"] = long_df.index.month
    long_df["hour"]  = long_df.index.hour

    fig, axes = plt.subplots(5, 1, figsize=(18, 14))
    fig.patch.set_facecolor("white")

    for ax, (col, label, unit, lc, cmap) in zip(axes, VARS_NO_WD):
        climate = long_df.groupby(["month", "hour"])[col].mean().unstack(level="hour")
        vmin_v  = climate.values.min()
        vmax_v  = climate.values.max()
        if col == "GlobalRad Ave (W/m2)":
            vmin_v = 0

        im = ax.imshow(climate.values, aspect="auto", cmap=cmap,
                       vmin=vmin_v, vmax=vmax_v,
                       interpolation="bilinear", origin="upper")

        ax.set_xticks(np.arange(-0.5, 24, 1), minor=True)
        ax.set_yticks(np.arange(-0.5, 12, 1), minor=True)
        ax.grid(which="minor", color="white", linewidth=0.4)
        ax.tick_params(which="minor", length=0)
        ax.set_xticks(range(0, 24, 3))
        ax.set_xticklabels([f"{h:02d}h" for h in range(0, 24, 3)],
                           fontsize=7.5, fontfamily=FONT)
        ax.set_yticks(range(12))
        ax.set_yticklabels(MONTH_ABBR, fontsize=8, fontfamily=FONT)

        cb = fig.colorbar(im, ax=ax, fraction=0.018, pad=0.01, aspect=14)
        cb.set_label(unit, fontsize=7.5, fontfamily=FONT, labelpad=5)
        cb.ax.tick_params(labelsize=7)
        ax.set_title(label, fontsize=9.5, fontfamily=FONT,
                     fontweight="bold", loc="left", pad=5)
        ax.set_ylabel("Month", fontsize=8, fontfamily=FONT, labelpad=4)
        ax.tick_params(labelsize=7.5)
        for sp in ax.spines.values():
            sp.set_linewidth(0.4)

    axes[-1].set_xlabel("Hour of Day", fontsize=9, fontfamily=FONT, labelpad=6)
    fig.suptitle(
        "Diurnal and Seasonal Climatology \u2014 NUS Campus Meteorological Network (2025)\n"
        "Mean across 40 stations",
        fontsize=12, fontfamily=FONT, fontweight="bold", y=1.005
    )
    fig.tight_layout(h_pad=1.2)
    _save(fig, save_path)
    return fig


def plot_radials(save_path: str = None):
    """Annual radial climatology for all six variables (Fig 6a style).

    Each panel shows hourly observations plotted by day-of-year on a polar
    axis, with the network-wide daily mean and ±1 s.d. band overlaid.

    Parameters
    ----------
    save_path : str, optional
        File path to save the figure.

    Returns
    -------
    matplotlib.figure.Figure
    """
    _apply_style()
    long_df = load_all()
    long_df = long_df.copy()
    long_df.loc[long_df["station"] == PRESSURE_OUTLIER, "AtmPress Ave (hPa)"] = np.nan

    if not isinstance(long_df.index, pd.DatetimeIndex):
        long_df.index = pd.to_datetime(long_df.index)
    long_df["hour"] = long_df.index.hour
    long_df["doy"]  = long_df.index.dayofyear

    fig, axs = plt.subplots(2, 3, figsize=(18, 13),
                             subplot_kw={"projection": "polar"})
    fig.patch.set_facecolor("white")

    for ax, (col, label, unit, lc, _) in zip(axs.flat, VARS):
        cfg = _RADIAL_CFG[col]
        src = long_df.copy()

        if col == "WindDir Ave (degrees)":
            _draw_wind_rose(ax, src)
            wr_handles = [
                mpatches.Patch(facecolor=_HOUR_CMAP(0.0),     alpha=0.88, label="00h (midnight)"),
                mpatches.Patch(facecolor=_HOUR_CMAP(12 / 23), alpha=0.88, label="12h (noon)"),
                mpatches.Patch(facecolor=_HOUR_CMAP(18 / 23), alpha=0.88, label="18h (dusk)"),
            ]
            ax.legend(handles=wr_handles,
                      title="Stacked by hour", title_fontsize=5.0,
                      bbox_to_anchor=(0.5, -0.03), loc="upper center",
                      fontsize=5.2, framealpha=0.92, edgecolor="#dddddd",
                      fancybox=False, ncol=3, columnspacing=0.5,
                      handlelength=0.9, handletextpad=0.4, borderpad=0.4,
                      prop={"family": FONT})
            continue

        grp_m = src.groupby(["doy", "hour"])[col].mean().reset_index()
        grp_s = src.groupby(["doy", "hour"])[col].std().reset_index()
        grp_s[col] = grp_s[col].fillna(0)
        vmin_v = float(np.nanpercentile(grp_m[col], 2))
        vmax_v = float(np.nanpercentile(grp_m[col], 98))

        mean_mask = grp_m["hour"].between(7, 18).values if cfg["daytime_only"] else None
        mc = MEAN_COLORS.get(col)

        _setup_polar(ax)
        _draw_radial(
            ax,
            doy       = grp_m["doy"].values,
            hour      = grp_m["hour"].values,
            val       = grp_m[col].values,
            vmin      = vmin_v, vmax = vmax_v, lc = lc,
            std       = grp_s[col].values,
            show_mean = cfg["show_mean"],
            mean_mask = mean_mask,
            mean_color= mc,
        )
        _add_month_labels(ax)
        ax.text(0, 0, "\n".join(cfg["center"]),
                ha="center", va="center", fontsize=7,
                fontfamily=FONT, color="#333333",
                multialignment="center", zorder=10)
        _annotate_scale(ax, vmin_v, vmax_v, unit)
        if cfg["line_label"]:
            _add_panel_legend(ax, lc, cfg["line_label"],
                              has_band=cfg["has_band"], mean_color=mc)

    # Shared hour-of-day colorbar
    sm = plt.cm.ScalarMappable(cmap=_HOUR_CMAP, norm=Normalize(vmin=0, vmax=23))
    sm.set_array([])
    cbar = fig.colorbar(sm, ax=axs.ravel().tolist(),
                        orientation="horizontal", fraction=0.025,
                        pad=0.04, aspect=50)
    cbar.set_label("Hour of Day", fontsize=9, fontfamily=FONT, labelpad=5)
    cbar.set_ticks([0, 6, 12, 18, 23])
    cbar.set_ticklabels(["00h", "06h", "12h", "18h", "23h"])
    cbar.ax.tick_params(labelsize=8)

    fig.suptitle(
        "Annual Radial Climatology \u2014 NUS Campus Meteorological Network (2025)\n"
        "Each point = hourly network mean; colour = hour of day",
        fontsize=11, fontfamily=FONT, fontweight="bold", y=1.01
    )
    _save(fig, save_path)
    return fig


def plot_imputation_examples(save_path: str = None):
    """Three representative gap-fill panels (observed vs XGBoost spatial fill).

    Shows a medium gap (WS40 Air Temperature), a longer gap (WS02 Atmospheric
    Pressure), and a very long gap (WS34 Global Radiation, first 720 h shown).

    Parameters
    ----------
    save_path : str, optional
        File path to save the figure.

    Returns
    -------
    matplotlib.figure.Figure
    """
    _apply_style()

    VAR_COLOR = {
        "AirTemp Ave (C)":      "#bd0026",
        "AtmPress Ave (hPa)":   "#023858",
        "GlobalRad Ave (W/m2)": "#e05c00",
    }
    VAR_LABEL = {
        "AirTemp Ave (C)":      "Air Temperature (\u00b0C)",
        "AtmPress Ave (hPa)":   "Atmospheric Pressure (hPa)",
        "GlobalRad Ave (W/m2)": "Global Radiation (W m\u207b\u00b2)",
    }
    FLAG_COL = {v: v.split()[0] + "_flag" for v in VAR_COLOR}

    EXAMPLES = [
        ("WS40", "AirTemp Ave (C)",       96,  500),
        ("WS02", "AtmPress Ave (hPa)",   120,  720),
        ("WS34", "GlobalRad Ave (W/m2)",  96,  720),
    ]
    COL_FILL = "#ebebeb"

    def _load_pair(ws, var):
        orig_df = load_station(ws, imputed=False)
        imp_df  = load_station(ws, imputed=True)
        return orig_df[var], imp_df[var], imp_df[FLAG_COL[var]]

    def _longest_s2(flags):
        s2 = (flags == 2).values
        runs, start = [], None
        for i, v in enumerate(s2):
            if v and start is None:  start = i
            elif not v and start is not None:
                runs.append((start, i - 1)); start = None
        if start is not None:
            runs.append((start, len(s2) - 1))
        if not runs:
            return None, None
        return max(runs, key=lambda r: r[1] - r[0])

    fig, axes = plt.subplots(3, 1, figsize=(10, 9))
    fig.subplots_adjust(hspace=0.55)

    for ax, (ws, var, ctx_h, max_disp_h), panel in zip(axes, EXAMPLES, ["a","b","c"]):
        orig, imp_vals, flags = _load_pair(ws, var)
        col_obs = VAR_COLOR[var]

        run_start, run_end = _longest_s2(flags)
        if run_start is None:
            ax.set_visible(False); continue

        gap_len  = run_end - run_start + 1
        disp_end = run_start + min(gap_len, max_disp_h)
        win_s    = max(0, run_start - ctx_h)
        win_e    = min(len(flags) - 1, disp_end + ctx_h)

        idx   = flags.index
        t     = idx[win_s : win_e + 1]
        obs_w = orig.iloc[win_s : win_e + 1]
        imp_w = imp_vals.iloc[win_s : win_e + 1]
        fl_w  = flags.iloc[win_s : win_e + 1]

        gap_t0 = idx[run_start]
        gap_t1 = idx[min(run_end, win_e)]

        ax.axvspan(gap_t0, gap_t1, color=COL_FILL, zorder=0)

        gap_mask = (t >= gap_t0) & (t <= gap_t1)
        ax.plot(t[gap_mask], imp_w[gap_mask], color=col_obs, lw=1.3,
                linestyle="--", alpha=0.85, zorder=2)

        obs_plot = obs_w.copy().where(fl_w == 0)
        ax.plot(t, obs_plot, color=col_obs, lw=1.5, linestyle="-", zorder=3)

        ax.set_ylabel(VAR_LABEL[var], fontsize=8.5)
        ax.tick_params(axis="both", labelsize=8)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
        ax.xaxis.set_major_locator(mdates.AutoDateLocator(minticks=4, maxticks=8))
        plt.setp(ax.get_xticklabels(), rotation=25, ha="right")

        mid_t = gap_t0 + (gap_t1 - gap_t0) / 2
        y0, y1 = ax.get_ylim()
        ann = (f"{gap_len} h gap  (first {max_disp_h} h shown)"
               if gap_len > max_disp_h else f"{gap_len} h gap")
        ax.text(mid_t, y0 + 0.94 * (y1 - y0), ann,
                ha="center", va="top", fontsize=7.5,
                color="#555555", style="italic")
        ax.text(0.01, 0.97, f"({panel})  {ws}", transform=ax.transAxes,
                fontsize=9, fontweight="bold", va="top")

    fig.legend(
        handles=[
            Line2D([0], [0], color="#888888", lw=1.5, linestyle="-",  label="Observed"),
            Line2D([0], [0], color="#888888", lw=1.3, linestyle="--", label="Imputed \u2014 XGBoost spatial regression"),
            mpatches.Patch(facecolor=COL_FILL, edgecolor="#aaaaaa",   label="Gap region"),
        ],
        loc="lower center", ncol=3, fontsize=8.5, frameon=True,
        bbox_to_anchor=(0.5, -0.04)
    )
    fig.suptitle("Representative gap-fill examples", fontsize=11, y=1.01)
    _save(fig, save_path)
    return fig
