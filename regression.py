"""
Regression checks on top of the group-mean/correlation results in
analyze.py: do the HOLC-grade outcome gaps survive controlling for state
(so it isn't just "the South is poorer and got more D grades"), and does
the historic grade predict today's poverty independently of today's
racial composition (or is it just relabeling the same thing)?

Run analyze.py first (this reads merged_holc_svi.csv). See README.md,
section "Statistical robustness" and "Is this discrimination?", for how
to read the coefficients — this is still observational data (no
instrument, no discontinuity design), so "controls for state" rules out
one obvious confound, not every confound.
"""
import pandas as pd
import statsmodels.formula.api as smf

MERGED_PATH = "merged_holc_svi.csv"


def fit(formula: str, data: pd.DataFrame) -> None:
    model = smf.ols(formula, data=data).fit(cov_type="HC1")  # robust SEs: tract outcomes are heteroskedastic
    coef, se, p = model.params["HRS"], model.bse["HRS"], model.pvalues["HRS"]
    print(f"  {formula}")
    print(f"    HRS coef = {coef:+.3f}  (robust SE {se:.3f}, p = {p:.2e})  "
          f"R² = {model.rsquared:.3f}  N = {int(model.nobs)}")


def main():
    df = pd.read_csv(MERGED_PATH, dtype={"GEOID10": str, "FIPS": str})
    df["poverty_pct"] = df["E_P_POV"] * 100
    df["minority_pct"] = df["P_MINORITY"] * 100

    print("=" * 70)
    print("OUTCOME: 2010 poverty rate (%), by HOLC Historic Redlining Score")
    print("(HRS: 1=A/best .. 4=D/hazardous)")
    print("=" * 70)
    fit("poverty_pct ~ HRS", df)
    fit("poverty_pct ~ HRS + C(STATE_ABBR)", df)
    fit("poverty_pct ~ HRS + minority_pct + C(STATE_ABBR)", df)

    print()
    print("=" * 70)
    print("OUTCOME: 2010 per capita income ($), by HRS")
    print("=" * 70)
    fit("E_PCI ~ HRS", df)
    fit("E_PCI ~ HRS + C(STATE_ABBR)", df)

    print()
    print("=" * 70)
    print("OUTCOME: 2010 % minority population, by HRS")
    print("(tests whether the historic grade predicts today's racial")
    print("composition independent of state — the closest thing here to")
    print("directly testing discriminatory persistence rather than a")
    print("generic poverty gap)")
    print("=" * 70)
    fit("minority_pct ~ HRS", df)
    fit("minority_pct ~ HRS + C(STATE_ABBR)", df)


if __name__ == "__main__":
    main()
