"""
Completes the physical-climate-risk half of the causal chain this project
could not reach for most of its history: joins HOLC grades to FEMA's
National Risk Index (NRI) tract-level natural hazard data, so the
heat/flood link doesn't have to rely on the cited papers' published
numbers alone (Hoffman, Shandas & Pendleton 2020; Lane et al. 2022).

Run download_data.py first (fetches NRI_Table_CensusTracts.csv, ~450MB).
See README.md, "Climate risk: FEMA National Risk Index", for why this
comes from a resilience.climate.gov / ArcGIS Hub mirror rather than
hazards.fema.gov or www.fema.gov directly (both unreachable from every
sandboxed environment tried in this project's history), and for the
caveat on what a NRI "risk score" actually measures.
"""
import os

import pandas as pd

from analyze import DATA_DIR, load_tract_scores, merge_and_save, print_correlations, print_grade_summary

NRI_PATH = os.path.join(DATA_DIR, "nri_census_tracts.csv")
NRI_COLUMNS = ["TRACTFIPS", "RISK_SCORE", "EAL_SCORE", "HWAV_RISKS", "RFLD_RISKS", "CFLD_RISKS"]


def load_nri(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, usecols=NRI_COLUMNS, dtype={"TRACTFIPS": str}, low_memory=False)
    df["TRACTFIPS"] = df["TRACTFIPS"].str.zfill(11)
    # a tract with no coastline/river exposure has no coastal/riverine flood
    # score at all (NaN), not a zero - average the two that exist per tract
    df["FLOOD_RISKS"] = df[["RFLD_RISKS", "CFLD_RISKS"]].mean(axis=1, skipna=True)
    return df[["TRACTFIPS", "RISK_SCORE", "EAL_SCORE", "HWAV_RISKS", "FLOOD_RISKS"]]


def main():
    tract_scores = load_tract_scores()

    print("Loading FEMA National Risk Index...")
    nri = load_nri(NRI_PATH)
    print(f"  {len(nri):,} tracts with NRI data\n")

    merged = merge_and_save(tract_scores, nri, "GEOID10", "TRACTFIPS", "merged_holc_nri.csv", "NRI")

    print_grade_summary(
        merged,
        dict(
            n_tracts=("GEOID10", "count"),
            mean_overall_risk=("RISK_SCORE", "mean"),
            mean_expected_annual_loss=("EAL_SCORE", "mean"),
            mean_heat_wave_risk=("HWAV_RISKS", "mean"),
            mean_flood_risk=("FLOOD_RISKS", "mean"),
        ),
        "MEAN FEMA NRI RISK SCORES BY DOMINANT HOLC GRADE\n(*_SCORE / *_RISKS are FEMA's 0-100 national percentiles)",
        decimals=2,
    )

    print_correlations(
        merged,
        [
            ("RISK_SCORE", "overall risk"),
            ("EAL_SCORE", "expected annual loss"),
            ("HWAV_RISKS", "heat wave risk"),
            ("FLOOD_RISKS", "flood risk (river+coastal avg)"),
        ],
        "CORRELATION: Historic Redlining Score vs NRI risk measures",
    )

    a, d = merged[merged.dominant_grade == "A"], merged[merged.dominant_grade == "D"]
    print(f"\nHeat wave risk ratio D/A: {d.HWAV_RISKS.mean() / a.HWAV_RISKS.mean():.2f}x")
    print(f"Flood risk ratio D/A:     {d.FLOOD_RISKS.mean() / a.FLOOD_RISKS.mean():.2f}x")

    print(
        "\nNote: each *_RISKS field is FEMA's own risk score for that hazard\n"
        "(expected loss weighted by frequency and exposure, normalized to a\n"
        "0-100 national percentile) - not a direct temperature or flood-depth\n"
        "reading. It's real hazard-risk data rather than a proxy inferred from\n"
        "socioeconomic outcomes, but it's still coarser than Shreevastava et\n"
        "al. 2025's direct ECOSTRESS land-surface-temperature measurements."
    )


if __name__ == "__main__":
    main()
