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

from analyze import load_tract_scores, merge_and_save, print_correlations, print_grade_summary

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
    tract_scores = load_tract_scores()

    print("Loading EPA EJScreen (this parses a ~190MB .dbf, a minute or so)...")
    ejscreen = load_ejscreen(EJSCREEN_DBF)
    print(f"  {len(ejscreen):,} tracts with EJScreen data\n")

    merged = merge_and_save(tract_scores, ejscreen, "GEOID10", "GEOID", "merged_holc_ejscreen.csv", "EJScreen")

    print_grade_summary(
        merged,
        dict(
            n_tracts=("GEOID10", "count"),
            mean_air_pollution_pctl=("air_pollution_pctl", "mean"),
            mean_traffic_pctl=("traffic_pctl", "mean"),
            mean_hazard_site_pctl=("hazard_site_pctl", "mean"),
            mean_lead_paint_pctl=("lead_paint_pctl", "mean"),
        ),
        "MEAN EJSCREEN NATIONAL PERCENTILES BY DOMINANT HOLC GRADE\n"
        "(0-100 national percentile; higher = more pollution burden / older housing stock)",
    )

    print_correlations(
        merged,
        [
            ("air_pollution_pctl", "air pollution (PM2.5/ozone/diesel PM avg)"),
            ("traffic_pctl", "traffic proximity"),
            ("hazard_site_pctl", "hazardous-site proximity (Superfund + TSDF avg)"),
            ("lead_paint_pctl", "lead paint indicator (pre-1960 housing)"),
        ],
        "CORRELATION: Historic Redlining Score vs EJScreen indicators",
    )

    a, d = merged[merged.dominant_grade == "A"], merged[merged.dominant_grade == "D"]
    print(f"\nAir pollution ratio D/A:    {d.air_pollution_pctl.mean() / a.air_pollution_pctl.mean():.2f}x")
    print(f"Hazard site proximity D/A: {d.hazard_site_pctl.mean() / a.hazard_site_pctl.mean():.2f}x")
    print(f"Lead paint indicator D/A:  {d.lead_paint_pctl.mean() / a.lead_paint_pctl.mean():.2f}x")


if __name__ == "__main__":
    main()
