"""
Cross-checks the HOLC-grade outcome gap against the most recent U.S.
government tract-level data that actually exists: the Census Bureau's
American Community Survey (ACS) 5-year estimates, pulled live from
api.census.gov rather than a mirror.

No published dataset covers anything close to 2026 yet (CDC/ATSDR's SVI
tops out at 2022 - see README.md, "Persistence over time"). ACS 5-year
2020-2024 (vintage "2024") is the most current tract-level release as of
this analysis and is used here as the closest available substitute.

Requires a free Census API key (https://api.census.gov/data/key_signup.html)
in the CENSUS_API_KEY environment variable. Run download_data.py and
analyze.py first (this reuses their HOLC-loading code and needs
merged_holc_svi.csv for the SVI-based comparison rows).
"""
import json
import os
import time
import urllib.error
import urllib.request

import pandas as pd

from analyze import load_tract_scores, print_correlations, print_grade_summary

API_KEY = os.environ["CENSUS_API_KEY"]
VINTAGE = 2024  # ACS 2020-2024 5-year estimates: most recent tract-level release available
BASE = f"https://api.census.gov/data/{VINTAGE}/acs/acs5"
SUBJECT_BASE = f"https://api.census.gov/data/{VINTAGE}/acs/acs5/subject"

# 50 states + DC; HOLC coverage is mainland US cities only, so territories are skipped.
STATE_FIPS = [f"{i:02d}" for i in range(1, 57) if f"{i:02d}" not in ("03", "07", "14", "43", "52")]


def fetch_state(base_url: str, get_vars: str, state: str) -> pd.DataFrame:
    url = f"{base_url}?get={get_vars}&for=tract:*&in=state:{state}&key={API_KEY}"
    with urllib.request.urlopen(url, timeout=30) as resp:
        rows = json.loads(resp.read())
    return pd.DataFrame(rows[1:], columns=rows[0])


def fetch_all_states(base_url: str, get_vars: str) -> pd.DataFrame:
    frames = []
    for state in STATE_FIPS:
        for attempt in range(3):
            try:
                frames.append(fetch_state(base_url, get_vars, state))
                break
            except urllib.error.HTTPError as e:
                if attempt == 2:
                    raise
                time.sleep(2 * (attempt + 1))
        time.sleep(0.2)  # be polite to a free shared API
    return pd.concat(frames, ignore_index=True)


def main():
    print(f"Pulling ACS {VINTAGE} 5-year tract data for 50 states + DC "
          "(~150 requests, a couple of minutes)...")

    income_race = fetch_all_states(BASE, "B19301_001E,B03002_001E,B03002_003E")
    poverty = fetch_all_states(SUBJECT_BASE, "S1701_C03_001E")

    acs = income_race.merge(poverty, on=["state", "county", "tract"])
    acs["GEOID"] = acs["state"] + acs["county"] + acs["tract"]
    acs["per_capita_income"] = pd.to_numeric(acs["B19301_001E"], errors="coerce")
    total_pop = pd.to_numeric(acs["B03002_001E"], errors="coerce")
    white_alone = pd.to_numeric(acs["B03002_003E"], errors="coerce")
    acs["minority_pct"] = 100 * (1 - white_alone / total_pop)
    acs["poverty_rate"] = pd.to_numeric(acs["S1701_C03_001E"], errors="coerce")
    acs = acs[(acs["per_capita_income"] > 0) & (acs["poverty_rate"] >= 0) & total_pop.gt(0)]
    acs = acs[["GEOID", "per_capita_income", "minority_pct", "poverty_rate"]]
    acs.to_csv("acs_2024_tracts.csv", index=False)
    print(f"  {len(acs):,} tracts with valid ACS {VINTAGE} estimates\n")

    tract_scores = load_tract_scores()

    merged = tract_scores.merge(acs, left_on="GEOID10", right_on="GEOID", how="inner")
    print(f"Merged: {len(merged):,} tracts have both HOLC grade and ACS {VINTAGE} data")
    print(
        "(Note: ACS 2020-2024 uses 2020 census tract boundaries; the HOLC\n"
        " crosswalk here uses 2010 boundaries, so some tracts that split or\n"
        " merged in the 2020 redistricting won't match on GEOID and are\n"
        " dropped, the same way 2020/2022 SVI already handled this.)\n"
    )

    print_grade_summary(
        merged,
        dict(
            n_tracts=("GEOID10", "count"),
            mean_poverty_rate=("poverty_rate", "mean"),
            mean_per_capita_income=("per_capita_income", "mean"),
            mean_pct_minority=("minority_pct", "mean"),
        ),
        f"MEAN OUTCOMES BY DOMINANT HOLC GRADE, ACS {VINTAGE - 4}-{VINTAGE} 5-YEAR ESTIMATES",
    )

    a, d = merged[merged.dominant_grade == "A"], merged[merged.dominant_grade == "D"]
    print(f"\nPoverty ratio D/A:  {d.poverty_rate.mean() / a.poverty_rate.mean():.2f}x")
    print(f"Income ratio A/D:   {a.per_capita_income.mean() / d.per_capita_income.mean():.2f}x")
    print_correlations(
        merged,
        [("poverty_rate", "poverty"), ("per_capita_income", "income"), ("minority_pct", "pct minority")],
        f"CORRELATION: Historic Redlining Score vs ACS {VINTAGE} outcomes",
    )


if __name__ == "__main__":
    main()
