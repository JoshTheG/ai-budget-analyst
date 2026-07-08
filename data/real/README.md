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
