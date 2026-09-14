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

## Files

- `download_data.py` — fetches both source files into `data/`
- `analyze.py` — builds the HRS, joins, prints the summary table,
  correlations, and A-vs-D comparison; saves `merged_holc_svi.csv`
- `requirements.txt` — just `pandas`

## Running it

```bash
pip install -r requirements.txt
python download_data.py   # ~120MB download, takes a minute
python analyze.py
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
HOLC/SVI sources. So this extension is still open: it needs to run
from a machine with direct access to FEMA/EPA, or a GitHub-mirrored
copy of the NRI/EJScreen tract tables needs to be located first.
