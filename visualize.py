"""
Produces the two summary charts referenced in README.md: a grade-by-grade
bar panel across every outcome this project measured, and a single
"punchline" chart ranking every HRS correlation computed across all five
datasets side by side.

Run analyze.py, analyze_climate.py, analyze_ejscreen.py, and
analyze_heat.py first (this reads their merged_holc_*.csv outputs).
Saves charts/by_grade.png and charts/correlation_summary.png.
"""
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

OUT_DIR = "charts"
GRADE_ORDER = ["A", "B", "C", "D"]
GRADE_COLORS = {"A": "#2c7bb6", "B": "#abd9e9", "C": "#fdae61", "D": "#d7191c"}

# (source csv, column, subplot title, y-axis label)
BY_GRADE_METRICS = [
    ("merged_holc_svi.csv", "E_P_POV", "Poverty rate\n(SVI 2010)", "poverty rate", lambda s: s * 100),
    ("merged_holc_svi.csv", "E_PCI", "Per capita income\n(SVI 2010)", "$", lambda s: s),
    ("merged_holc_svi.csv", "P_MINORITY", "% minority\n(SVI 2010)", "%", lambda s: s * 100),
    ("merged_holc_nri.csv", "HWAV_RISKS", "Heat wave risk\n(FEMA NRI)", "national percentile", lambda s: s),
    ("merged_holc_ejscreen.csv", "air_pollution_pctl", "Air pollution\n(EPA EJScreen)", "national percentile", lambda s: s),
    ("merged_holc_heat.csv", "pct_high_heat_vulnerability", "% high heat vulnerability\n(Census CRE 2022)", "%", lambda s: s),
]

# (source csv, column, label, category) - computed fresh from the merged
# data each run, not hardcoded, so the chart can't drift from the actual
# numbers. analyze_acs.py's ACS 2020-2024 cross-check needs a Census API
# key and doesn't persist a merged file, so it's reported in README.md
# directly rather than duplicated here.
CORRELATIONS = [
    ("merged_holc_svi.csv", "E_P_POV", "SVI: poverty rate", "socioeconomic"),
    ("merged_holc_svi.csv", "E_PCI", "SVI: per capita income", "socioeconomic"),
    ("merged_holc_svi.csv", "P_MINORITY", "SVI: % minority", "socioeconomic"),
    ("merged_holc_ejscreen.csv", "hazard_site_pctl", "EJScreen: hazardous-site proximity", "pollution"),
    ("merged_holc_ejscreen.csv", "air_pollution_pctl", "EJScreen: air pollution", "pollution"),
    ("merged_holc_ejscreen.csv", "traffic_pctl", "EJScreen: traffic proximity", "pollution"),
    ("merged_holc_ejscreen.csv", "lead_paint_pctl", "EJScreen: lead paint (pre-1960 housing)", "pollution"),
    ("merged_holc_heat.csv", "pct_high_heat_vulnerability", "CRE Heat: % high heat vulnerability", "heat/hazard"),
    ("merged_holc_nri.csv", "RISK_SCORE", "FEMA NRI: overall risk", "heat/hazard"),
    ("merged_holc_nri.csv", "HWAV_RISKS", "FEMA NRI: heat wave risk", "heat/hazard"),
    ("merged_holc_nri.csv", "FLOOD_RISKS", "FEMA NRI: flood risk", "heat/hazard"),
    ("merged_holc_nri.csv", "EAL_SCORE", "FEMA NRI: expected annual loss", "heat/hazard"),
    ("merged_holc_heat.csv", "days_90f_heat_index", "CRE Heat: days/yr >= 90F", "heat/hazard"),
    ("merged_holc_heat.csv", "max_wet_bulb_temp", "CRE Heat: peak wet-bulb temp", "heat/hazard"),
]
CATEGORY_COLORS = {"socioeconomic": "#2c7bb6", "pollution": "#fdae61", "heat/hazard": "#d7191c"}


def by_grade_chart():
    fig, axes = plt.subplots(2, 3, figsize=(13, 7))
    for ax, (csv_path, col, title, ylabel, transform) in zip(axes.flat, BY_GRADE_METRICS):
        df = pd.read_csv(csv_path)
        means = transform(df.groupby("dominant_grade")[col].mean()).reindex(GRADE_ORDER)
        ax.bar(GRADE_ORDER, means.values, color=[GRADE_COLORS[g] for g in GRADE_ORDER])
        ax.set_title(title, fontsize=10)
        ax.set_ylabel(ylabel, fontsize=9)
        ax.set_xlabel("HOLC grade (1930s)", fontsize=9)
        ax.tick_params(labelsize=9)
    fig.suptitle("Outcomes in 2010-2024 data, by 1930s HOLC grade", fontsize=13)
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    path = os.path.join(OUT_DIR, "by_grade.png")
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"[saved] {path}")


def correlation_summary_chart():
    computed = []
    for csv_path, col, label, category in CORRELATIONS:
        df = pd.read_csv(csv_path)
        computed.append((label, category, df["HRS"].corr(df[col])))

    rows = sorted(computed, key=lambda r: r[2])
    labels = [r[0] for r in rows]
    values = [r[2] for r in rows]
    colors = [CATEGORY_COLORS[r[1]] for r in rows]

    fig, ax = plt.subplots(figsize=(9, 7))
    ax.barh(labels, values, color=colors)
    ax.axvline(0, color="black", linewidth=0.8)
    ax.set_xlabel("correlation with Historic Redlining Score (r)")
    ax.set_title("How strongly does the 1930s HOLC grade predict each outcome?")
    ax.tick_params(labelsize=8)

    handles = [plt.Rectangle((0, 0), 1, 1, color=c) for c in CATEGORY_COLORS.values()]
    ax.legend(handles, CATEGORY_COLORS.keys(), loc="lower right", fontsize=8)
    fig.tight_layout()
    path = os.path.join(OUT_DIR, "correlation_summary.png")
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"[saved] {path}")


if __name__ == "__main__":
    os.makedirs(OUT_DIR, exist_ok=True)
    by_grade_chart()
    correlation_summary_chart()
