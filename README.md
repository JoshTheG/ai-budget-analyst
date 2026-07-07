# AI Budget Analyst

Automated budget analysis for any tabular financial dataset: point it at a
CSV or Excel export and it produces what a municipal budget analyst
produces — a variance workbook, trend and forecast tables, anomaly flags,
and a written budget memo.

Built around one design rule: **the LLM never does arithmetic.** All
figures are computed deterministically with pandas/NumPy. Claude does what
LLMs are actually good at — reading an unfamiliar schema, deciding which
findings matter, and writing clear prose around verified numbers. Every
number in the memo is traceable to code, and the schema mapping is saved
to `schema_mapping.json` as an audit trail.

## Architecture

```
 any CSV/XLSX ──▶ ingest.py ──▶ profile (columns, dtypes, samples)
                                    │
                                    ▼
                  schema_mapper.py  ── Claude maps columns to canonical
                                       roles (period, entity, budget,
                                       actual, revenue...); keyword
                                       heuristics without an API key
                                    │
                                    ▼
                  analysis.py       ── deterministic pandas/NumPy:
                                       variance, trends, least-squares
                                       forecast, z-score anomaly flags
                                    │
                                    ▼
                  agent.py          ── Claude writes the memo / answers
                                       questions using ONLY the computed
                                       facts; template memo in mock mode
                                    │
                                    ▼
                  report.py         ── budget_analysis.xlsx + budget_memo.md
```

## Quickstart

```bash
pip install -r requirements.txt
python data/make_sample.py                      # build the demo dataset
python -m budget_analyst analyze data/sample_prns_operating_budget.csv
```

Outputs land in `output/`: `budget_analysis.xlsx`, `budget_memo.md`,
`schema_mapping.json`.

Ask questions in plain English:

```bash
python -m budget_analyst ask data/sample_prns_operating_budget.csv \
    "Which division is furthest over budget and by how much?"
```

## Mock mode vs. live mode

Without `ANTHROPIC_API_KEY` set, the tool runs fully offline: heuristic
schema mapping plus a template memo — built from the same computed facts,
so the numbers are identical. With a key (and `pip install anthropic`),
Claude handles schema mapping, memo writing, and Q&A:

```bash
export ANTHROPIC_API_KEY=sk-ant-...
python -m budget_analyst analyze yourdata.csv
```

Force mock mode anytime with `--mock`.

## Using real City of San Jose data

- **Operating budget:** export CSV views from the City's OpenGov
  transparency platform: https://sanjoseca.opengov.com/transparency
- **311 service requests (updated daily):**
  https://data.sanjoseca.gov/dataset/311-service-request-data
- **Capital budget / C&C funds:** budget documents at
  https://www.sanjoseca.gov/your-government/departments-offices/office-of-the-city-manager/budget

The bundled `data/sample_prns_operating_budget.csv` is **illustrative**:
it mirrors the real PRNS division structure but the dollars are
representative, not the City's actual figures. Swap in a real export
before citing any numbers.

## Project structure

```
budget_analyst/
    ingest.py         load + profile any CSV/Excel
    schema_mapper.py  Claude (or heuristic) column-role mapping
    analysis.py       deterministic variance/trend/forecast/anomaly math
    agent.py          Claude narration + Q&A, mock fallback
    report.py         Excel workbook + memo writer
    cli.py            analyze / ask commands
data/                 sample generator + demo dataset
examples/   