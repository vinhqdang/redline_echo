"""
Joins HOLC grades to EPA EJScreen (pollution burden, industrial-site
proximity, housing age) — a second, independent take on the physical
side of the causal chain, alongside analyze_climate.py's FEMA National
Risk Index comparison. EJScreen covers environmental *quality*
(air pollution, hazardous-site proximity) rather than natural-hazard
risk, so a different result here than in analyze_climate.py wouldn't be
a contradiction — they're measuring different things.

Run download_data.py first (fetches EJScreen 2.32 tract data as a
~450MB shapefile zip; only the ~190MB .dbf attribute table is kept —
see README.md, "Environmental quality: EPA EJScreen", for where this
comes from and why, same story as the FEMA NRI file: EPA's own
epa.gov/EJScreen domains are unreachable, but a third-party re-upload
of the same official data on ArcGIS Hub isn't).
"""
import os

import pandas as pd
from dbfread import DBF

from analyze import HOLC_PATH, build_tract_scores, load_holc_flat

DATA_DIR = "data"
EJSCREEN_DBF = os.path.join(DATA_DIR, "ejscreen_2024_tracts.dbf")

FIELDS = ["ID", "P_PM25", "P_OZONE", "P_DSLPM", "P_PTRAF", "P_PNPL", "P_PTSDF", "P_LDPNT"]


def load_ejscreen(path: str) -> pd.DataFrame:
    # declared as UTF-8 but a stray byte in an unrelated text field breaks
    # strict decoding; latin1 never raises and we only read numeric fields
    table = DBF(path, load=False, encoding="latin1")
    rows = [{f: rec[f] for f in FIELDS} for rec in table]
    df = pd.DataFrame(rows)
    df = df.rename(columns={"ID": "GEOID"})
    for col in FIELDS[1:]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["air_pollution_pctl"] = df[["P_PM25", "P_OZONE", "P_DSLPM"]].mean(axis=1)
    df["hazard_site_pctl"] = df[["P_PNPL", "P_PTSDF"]].mean(axis=1)
    df = df.rename(columns={"P_PTRAF": "traffic_pctl", "P_LDPNT": "lead_paint_pctl"})
    return df[["GEOID", "air_pollution_pctl", "traffic_pctl", "hazard_site_pctl", "lead_paint_pctl"]]


def main():
    print("Loading HOLC crosswalk...")
    tract_scores = build_tract_scores(load_holc_flat(HOLC_PATH))
    print(f"  {len(tract_scores):,} tracts with HOLC coverage\n")

    print("Loading EPA EJScreen (this parses a ~190MB .dbf, a minute or so)...")
    ejscreen = load_ejscreen(EJSCREEN_DBF)
    print(f"  {len(ejscreen):,} tracts with EJScreen data\n")

    merged = tract_scores.merge(ejscreen, left_on="GEOID10", right_on="GEOID", how="inner")
    merged.to_csv("merged_holc_ejscreen.csv", index=False)
    print(f"Merged: {len(merged):,} tracts have both HOLC grade and EJScreen data\n")

    summary = (
        merged.groupby("dominant_grade")
        .agg(
            n_tracts=("GEOID10", "count"),
            mean_air_pollution_pctl=("air_pollution_pctl", "mean"),
            mean_traffic_pctl=("traffic_pctl", "mean"),
            mean_hazard_site_pctl=("hazard_site_pctl", "mean"),
            mean_lead_paint_pctl=("lead_paint_pctl", "mean"),
        )
        .reindex(["A", "B", "C", "D"])
        .round(1)
    )
    print("=" * 70)
    print("MEAN EJSCREEN NATIONAL PERCENTILES BY DOMINANT HOLC GRADE")
    print("(0-100 national percentile; higher = more pollution burden /")
    print(" older housing stock)")
    print("=" * 70)
    print(summary.to_string())

    print("\n" + "=" * 70)
    print("CORRELATION: Historic Redlining Score vs EJScreen indicators")
    print("=" * 70)
    for col, label in [
        ("air_pollution_pctl", "air pollution (PM2.5/ozone/diesel PM avg)"),
        ("traffic_pctl", "traffic proximity"),
        ("hazard_site_pctl", "hazardous-site proximity (Superfund + TSDF avg)"),
        ("lead_paint_pctl", "lead paint indicator (pre-1960 housing)"),
    ]:
        print(f"HRS vs {label}: r = {merged['HRS'].corr(merged[col]):.3f}")

    a, d = merged[merged.dominant_grade == "A"], merged[merged.dominant_grade == "D"]
    print(f"\nAir pollution ratio D/A:    {d.air_pollution_pctl.mean() / a.air_pollution_pctl.mean():.2f}x")
    print(f"Hazard site proximity D/A: {d.hazard_site_pctl.mean() / a.hazard_site_pctl.mean():.2f}x")
    print(f"Lead paint indicator D/A:  {d.lead_paint_pctl.mean() / a.lead_paint_pctl.mean():.2f}x")


if __name__ == "__main__":
    main()
