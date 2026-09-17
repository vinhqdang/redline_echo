"""
Produces the additional figures used in the manuscript submitted to
Environment and Planning B: Urban Analytics and City Science (see
README.md, "Manuscript status"): the Chicago/national HOLC map, the
poverty-ratio persistence trend chart, and the tract-level HRS-vs-poverty
scatter. These are separate from visualize.py's two summary charts,
which are unrelated to any specific manuscript and are kept as the
README's own headline figures.

Run download_data.py and analyze.py first (needs data/holc_crosswalk.geojson
and merged_holc_svi.csv). Run analyze_trends.py first for the trend chart
(needs holc_trend_by_year.csv). Downloads a small (~90KB) public-domain US
state-boundary GeoJSON on first run, used only as map background context.

Requires the `shapely` package (see requirements.txt).
"""
import json
import os
import urllib.request

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MplPolygon
from matplotlib.collections import PatchCollection
import numpy as np
import pandas as pd
from shapely.geometry import shape

from analyze import DATA_DIR, HOLC_PATH

OUT_DIR = "charts"
GRADES = ["A", "B", "C", "D"]
GRADE_COLORS = {"A": "#2c7bb6", "B": "#abd9e9", "C": "#fdae61", "D": "#d7191c"}

US_STATES_URL = "https://raw.githubusercontent.com/python-visualization/folium/main/examples/data/us-states.json"
US_STATES_PATH = os.path.join(DATA_DIR, "us-states.geojson")

MERGED_SVI_PATH = "merged_holc_svi.csv"
TREND_PATH = "holc_trend_by_year.csv"


def download_us_states():
    if os.path.exists(US_STATES_PATH):
        return
    print(f"Downloading US state boundary outlines (~90KB) to {US_STATES_PATH}...")
    urllib.request.urlretrieve(US_STATES_URL, US_STATES_PATH)


def chicago_and_national_map_figure():
    """Figure 1 in the EPB manuscript: (a) Chicago 1937 HOLC polygons,
    (b) national bubble map of the D/A poverty-rate ratio by city."""
    download_us_states()

    print("Loading HOLC crosswalk geometry (51,000+ polygons)...")
    with open(HOLC_PATH) as f:
        crosswalk = json.load(f)

    chicago_polys, geo_rows = [], []
    for feat in crosswalk["features"]:
        p = feat["properties"]
        grade = str(p.get("grade", "")).strip()
        if grade not in GRADE_COLORS:
            continue
        try:
            geom = shape(feat["geometry"])
        except Exception:
            continue
        if p.get("city") == "Chicago":
            chicago_polys.append((geom, grade))
        centroid = geom.centroid
        geo_rows.append({"city": p.get("city"), "GEOID10": p.get("GEOID10"), "lon": centroid.x, "lat": centroid.y})

    geo = pd.DataFrame(geo_rows).dropna(subset=["city", "GEOID10"])
    geo["GEOID10"] = geo["GEOID10"].astype(str)
    tract_city = geo.groupby("GEOID10")["city"].agg(lambda s: s.value_counts().idxmax())
    city_centroid = geo.groupby("city")[["lon", "lat"]].mean()

    svi = pd.read_csv(MERGED_SVI_PATH, dtype={"GEOID10": str})
    svi = svi.merge(tract_city.rename("city"), left_on="GEOID10", right_index=True, how="inner")

    city_stats = []
    for city, g in svi.groupby("city"):
        a = g.loc[g.dominant_grade == "A", "E_P_POV"]
        d = g.loc[g.dominant_grade == "D", "E_P_POV"]
        if len(a) >= 3 and len(d) >= 3 and a.mean() > 0:
            city_stats.append({"city": city, "n_tracts": len(g), "ratio": d.mean() / a.mean()})
    city_stats = pd.DataFrame(city_stats).merge(city_centroid, on="city")
    print(f"  {len(city_stats)} cities with enough A- and D-graded tracts for a ratio")

    with open(US_STATES_PATH) as f:
        states = json.load(f)

    fig, (ax_chi, ax_us) = plt.subplots(1, 2, figsize=(13, 6.5))

    # (a) Chicago
    for geom, grade in chicago_polys:
        polys = geom.geoms if geom.geom_type == "MultiPolygon" else [geom]
        for poly in polys:
            xs, ys = poly.exterior.xy
            ax_chi.fill(xs, ys, facecolor=GRADE_COLORS[grade], edgecolor="white", linewidth=0.2)
    ax_chi.set_aspect("equal")
    ax_chi.set_xticks([])
    ax_chi.set_yticks([])
    ax_chi.set_title("(a) 1937 HOLC grades, Chicago, IL", fontsize=11)
    handles = [plt.Rectangle((0, 0), 1, 1, color=GRADE_COLORS[g]) for g in GRADES]
    ax_chi.legend(handles, GRADES, loc="lower left", fontsize=8, title="HOLC grade")

    # (b) national bubble map
    patches = []
    for feat in states["features"]:
        geom = feat["geometry"]
        polys = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
        for poly in polys:
            patches.append(MplPolygon(poly[0], closed=True))
    ax_us.add_collection(PatchCollection(patches, facecolor="#f0f0f0", edgecolor="white", linewidth=0.6, zorder=1))
    sizes = 15 + city_stats["n_tracts"] * 0.8
    sc = ax_us.scatter(
        city_stats.lon, city_stats.lat, s=sizes, c=city_stats.ratio,
        cmap="RdYlBu_r", vmin=1.0, vmax=4.0, edgecolor="black", linewidth=0.4, zorder=2, alpha=0.85,
    )
    fig.colorbar(sc, ax=ax_us, shrink=0.75, pad=0.02, label="D/A poverty-rate ratio")
    ax_us.set_xlim(-127, -66)
    ax_us.set_ylim(24, 50)
    ax_us.set_aspect(1.3)
    ax_us.set_xticks([])
    ax_us.set_yticks([])
    for spine in ax_us.spines.values():
        spine.set_visible(False)
    ax_us.set_title(f"(b) D/A poverty-rate ratio, {len(city_stats)} cities", fontsize=11)

    fig.tight_layout()
    path = os.path.join(OUT_DIR, "epb_fig1_holc_maps.png")
    fig.savefig(path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"[saved] {path}")


