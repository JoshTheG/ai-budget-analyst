"""Generate a sample dataset shaped like a City of San Jose PRNS
operating-budget export: division x category x fiscal year, adopted
budget vs. actuals plus revenue estimate vs. actual.

ILLUSTRATIVE DATA. Division names mirror the real PRNS structure; the
dollar figures are representative, not the City's actual numbers.
Replace with a real export from sanjoseca.opengov.com for live use.
"""

import csv
import random
from pathlib import Path

random.seed(42)

DIVISIONS = {
    "Administrative Services": 12.0,
    "Parks Maintenance & Operations": 38.0,
    "Recreation & Community Services": 34.0,
    "Community Facilities Development": 9.0,
    "Happy Hollow Park & Zoo": 16.0,
    "Strategic Support": 7.0,
}
CATEGORIES = {"Personal Services": 0.72, "Non-Personal/Equipment": 0.28}
YEARS = ["FY 2022-23", "FY 2023-24", "FY 2024-25", "FY 2025-26"]
GROWTH = 1.045  # nominal annual growth

rows = []
for y_i, fy in enumerate(YEARS):
    for div, base_m in DIVISIONS.items():
        for cat, share in CATEGORIES.items():
            budget = base_m * 1_000_000 * share * (GROWTH ** y_i)
            budget *= random.uniform(0.98, 1.02)
            actual = budget * random.uniform(0.88, 1.06)
            # build in a story: zoo overruns, facilities dev underspends
            if div == "Happy Hollow Park & Zoo":
                actual = budget * random.uniform(1.03, 1.09)
            if div == "Community Facilities Development":
                actual = budget * random.uniform(0.80, 0.90)
            rev_b = budget * {"Administrative Services": 0.05,
                              "Parks Maintenance & Operations": 0.10,
                              "Recreation & Community Services": 0.45,
                              "Community Facilities Development": 0.02,
                              "Happy Hollow Park & Zoo": 0.55,
                              "Strategic Support": 0.01}[div]
            rev_a = rev_b * random.uniform(0.85, 1.10)
            rows.append({
                "Fiscal Year": fy,
                "Division": div,
                "Expenditure Category": cat,
                "Adopted Budget": round(budget, 2),
                "Actual Expenditure": round(actual, 2),
                "Revenue Estimate": round(rev_b, 2),
                "Actual Revenue": round(rev_a, 2),
            })

out = Path(__file__).parent / "sample_prns_operating_budget.csv"
with out.open("w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)
print(f"wrote {out} ({len(rows)} rows)")
# EOF-SENTINEL
