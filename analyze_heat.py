"""
Joins HOLC grades to the Census Bureau's Community Resilience Estimates
(CRE) for Heat, 2022 — the one dataset in this project that measures
actual heat exposure (not a risk score or pollution proxy): days per
year at or above a 90 F heat index, peak wet-bulb temperature, and the
modeled share of the population with 3+ heat-vulnerability risk factors.

Run download_data.py first. See README.md, "Direct heat exposure:
Census Community Resilience Estimates", for where this comes from
(www2.census.gov, found via the Census Bureau's own CRE-Heat product
page after FEMA's tile-only heat-severity raster turned out to have no
public API for raw pixel values) and the caveat on regional-climate
confounding — LONG_90_DAY mostly reflects which state a tract is in,
not urban heat-island effects specifically.
"""
import os

import pandas as pd

from analyze import HOLC_PATH, build_tract_scores, load_holc_flat

DATA_DIR = "data"
CRE_HEAT_PATH = os.path.join(DATA_DIR, "cre22_heat_tract.csv")


def load_cre_heat(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, dtype={"STATE": str, "COUNTY": str, "TRACT": str}, encoding="latin1")
    df["GEOID"] = df["GEO_ID"].str.removeprefix("1400000US")
    return df[["GEOID", "LONG_90_DAY", "MAX_WBT", "PRED3_PE"]].rename(
        columns={"LONG_90_DAY": "days_90f_heat_index", "MAX_WBT": "max_wet_bulb_temp", "PRED3_PE": "pct_high_heat_vulnerability"}
    )


def main():
    print("Loading HOLC crosswalk...")
    tract_scores = build_tract_scores(load_holc_flat(HOLC_PATH))
    print(f"  {len(tract_scores):,} tracts with HOLC coverage\n")

    print("Loading Census CRE Heat 2022...")
    cre = load_cre_heat(CRE_HEAT_PATH)
    print(f"  {len(cre):,} tracts with CRE Heat data\n")

    merged = tract_scores.merge(cre, left_on="GEOID10", right_on="GEOID", how="inner")
    merged.to_csv("merged_holc_heat.csv", index=False)
    print(f"Merged: {len(merged):,} tracts have both HOLC grade and CRE Heat data\n")

    summary = (
        merged.groupby("dominant_grade")
        .agg(
            n_tracts=("GEOID10", "count"),
            mean_days_90f=("days_90f_heat_index", "mean"),
            mean_max_wet_bulb=("max_wet_bulb_temp", "mean"),
            mean_pct_high_vulnerability=("pct_high_heat_vulnerability", "mean"),
        )
        .reindex(["A", "B", "C", "D"])
        .round(2)
    )
    print("=" * 70)
    print("MEAN HEAT EXPOSURE BY DOMINANT HOLC GRADE (Census CRE 2022)")
    print("=" * 70)
    print(summary.to_string())

    print("\n" + "=" * 70)
    print("CORRELATION: Historic Redlining Score vs heat exposure")
    print("=" * 70)
    for col, label in [
        ("days_90f_heat_index", "days/year >= 90F heat index"),
        ("max_wet_bulb_temp", "peak wet-bulb temperature"),
        ("pct_high_heat_vulnerability", "% pop. with 3+ heat risk factors"),
    ]:
        print(f"HRS vs {label}: r = {merged['HRS'].corr(merged[col]):.3f}")

    a, d = merged[merged.dominant_grade == "A"], merged[merged.dominant_grade == "D"]
    print(f"\nHigh-vulnerability pop. % ratio D/A: {d.pct_high_heat_vulnerability.mean() / a.pct_high_heat_vulnerability.mean():.2f}x")

    print(
        "\nNote: days-above-90F and peak wet-bulb temperature are dominated\n"
        "by which state/climate zone a tract sits in (Arizona vs. Minnesota),\n"
        "not by within-city redlining patterns - HOLC cities aren't evenly\n"
        "spread across climate zones, so a raw national correlation on\n"
        "those two columns conflates 'which region got redlined' with\n"
        "'how much hotter is the redlined part of a given city'. The\n"
        "pct_high_heat_vulnerability figure is CDC/Census's own\n"
        "population-risk-factor composite (age, health, poverty, AC\n"
        "access) and is less climate-confounded, closer in spirit to the\n"
        "socioeconomic-vulnerability measures used throughout this project."
    )


if __name__ == "__main__":
    main()