def trend_ratio_chart():
    """Figure 2 in the EPB manuscript: D/A poverty-ratio persistence, 2010-2022."""
    trend = pd.read_csv(TREND_PATH)
    fig, ax = plt.subplots(figsize=(7, 5))
    ax.plot(trend.year, trend.poverty_ratio_D_over_A, "o-", color="#d7191c", linewidth=2)
    ax.axvline(2019, color="gray", linestyle="--", linewidth=0.8)
    ax.text(2019.3, trend.poverty_ratio_D_over_A.min(), "threshold\nredefinition", fontsize=8, color="gray")
    ax.set_xlabel("SVI vintage year")
    ax.set_ylabel("D-graded / A-graded poverty rate")
    ax.set_title("Persistence of the HOLC grade poverty gap, 2010-2022")
    fig.tight_layout()
    path = os.path.join(OUT_DIR, "epb_fig2_trend_ratio.png")
    fig.savefig(path, dpi=200)
    plt.close(fig)
    print(f"[saved] {path}")


def hrs_scatter_chart():
    """Figure 3 in the EPB manuscript: every tract, HRS vs 2010 poverty rate."""
    svi = pd.read_csv(MERGED_SVI_PATH)
    x = svi["HRS"].values
    y = 100 * svi["E_P_POV"].values
    slope, intercept = np.polyfit(x, y, 1)
    r = np.corrcoef(x, y)[0, 1]

    fig, ax = plt.subplots(figsize=(7, 5.5))
    hb = ax.hexbin(x, y, gridsize=45, cmap="viridis", mincnt=1, bins="log")
    xs = np.linspace(x.min(), x.max(), 100)
    ax.plot(xs, slope * xs + intercept, color="#d7191c", linewidth=1.5, label=f"OLS fit ($r={r:.2f}$)")
    fig.colorbar(hb, ax=ax, label="tracts per hexagonal bin (log scale)")
    ax.set_xlabel("Historic Redlining Score (1 = grade A, 4 = grade D)")
    ax.set_ylabel("2010 tract poverty rate (%)")
    ax.set_title(f"Every tract, not just grade means (n={len(svi):,})")
    ax.legend(loc="upper left", fontsize=9)
    fig.tight_layout()
    path = os.path.join(OUT_DIR, "epb_fig3_hrs_scatter.png")
    fig.savefig(path, dpi=200)
    plt.close(fig)
    print(f"[saved] {path}")
    print(f"  slope={slope:.3f} intercept={intercept:.3f} r={r:.3f}")


if __name__ == "__main__":
    os.makedirs(OUT_DIR, exist_ok=True)
    chicago_and_national_map_figure()
    trend_ratio_chart()
    hrs_scatter_chart()
