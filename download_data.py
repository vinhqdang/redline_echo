"""
Downloads the source datasets used by analyze.py, analyze_trends.py,
analyze_climate.py, and analyze_ejscreen.py.

- HOLC redlining -> 2010 census tract crosswalk (American Panorama /
  Mapping Inequality, Digital Scholarship Lab, University of Richmond)
- CDC/ATSDR Social Vulnerability Index, every published tract vintage
- FEMA National Risk Index, tract level (natural hazard risk scores)
- EPA EJScreen, tract level (pollution burden, industrial-site proximity)

~700MB total. Run this once; analyze*.py read from ./data/.
See README.md for full source attribution, license notes, and (for the
NRI/EJScreen files) why they come from ArcGIS Hub re-uploads rather than
fema.gov/epa.gov directly.
"""
import os
import subprocess
import urllib.request
import zipfile

DATA_DIR = "data"

HOLC_URL = (
    "https://raw.githubusercontent.com/americanpanorama/"
    "mapping-inequality-census-crosswalk/main/"
    "MIv3Areas_2010TractCrosswalk.geojson"
)
HOLC_PATH = os.path.join(DATA_DIR, "holc_crosswalk.geojson")

SVI_REPO = "https://github.com/lpiep/cdc-svi.git"
SVI_CLONE_DIR = os.path.join(DATA_DIR, "cdc-svi")
SVI_CSV_RELATIVE = os.path.join("csv", "tract", "SVI_2010_US.csv")

# FEMA-authored National Risk Index, Census Tracts layer, republished as an
# ArcGIS Hub open dataset by resilience.climate.gov (item 9da4eeb936544335a6db0cd7a8448a51).
# hazards.fema.gov/nri/data-resources and www.fema.gov's own static file
# downloads return 403 from every sandboxed environment tried for this
# project; this Hub download endpoint doesn't.
NRI_URL = (
    "https://opendata.arcgis.com/api/v3/datasets/"
    "9da4eeb936544335a6db0cd7a8448a51_0/downloads/data"
    "?format=csv&spatialRefId=4326"
)
NRI_PATH = os.path.join(DATA_DIR, "nri_census_tracts.csv")

# EPA EJScreen 2.32, US tract percentiles, re-uploaded to ArcGIS as a
# shapefile by a third party (item 448f514d14204df7b4641e96a3fee52e) from
# EPA's own last-published release. epa.gov/EJScreen and gaftp.epa.gov
# are unreachable from every sandboxed environment tried for this project
# (EPA also discontinued public EJScreen access in Feb 2025); this
# re-upload of the official EPA data isn't. Only the .dbf attribute table
# is kept - the .shp geometry (~650MB) is dropped since only the tract
# FIPS + indicator values are needed here.
EJSCREEN_URL = (
    "https://www.arcgis.com/sharing/rest/content/items/"
    "448f514d14204df7b4641e96a3fee52e/data"
)
EJSCREEN_ZIP_PATH = os.path.join(DATA_DIR, "ejscreen_2024_tracts.zip")
EJSCREEN_DBF_PATH = os.path.join(DATA_DIR, "ejscreen_2024_tracts.dbf")
EJSCREEN_DBF_MEMBER = "EJSCREEN_Full_with_AS_CNMI_GU_VI.dbf"


def download_holc():
    if os.path.exists(HOLC_PATH):
        print(f"[skip] {HOLC_PATH} already exists")
        return
    print("Downloading HOLC crosswalk GeoJSON (~67MB)...")
    urllib.request.urlretrieve(HOLC_URL, HOLC_PATH)
    print(f"[done] saved to {HOLC_PATH}")


def download_svi():
    svi_csv_path = os.path.join(SVI_CLONE_DIR, SVI_CSV_RELATIVE)
    if os.path.exists(svi_csv_path):
        print(f"[skip] {svi_csv_path} already exists")
        return
    print("Cloning CDC SVI archive repo (~depth 1, includes 2010/2014 tract CSVs)...")
    subprocess.run(
        ["git", "clone", "--depth", "1", SVI_REPO, SVI_CLONE_DIR],
        check=True,
    )
    print(f"[done] SVI data at {svi_csv_path}")


def download_nri():
    if os.path.exists(NRI_PATH):
        print(f"[skip] {NRI_PATH} already exists")
        return
    print("Downloading FEMA National Risk Index, Census Tracts (~450MB)...")
    urllib.request.urlretrieve(NRI_URL, NRI_PATH)
    print(f"[done] saved to {NRI_PATH}")


def download_ejscreen():
    if os.path.exists(EJSCREEN_DBF_PATH):
        print(f"[skip] {EJSCREEN_DBF_PATH} already exists")
        return
    print("Downloading EPA EJScreen shapefile (~450MB zip)...")
    urllib.request.urlretrieve(EJSCREEN_URL, EJSCREEN_ZIP_PATH)
    print("Extracting attribute table (dropping the geometry files)...")
    with zipfile.ZipFile(EJSCREEN_ZIP_PATH) as zf:
        with zf.open(EJSCREEN_DBF_MEMBER) as src, open(EJSCREEN_DBF_PATH, "wb") as dst:
            dst.write(src.read())
    os.remove(EJSCREEN_ZIP_PATH)
    print(f"[done] saved to {EJSCREEN_DBF_PATH}")


if __name__ == "__main__":
    os.makedirs(DATA_DIR, exist_ok=True)
    download_holc()
    download_svi()
    download_nri()
    download_ejscreen()
    print("\nAll data downloaded. Run analyze.py next.")
