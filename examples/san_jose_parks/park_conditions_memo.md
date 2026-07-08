# Park Maintenance Investment Priority Analysis

**Source:** City of San Jose Park Condition Assessment (open data,
published weekly) · 2021-2025 · analyzed 2026-07-08

## Summary

In the 2025 assessment cycle, 265
parks were scored; the citywide average condition is
87.2/100. 21 parks score below
the 70-point condition floor, 84 have declined 5+
points since their first assessment, and 70 sit in
the lowest quartile of the Healthy Places Index (the ActivateSJ equity
lens).

## Priority findings

- **2 parks carry all three flags** (poor + declining +
  high-equity-need) and are the strongest candidates for the next
  maintenance/C&C dollar: McLaughlin Park, Meadowfair Park.
- **Systemic asset gap:** Drinking Fountains is the weakest category
  citywide (avg 64.47/100;
  46.63% of parks below 70) - a program-level
  funding case, not a park-by-park one.
- **District picture:** Council District 8 averages
  81.06/100 vs. District 5 at
  90.14/100 - relevant to targeting the
  district-based Construction & Conveyance tax funds.

## Method (fully transparent)

One assessment per park-year (annual Summer survey preferred). Three
boolean flags: condition (<70/100), declining (-5 pts or more since first
year), equity (HPI ≤ 25th percentile). Priority tier = flag count. Every
figure is computed in `scripts/park_conditions.py`; no modeling, no
weights to argue about.

## Recommended next steps

1. Validate tier-3 parks against current CIP project list and C&C fund
   balances by district (this toolkit's `fund_summary` view).
2. Cost the drinking fountains gap as a single program line for
   the next budget development cycle.
3. Re-run weekly as new assessments post; scores move when crews do.
