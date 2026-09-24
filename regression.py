"""
Regression checks on top of the group-mean/correlation results in
analyze.py: do the HOLC-grade outcome gaps survive controlling for state
(so it isn't just "the South is poorer and got more D grades"), for city
(so the comparison is between tracts graded differently within the same
city, which is the level HOLC actually graded at), and does the historic
grade predict today's poverty independently of today's racial
composition (or is it just relabeling the same thing)?

Standard errors are either heteroskedasticity-robust (HC1) or clustered
by HOLC city; tracts in the same city share unobserved local conditions,
so treating them as independent overstates precision.

Run analyze.py first (this reads merged_holc_svi.csv and the HOLC
crosswalk for each tract's city). See README.md, section "Statistical
robustness" and "Is this discrimination?", for how to read the
coefficients — this is still observational data (no instrument, no
discontinuity design), so city fixed effects rule out between-city
confounds, not every within-city one.
"""
import pandas as pd
import statsmodels.formula.api as smf

from analyze import HOLC_PATH, load_holc_flat

MERGED_PATH = "merged_holc_svi.csv"


def tract_cities() -> pd.DataFrame:
    """Each tract's HOLC city: the city of its largest-area-share polygon."""
    holc = load_holc_flat(HOLC_PATH)
    holc["city_id"] = holc["city"].astype(str) + ", " + holc["state"].astype(str)
    idx = holc.groupby("GEOID10")["pct_tract"].idxmax()
    return holc.loc[idx, ["GEOID10", "city_id"]]


def fit(formula: str, data: pd.DataFrame, cluster: bool = False) -> None:
    if cluster:
        model = smf.ols(formula, data=data).fit(cov_type="cluster", cov_kwds={"groups": data["city_id"]})
        se_label = "city-clustered SE"
    else:
        model = smf.ols(formula, data=data).fit(cov_type="HC1")  # tract outcomes are heteroskedastic
        se_label = "robust SE"
    coef, se, p = model.params["HRS"], model.bse["HRS"], model.pvalues["HRS"]
    print(f"  {formula}{'  [clustered by city]' if cluster else ''}")
    print(f"    HRS coef = {coef:+.3f}  ({se_label} {se:.3f}, p = {p:.2e})  "
          f"R² = {model.rsquared:.3f}  N = {int(model.nobs)}")


def main():
    df = pd.read_csv(MERGED_PATH, dtype={"GEOID10": str, "FIPS": str})
    df["poverty_pct"] = df["E_P_POV"] * 100
    df["minority_pct"] = df["P_MINORITY"] * 100
    df = df.merge(tract_cities(), on="GEOID10", how="inner")
    print(f"{len(df):,} tracts in {df['city_id'].nunique()} HOLC cities\n")

    print("=" * 70)
    print("OUTCOME: 2010 poverty rate (%), by HOLC Historic Redlining Score")
    print("(HRS: 1=A/best .. 4=D/hazardous)")
    print("=" * 70)
    fit("poverty_pct ~ HRS", df)
    fit("poverty_pct ~ HRS + C(STATE_ABBR)", df)
    fit("poverty_pct ~ HRS + minority_pct + C(STATE_ABBR)", df)
    fit("poverty_pct ~ HRS + C(city_id)", df, cluster=True)
    fit("poverty_pct ~ HRS + minority_pct + C(city_id)", df, cluster=True)

    print()
    print("=" * 70)
    print("OUTCOME: 2010 per capita income ($), by HRS")
    print("=" * 70)
    fit("E_PCI ~ HRS", df)
    fit("E_PCI ~ HRS + C(STATE_ABBR)", df)
    fit("E_PCI ~ HRS + C(city_id)", df, cluster=True)
    fit("E_PCI ~ HRS + minority_pct + C(city_id)", df, cluster=True)

    print()
    print("=" * 70)
    print("OUTCOME: 2010 % minority population, by HRS")
    print("(tests whether the historic grade predicts today's racial")
    print("composition independent of location — the closest thing here to")
    print("directly testing discriminatory persistence rather than a")
    print("generic poverty gap)")
    print("=" * 70)
    fit("minority_pct ~ HRS", df)
    fit("minority_pct ~ HRS + C(STATE_ABBR)", df)
    fit("minority_pct ~ HRS + C(city_id)", df, cluster=True)


if __name__ == "__main__":
    main()
