"""
Downloads the two source datasets used by analyze.py.

- HOLC redlining -> 2010 census tract crosswalk (American Panorama /
  Mapping Inequality, Digital Scholarship Lab, University of Richmond)
- CDC/ATSDR Social Vulnerability Index, 2010, tract level

Both are ~50-70MB. Run this once; analyze.py reads from ./data/.
See README.md for full source attribution and license notes.
"""
import os
import subprocess
import urllib.request

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


if __name__ == "__main__":
    os.makedirs(DATA_DIR, exist_ok=True)
    download_holc()
    download_svi()
    print("\nAll data downloaded. Run analyze.py next.")
