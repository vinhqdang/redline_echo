# Redline Echo

Redlining (HOLC) vs. present-day socioeconomic outcomes: joins the
official 1930s HOLC redlining grades to 2010 census tracts and looks
at how poverty, income, and racial composition in those same tracts
looked ~70 years later, per the 2010 CDC/ATSDR Social Vulnerability
Index — the 1937 map decisions still echoing in the 2010 data, decades
after the Fair Housing Act (1968) outlawed redlining.

This was built to sanity-check a claim used in a *Teaching Sociology*
manuscript (module: students build a climate-risk model, audit it for
racial/income disparity, then compare results to historical HOLC maps).
Before trusting the literature's causal story, we pulled real data
ourselves and re-derived the basic pattern.

## What this DOES show

A real, verifiable, monotonic relationship: tracts historically graded
"D" (Hazardous) by HOLC are, in 2010 data:
- **2.75x** poorer (27.4% vs. 10.0% poverty rate) than "A"-graded tracts
- earning **47%** as much per capita ($22,183 vs. $47,454)
- more concentrated with racial/ethnic minority residents (65.7% vs. 28.2%)

...more than 40 years after redlining was outlawed (Fair Housing Act,
1968) and ~70 years after the maps were drawn. Correlation between the
continuous Historic Redlining Score and these outcomes is moderate
(r ≈ 0.34–0.36) — real, but far from deterministic. Many "D" tracts are
not poor today; many "A" tracts are. See Shreevastava et al. 2025
(cited in the manuscript) for why: present-day investment can and does
change outcomes independent of the historical grade.

## Is this discrimination?

Two separate claims, often conflated, are worth pulling apart:

1. **The 1930s grading was explicitly discriminatory by design, not just in
   effect.** This isn't inferred from the data below — it's documented in
   the historical record. HOLC's own area-description methodology directed
   assessors to record a neighborhood's racial and immigrant composition,
   and treated the presence of Black, Jewish, or immigrant residents as a
   negative factor that could push a grade down to "C" or "D" regardless of
   the physical housing stock. This is established by historians working
   directly from the original HOLC records (the same underlying source as
   the crosswalk used here) — see Jackson, *Crabgrass Frontier* (1985) and
   Rothstein, *The Color of Law* (2017); the Mapping Inequality project
   (Nelson et al., cited above) documents it directly from the scanned
   HOLC area-description forms. So the grade variable used throughout this
   project (`HRS`/`dominant_grade`) is not a neutral risk score that
   happened to correlate with race — race was one of the inputs.
