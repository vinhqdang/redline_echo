"""
Joins 1930s HOLC redlining grades to 2010 census tracts, joins those to
2010 CDC/ATSDR Social Vulnerability Index data, and reports how poverty,
income, and racial composition varied by historic HOLC grade.

Run download_data.py first. See README.md for methodology, data source
attribution, and — importantly — the caveats section on what this
analysis does and does not demonstrate (it's socioeconomic sorting,
not direct physical climate-risk data; correlational, not causal).
"""
import os
import json

import numpy as np
import pandas as pd

DATA_DIR = "data"
HOLC_PATH = os.path.join(DATA_DIR, "holc_crosswalk.geojson")
SVI_PATH = os.path.join(DATA_DIR, "cdc-svi", "csv", "tract", "SVI_2010_US.csv")

GRADE_TO_NUM = {"A": 1, "B": 2, "C": 3, "D": 4}


def load_holc_flat(path: str) -> pd.DataFrame:
    """Flatten the HOLC GeoJSON's properties into a table (geometry dropped)."""
    with open(path) as f:
        data = json.load(f)
    rows = [feat["properties"] for feat in data["features"]]
    df = pd.DataFrame(rows)[["area_id", "city", "state", "grade", "GEOID10", "pct_tract"]]
    df["grade"] = df["grade"].astype(str).str.strip()
    df = df[df["grade"].isin(GRADE_TO_NUM)].copy()
    df["GEOID10"] = df["GEOID10"].astype(str).str.zfill(11)
    df["grade_num"] = df["grade"].map(GRADE_TO_NUM)
    return df


def build_tract_scores(holc_flat: pd.DataFrame) -> pd.DataFrame:
    """
    Collapse (possibly multiple) HOLC polygons per tract into one row per
    tract: an area-weighted Historic Redlining Score (HRS, 1=A best,
    4=D worst) and the single dominant (largest-area-share) grade.
    """
    def agg(g: pd.DataFrame) -> pd.Series:
        w = g["pct_tract"]
        hrs = np.average(g["grade_num"], weights=w) if w.sum() > 0 else g["grade_num"].mean()
        dominant = g.loc[g["pct_tract"].idxmax(), "grade"]
        return pd.Series({"HRS": hrs, "dominant_grade": dominant, "n_polygons": len(g)})

    return holc_flat.groupby("GEOID10").apply(agg, include_groups=False).reset_index()


def load_svi(path: str) -> pd.DataFrame:
    svi = pd.read_csv(path, dtype={"FIPS": str}, low_memory=False)
    svi["FIPS"] = svi["FIPS"].str.zfill(11)
    cols = svi[["FIPS", "STATE_ABBR", "COUNTY", "E_TOTPOP", "E_P_POV", "E_PCI", "P_MINORITY"]].copy()
    for c in ["E_TOTPOP", "E_P_POV", "E_PCI", "P_MINORITY"]:
        cols[c] = pd.to_numeric(cols[c], errors="coerce")
    # SVI uses negative sentinel values (e.g. -999) for suppressed/missing estimates
    return cols[(cols["E_P_POV"] >= 0) & (cols["E_PCI"] > 0)]


def main():
    print("Loading HOLC crosswalk...")
    holc_flat = load_holc_flat(HOLC_PATH)
    print(f"  {len(holc_flat):,} clean HOLC polygon-tract records (grades A-D)")

    tract_scores = build_tract_scores(holc_flat)
    print(f"  {len(tract_scores):,} unique tracts with HOLC coverage")

    print("\nLoading SVI 2010...")
    svi = load_svi(SVI_PATH)
    print(f"  {len(svi):,} tracts with valid SVI estimates")

    merged = tract_scores.merge(svi, left_on="GEOID10", right_on="FIPS", how="inner")
    merged.to_csv("merged_holc_svi.csv", index=False)
    print(f"\nMerged: {len(merged):,} tracts have both HOLC grade and SVI data")
    print("  -> saved to merged_holc_svi.csv")

    print("\n" + "=" * 70)
    print("MEAN OUTCOMES BY DOMINANT HOLC GRADE")
    print("=" * 70)
    summary = (
        merged.groupby("dominant_grade")
        .agg(
            n_tracts=("GEOID10", "count"),
            mean_poverty_rate=("E_P_POV", "mean"),
            median_poverty_rate=("E_P_POV", "median"),
            mean_per_capita_income=("E_PCI", "mean"),
            mean_pct_minority=("P_MINORITY", "mean"),
        )
        .reindex(["A", "B", "C", "D"])
    )
    summary["mean_poverty_rate"] = (summary["mean_poverty_rate"] * 100).round(1)
    summary["median_poverty_rate"] = (summary["median_poverty_rate"] * 100).round(1)
    summary["mean_per_capita_income"] = summary["mean_per_capita_income"].round(0)
    summary["mean_pct_minority"] = (summary["mean_pct_minority"] * 100).round(1)
    print(summary.to_string())

    print("\n" + "=" * 70)
    print("CORRELATION: continuous Historic Redlining Score (1=A best, 4=D worst)")
    print("=" * 70)
    print(f"HRS vs poverty rate:      r = {merged['HRS'].corr(merged['E_P_POV']):.3f}")
    print(f"HRS vs per capita income: r = {merged['HRS'].corr(merged['E_PCI']):.3f}")
    print(f"HRS vs pct minority:      r = {merged['HRS'].corr(merged['P_MINORITY']):.3f}")

    print("\n" + "=" * 70)
    print("A vs D DIRECT COMPARISON")
    print("=" * 70)
    a = merged[merged.dominant_grade == "A"]
    d = merged[merged.dominant_grade == "D"]
    print(f"A-graded (n={len(a)}): poverty {a.E_P_POV.mean()*100:.1f}%, "
          f"income ${a.E_PCI.mean():,.0f}, minority {a.P_MINORITY.mean()*100:.1f}%")
    print(f"D-graded (n={len(d)}): poverty {d.E_P_POV.mean()*100:.1f}%, "
          f"income ${d.E_PCI.mean():,.0f}, minority {d.P_MINORITY.mean()*100:.1f}%")
    print(f"Income ratio A/D:  {a.E_PCI.mean()/d.E_PCI.mean():.2f}x")
    print(f"Poverty ratio D/A: {d.E_P_POV.mean()/a.E_P_POV.mean():.2f}x")

    print("\nReminder: this is socioeconomic data, not physical climate-risk\n"
          "data. See README.md 'What this does NOT show' before citing these\n"
          "numbers as evidence of heat/flood exposure.")


if __name__ == "__main__":
    main()
