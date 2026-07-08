# Real City of San José open data

`park_condition_assessment.csv` is a snapshot of the City of San José
**Park Condition Assessment** dataset (PRNS field-staff Survey123 scores
by park and asset category, published weekly on the City's open data
portal): https://data.sanjoseca.gov/dataset/park-condition-assessment

Snapshot committed 2026-07-08. Refresh anytime:

```bash
python scripts/fetch_sanjose.py
```

Public data provided by the City of San José open data program. Scores
are the City's own field assessments; this repo adds analysis only
(`scripts/park_conditions.py`).

`opengov_prns_actuals_snapshot.csv` is a manual export from the City's
OpenGov transparency portal (sanjoseca.opengov.com): PRNS personal
services monthly actuals (September, FY2012-13 through FY2018-19,
General Fund + Cash Reserve Fund), downloaded 2026-07-08. A real
crosstab-format file — run it through the core pipeline:

```bash
python -m budget_analyst analyze data/real/opengov_prns_actuals_snapshot.csv
```