2. **Whether today's gap is still driven by that same mechanism, or by
   something else entirely, is an empirical question** — and the one this
   project can actually test with real data. The regression checks below
   ask specifically whether the historic grade still predicts 2010
   outcomes *after* accounting for a tract's current racial composition
   and its state. If the grade's effect vanished once you control for
   today's demographics, that would suggest the "gap" is really just
   today's segregation restated. It doesn't vanish (see "Statistical
   robustness"): the historic grade keeps independent predictive power,
   consistent with a durable, place-based effect — most plausibly
   decades of investment, lending, and zoning decisions that tracked the
   original grade — separate from whoever happens to live there today.

Neither point makes this a causal, individual-level claim ("this specific
person was discriminated against because of this specific grade"). Both
together are why "echo" is the right word for what's in this repo: a
documented discriminatory input, and a measurable, statistically robust
signal of it 80-90 years later.

## What this DOES NOT show

**This is socioeconomic data (poverty, income, race), not physical
climate-risk data (heat, flood exposure).** The published papers this
manuscript relies on (Hoffman, Shandas & Pendleton 2020; Lane et al.
2022; Salazar-Miranda et al. 2024) establish the second half of the
causal chain — that this socioeconomic sorting translates into
measurably higher heat and flood exposure via reduced tree canopy,
more impervious surface, and less drainage investment. This project
does not independently re-verify that second link, because building
this without direct access to FEMA/NOAA/EPA endpoints, we could only
reach data mirrored on GitHub (see Data Sources). **From an environment
with unrestricted internet access, extending this to pull real
climate-risk data is the natural next step** — see "Extending this"
below for where to start (and for what was already tried).

This is also **correlational, not causal**, at the tract level (unlike
Salazar-Miranda et al. 2024's boundary-discontinuity design, which
compares near-identical properties on opposite sides of a HOLC
boundary line — a much stronger design than the simple grouped means
computed here).

## Data sources

| Dataset | Source | License/Attribution | Vintage |
|---|---|---|---|
| HOLC grades → 2010 census tract crosswalk | [American Panorama / Mapping Inequality](https://dsl.richmond.edu/panorama/redlining/), mirrored at `github.com/americanpanorama/mapping-inequality-census-crosswalk` | Nelson, Robert K., et al., Digital Scholarship Lab, University of Richmond. CC BY-NC-SA 4.0 | 2010 tracts |
| Social Vulnerability Index (poverty, income, minority %) | CDC/ATSDR SVI 2010, mirrored at `github.com/lpiep/cdc-svi` (original: `svi.cdc.gov`) | Public domain, U.S. government work | 2010 tracts |

Both files are large (HOLC GeoJSON ~67MB, SVI CSV ~55MB); `download_data.py`
fetches them fresh rather than bundling them.

## Methodology

1. Flatten the HOLC GeoJSON's `features[].properties` into a table:
   `area_id, city, state, grade, GEOID10, pct_tract`. `pct_tract` is the
   fraction of a 2010 census tract covered by that HOLC polygon (tracts
   can span multiple HOLC-graded areas).
2. Keep only standard grades A/B/C/D (drop rare/nonstandard "E"/"F" and
   blank grades — 51,866 raw records → 43,257 clean records).
3. For each tract, compute:
   - **Historic Redlining Score (HRS)**: area-weighted mean of grade
     (A=1 … D=4), following the approach used in Meier & Mitchell
     (2021), the crosswalk source cited by Salazar-Miranda et al. (2024).
   - **Dominant grade**: the single grade covering the largest area
     share of the tract, for simpler group comparisons.
4. Join to SVI 2010 on 11-digit tract FIPS (`GEOID10` = `FIPS`).
5. Compare group means (by dominant grade) and Pearson correlations
   (HRS vs. each outcome, continuous).

Result: 16,500 tracts had HOLC coverage; 16,372 of those also had valid
SVI data (some SVI records use -999 sentinel values for suppressed/
missing estimates and are dropped).

## Persistence over time (2010-2022)

The CDC/ATSDR mirror used here (`lpiep/cdc-svi`) carries every published
SVI tract vintage, not just 2010. `analyze_trends.py` re-runs the A-vs-D
comparison for each one:

| Year | Poverty definition | A poverty % | D poverty % | D/A ratio | A income | D income | A/D income ratio | HRS↔poverty r |
|---|---|---|---|---|---|---|---|---|
| 2010 | 100% FPL | 9.9 | 27.3 | 2.74 | $47,454 | $22,183 | 2.14 | 0.357 |
| 2014 | 100% FPL | 11.1 | 29.3 | 2.65 | $49,677 | $23,727 | 2.09 | 0.359 |
| 2016 | 100% FPL | 11.1 | 28.6 | 2.57 | $51,786 | $25,284 | 2.05 | 0.360 |
| 2018 | 100% FPL | 10.6 | 26.6 | 2.51 | $56,161 | $28,282 | 1.99 | 0.345 |
| 2020 | 150% FPL | 14.9 | 35.3 | 2.37 | — | — | — | 0.346 |
| 2022 | 150% FPL | 15.3 | 34.6 | 2.27 | — | — | — | 0.340 |

CDC/ATSDR redefined the poverty-rate variable in the 2020 redesign (100%
of the federal poverty line → 150%) and dropped per-capita income
entirely, so the pre/post-2020 rows aren't on an identical scale — that
redefinition, not a real-world jump, explains most of the 2018→2020 level
change. Within each definition era, though, the pattern is consistent:
the gap has been *narrowing slowly* (D/A poverty ratio 2.74 → 2.51 across
2010-2018; 2.37 → 2.27 across 2020-2022) while staying large, and the
HRS-poverty correlation is essentially flat (0.34-0.36) across all six
vintages spanning 12 years. This is not a one-year artifact of the 2010
snapshot in "What this DOES show" above.

## Statistical robustness

Group means and a bivariate correlation can both be driven by a
confound — e.g., if D grades happened to cluster in poorer states
regardless of redlining. `regression.py` runs OLS (heteroskedasticity-robust
SEs) on the 2010 merged data to check this:

| Outcome | Specification | HRS coefficient | p-value | R² |
|---|---|---|---|---|
| Poverty rate (%) | HRS only | +6.82 pts/grade | <1e-300 | 0.130 |
| Poverty rate (%) | + state fixed effects | +7.16 pts/grade | <1e-300 | 0.201 |
| Poverty rate (%) | + state FE + current minority % | +4.09 pts/grade | 2.6e-256 | 0.395 |
| Per capita income ($) | HRS only | −$7,809/grade | <1e-280 | 0.123 |
| Per capita income ($) | + state fixed effects | −$8,305/grade | <1e-300 | 0.176 |
| % minority (2010) | HRS only | +14.14 pts/grade | <1e-300 | 0.118 |
| % minority (2010) | + state fixed effects | +13.31 pts/grade | <1e-300 | 0.238 |

Two things stand out:

- Adding state fixed effects **doesn't shrink** the HRS coefficient — it
  grows slightly. The gap isn't an artifact of which states got more D
  grades; it holds comparing tracts within the same state.
- Adding today's minority % as a control cuts the poverty coefficient
  roughly in half (+6.8 → +4.1 points per grade step) but doesn't remove
  it, and it stays overwhelmingly significant. The historic grade is
  carrying real information about 2010 poverty beyond what today's racial
  composition alone explains — see "Is this discrimination?" above for
  why that matters.

This is still observational data: no instrument, no boundary-discontinuity
design (unlike Salazar-Miranda et al. 2024), and no control for other
plausible confounds (pre-1930s housing stock, density, distance to
downtown). It rules out "it's just states" and "it's just who lives there
now" as full explanations; it does not establish the specific causal
mechanism.

## Files

- `download_data.py` — fetches both source files into `data/` (the SVI
  clone includes every vintage 2000-2022, not just 2010)
- `analyze.py` — builds the HRS, joins, prints the summary table,
  correlations, and A-vs-D comparison; saves `merged_holc_svi.csv`
- `analyze_trends.py` — reruns the A-vs-D comparison across every SVI
  vintage 2010-2022 to check persistence over time; saves
  `holc_trend_by_year.csv`
- `regression.py` — OLS checks (state fixed effects, controlling for
  current racial composition) on top of `merged_holc_svi.csv`
- `requirements.txt` — `pandas`, `statsmodels`

## Running it

```bash
pip install -r requirements.txt
python download_data.py   # ~1.5GB (full multi-year SVI archive), a few minutes
python analyze.py           # 2010 snapshot: group means, correlations
python analyze_trends.py    # same comparison across 2010-2022
python regression.py        # OLS robustness checks (needs analyze.py run first)
```

## Extending this

To actually complete the causal chain (redlining → socioeconomic
sorting → **physical climate risk**), the natural next additions are:

- **FEMA National Risk Index**: tract-level flood/heat/wildfire risk
  scores, bulk CSV download at https://hazards.fema.gov/nri/data-resources
- **EPA EJScreen**: tract-level environmental indicators (heat, air
  quality, proximity to hazards). EPA discontinued public access to
  EJScreen in February 2025; third-party mirrors of the last published
  vintage exist (e.g. screening-tools.com, a Zenodo archive) but were
  not reachable from this environment either — see below.
- **NOAA/NASA land surface temperature**: for a direct heat measure
  rather than a risk index (see Shreevastava et al. 2025's use of
  ECOSTRESS data, cited in the manuscript, for the gold-standard
  version of this)

Joining any of these to `merged_holc_svi.csv` on `GEOID10` would let
you test the actual heat/flood link directly, the same way the cited
papers do — rather than relying on their published numbers.

**Tried from this environment (2026-09):** `hazards.fema.gov` and
`www.epa.gov` both returned HTTP 403/404 through the outbound proxy
here, and a Zenodo mirror of archived EJScreen data timed out. Only
GitHub-hosted mirrors (`raw.githubusercontent.com`, arbitrary public
repos) were reachable — the same constraint noted above for the
HOLC/SVI sources. Searched further for a GitHub-native tract-level heat
dataset as a substitute and checked two candidates: `US-Cities-UHI-Analysis`
(README describes a `UHI_Cities_2015_2022.csv` output, but the repo as
published doesn't actually contain that file, and it's 5 cities'
monthly urban-vs-rural means anyway — not tract-resolved, so it
couldn't join to individual HOLC grades even if present) and
`LA-neighborhood-heat` (a real census-tract-scale heat modeling
pipeline for LA, but it computes its inputs from satellite providers
directly at runtime rather than shipping data in the repo, so using it
still needs non-GitHub network access this environment doesn't have).
So this extension is still open: it needs to run from a machine with
direct access to FEMA/EPA/NOAA, or a GitHub-mirrored copy of the actual
NRI/EJScreen/LST tract tables needs to be located first.
