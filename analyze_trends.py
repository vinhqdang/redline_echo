"""
Tracks the HOLC-grade outcome gap across every CDC/ATSDR SVI vintage the
mirrored archive carries for census tracts (2010-2022), to check whether
the disparity documented in analyze.py is a one-year artifact or a durable
pattern.

Run download_data.py first (the SVI clone includes all vintages already,
not just 2010). See README.md, section "Persistence over time", for how
to read the output and the caveat about the 2020 poverty-threshold
redefinition (100% FPL -> 150% FPL) breaking strict comparability of the
poverty-rate column across the 2018/2020 boundary.
"""
import os

import pandas as pd

from analyze import DATA_DIR, HOLC_PATH, build_tract_scores, load_holc_flat

SVI_TRACT_DIR = os.path.join(DATA_DIR, "cdc-svi", "csv", "tract")

# Column names and scaling drift across CDC/ATSDR SVI redesigns.
# poverty_definition documents the 2020 threshold change (100% -> 150% FPL);
# treat pre/post-2020 poverty rates as related but not strictly comparable.
YEAR_SCHEMAS = {
    2010: dict(pov="E_P_POV", pov_pct=False, pci="E_PCI", minority="P_MINORITY", minority_pct=False, poverty_definition="100% FPL"),
    2014: dict(pov="EP_POV", pov_pct=True, pci="E_PCI", minority="EP_MINRTY", minority_pct=True, poverty_definition="100% FPL"),
    2016: dict(pov="EP_POV", pov_pct=True, pci="E_PCI", minority="EP_MINRTY", minority_pct=True, poverty_definition="100% FPL"),
    2018: dict(pov="EP_POV", pov_pct=True, pci="E_PCI", minority="EP_MINRTY", minority_pct=True, poverty_definition="100% FPL"),
    2020: dict(pov="EP_POV150", pov_pct=True, pci=None, minority="EP_MINRTY", minority_pct=True, poverty_definition="150% FPL"),
    2022: dict(pov="EP_POV150", pov_pct=True, pci=None, minority="EP_MINRTY", minority_pct=True, poverty_definition="150% FPL"),
}


def load_svi_year(year: int, schema: dict) -> pd.DataFrame:
    path = os.path.join(SVI_TRACT_DIR, f"SVI_{year}_US.csv")
    raw = pd.read_csv(path, dtype={"FIPS": str}, low_memory=False)
    raw["FIPS"] = raw["FIPS"].str.zfill(11)

    df = pd.DataFrame({"FIPS": raw["FIPS"]})
    df["poverty_rate"] = pd.to_numeric(raw[schema["pov"]], errors="coerce")
    df["minority_pct"] = pd.to_numeric(raw[schema["minority"]], errors="coerce")
    if not schema["pov_pct"]:
        df["poverty_rate"] *= 100
    if not schema["minority_pct"]:
        df["minority_pct"] *= 100
    # both scales use -999 (or a fraction of it) as a suppressed/missing sentinel
    df = df[(df["poverty_rate"] >= 0) & (df["minority_pct"] >= 0)]

    if schema["pci"]:
        pci = pd.to_numeric(raw[schema["pci"]], errors="coerce")
        df["per_capita_income"] = pci.where(pci > 0)
    else:
        df["per_capita_income"] = pd.NA
    return df


def main():
    print("Loading HOLC crosswalk...")
    tract_scores = build_tract_scores(load_holc_flat(HOLC_PATH))
    print(f"  {len(tract_scores):,} tracts with HOLC coverage\n")

    rows = []
    for year, schema in sorted(YEAR_SCHEMAS.items()):
        svi = load_svi_year(year, schema)
        merged = tract_scores.merge(svi, left_on="GEOID10", right_on="FIPS", how="inner")
        a = merged[merged.dominant_grade == "A"]
        d = merged[merged.dominant_grade == "D"]
        row = {
            "year": year,
            "poverty_definition": schema["poverty_definition"],
            "n_tracts": len(merged),
            "A_poverty_pct": round(a.poverty_rate.mean(), 1),
            "D_poverty_pct": round(d.poverty_rate.mean(), 1),
            "poverty_ratio_D_over_A": round(d.poverty_rate.mean() / a.poverty_rate.mean(), 2),
            "A_minority_pct": round(a.minority_pct.mean(), 1),
            "D_minority_pct": round(d.minority_pct.mean(), 1),
            "HRS_vs_poverty_r": round(merged["HRS"].corr(merged["poverty_rate"]), 3),
        }
        if schema["pci"]:
            row["A_income"] = round(a.per_capita_income.mean(), 0)
            row["D_income"] = round(d.per_capita_income.mean(), 0)
            row["income_ratio_A_over_D"] = round(a.per_capita_income.mean() / d.per_capita_income.mean(), 2)
        rows.append(row)

    trend = pd.DataFrame(rows)
    trend.to_csv("holc_trend_by_year.csv", index=False)
    pd.set_option("display.width", 160)
    print("=" * 70)
    print("A-vs-D GAP BY SVI VINTAGE, 2010-2022")
    print("=" * 70)
    print(trend.to_string(index=False))
    print(
        "\nNote: 2020/2022 poverty rate uses a 150%-of-federal-poverty-line\n"
        "threshold (CDC/ATSDR's 2020 SVI redesign); 2010-2018 use the 100%\n"
        "threshold. The poverty ratio is still informative within each\n"
        "definition era but a jump exactly at 2018->2020 is partly a\n"
        "measurement artifact, not a real-world level shift. Per capita\n"
        "income was dropped from SVI in the 2020 redesign, so no income\n"
        "figures are available for 2020/2022."
    )


if __name__ == "__main__":
    main()
