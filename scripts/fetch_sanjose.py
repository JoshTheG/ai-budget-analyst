"""Download real, regularly-refreshed City of San Jose open datasets.

    python scripts/fetch_sanjose.py            # park condition assessment

Sources (City of San Jose open data portal, data.sanjoseca.gov):
- Park Condition Assessment (PCA): PRNS field-staff Survey123 scores by
  park and asset category, published WEEKLY. Package
  `park-condition-assessment`, ArcGIS layer 557.

Re-run anytime to refresh `data/real/` with the latest published data.
"""

from __future__ import annotations

import sys
import urllib.request
from pathlib import Path

DATASETS = {
    "park_condition_assessment.csv": (
        "https://gisdata-csj.opendata.arcgis.com/api/download/v1/items/"
        "0e71d67a90834400829f3b15b0ff630a/csv?layers=557"
    ),
}

OUT_DIR = Path(__file__).resolve().parents[1] / "data" / "real"


def fetch_all() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for name, url in DATASETS.items():
        dest = OUT_DIR / name
        print(f"downloading {name} ...")
        with urllib.request.urlopen(url, timeout=120) as resp:  # noqa: S310
            dest.write_bytes(resp.read())
        print(f"  wrote {dest} ({dest.stat().st_size:,} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(fetch_all())
