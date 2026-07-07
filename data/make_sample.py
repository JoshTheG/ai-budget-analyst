"""Generate the two demo datasets.

1. sample_prns_operating_budget.csv - shaped like a City of San Jose PRNS
   operating-budget export: division x category x fiscal year, adopted
   budget vs. actuals plus revenue estimate vs. actual.
2. sample_prns_capital_funds.csv - shaped like a capital monitoring
   extract: fund x project x fiscal year with appropriation, expended,
   encumbrance, and revenue columns, mirroring the fund portfolio the
   PRNS Capital Budget Unit oversees (Construction & Conveyance tax
   funds by council district, a parks bond fund, and the Park Trust Fund).

ILLUSTRATIVE DATA. Names mirror the real PRNS structure; the dollar
figures are representative, not the City's actual numbers. Replace with
a real export from sanjoseca.opengov.com for live use.
"""

import csv
import random
from pathlib import Path

random.seed(42)

HERE = Path(__file__).parent
YEARS = ["FY 2022-23", "FY 2023-24", "FY 2024-25", "FY 2025-26"]
GROWTH = 1.045  # nominal annual growth

# ---------------------------------------------------------------- operating
DIVISIONS = {
    "Administrative Services": 12.0,
    "Parks Maintenance & Operations": 38.0,
    "Recreation & Community Services": 34.0,
    "Community Facilities Development": 9.0,
    "Happy Hollow Park & Zoo": 16.0,
    "Strategic Support": 7.0,
}
CATEGORIES = {"Personal Services": 0.72, "Non-Personal/Equipment": 0.28}

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

out = HERE / "sample_prns_operating_budget.csv"
with out.open("w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)
print(f"wrote {out} ({len(rows)} rows)")

# ------------------------------------------------------------------ capital
FUNDS = ([f"C&C Tax Fund - Council District {d}" for d in range(1, 11)]
         + ["Parks & Rec Bond Projects Fund", "Park Trust Fund"])
PROJECT_TYPES = ["Playground Renovation", "Trail Segment", "Community Center HVAC",
                 "Sports Field Lighting", "Restroom Replacement", "Pool Rehab"]

cap_rows = []
for y_i, fy in enumerate(YEARS):
    for fund in FUNDS:
        n_projects = random.randint(2, 4)
        for i in range(n_projects):
            proj = f"{random.choice(PROJECT_TYPES)} #{i + 1}"
            approp = random.uniform(0.4, 6.0) * 1_000_000 * (GROWTH ** y_i)
            spent_pct = random.uniform(0.15, 0.85)
            enc_pct = random.uniform(0.05, min(0.30, 0.95 - spent_pct))
            expended = approp * spent_pct
            encumbered = approp * enc_pct
            # trust fund collects developer in-lieu fees; C&C gets tax receipts
            rev_est = approp * random.uniform(0.6, 1.1)
            rev_act = rev_est * random.uniform(0.8, 1.15)
            cap_rows.append({
                "Fiscal Year": fy,
                "Fund": fund,
                "Project": proj,
                "Appropriation": round(approp, 2),
                "Expended to Date": round(expended, 2),
                "Encumbrance": round(encumbered, 2),
                "Revenue Estimate": round(rev_est, 2),
                "Actual Revenue": round(rev_act, 2),
            })

out = HERE / "sample_prns_capital_funds.csv"
with out.open("w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(cap_rows[0].keys()))
    w.writeheader()
    w.writerows(cap_rows)
print(f"wrote {out} ({len(cap_rows)} rows)")
