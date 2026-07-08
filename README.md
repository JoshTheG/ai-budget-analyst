# AI Budget Analyst

A municipal budget analysis toolkit: point it at any CSV or Excel export —
operating or capital — and it produces what a budget office produces:

- a **formatted Excel variance workbook** (conditional highlighting,
  embedded budget-vs-actual chart, currency formats, summary sheet)
- a **written budget memo** with findings, risks, outlook, and actions
- a **4-slide PowerPoint briefing deck**
- a **live dashboard** that watches the file: keep the workbook open in
  Excel, hit save, and the KPIs, chart, and tables update themselves

It handles the data the way it actually arrives: multi-sheet workbooks,
report-title rows above the header, dollars stored as text like
`$1,234.56` or accounting negatives `(500.00)` — and it maps unfamiliar
column names onto analysis roles automatically.

Built around one design rule: **the LLM never does arithmetic.** All
figures are computed deterministically with pandas/NumPy. Claude does what
LLMs are actually good at — reading an unfamiliar schema, deciding which
findings matter, and writing clear prose around verified numbers. Without
an API key everything still runs, fully offline, on the same computed
facts. Every number is traceable to code, and the schema mapping is saved
to `schema_mapping.json` as an audit trail.

## What it computes

| Analysis | What you get |
|---|---|
| Variance | budget vs. actual by division/fund/project and by category, latest period |
| Encumbrances | available balance = budget − actual − encumbered; % committed |
| Revenue | collections vs. estimate/target, attainment %, weakest performers |
| Fund summary | per-fund appropriation, expended, encumbered, available, net activity — the reconciliation view for capital & special funds |
| Trend | totals by period with period-over-period change |
| Forecast | least-squares next-period projection with R² |
| Anomalies | z-score outlier flags on variance % |

Each analysis activates only when the data supports it: an operating
export gets division variance and revenue attainment; a capital extract
with fund/project/encumbrance columns also gets the fund reconciliation.

## Quickstart

```bash
pip install -r requirements.txt
python data/make_sample.py                      # build both demo datasets

# full analysis -> Excel workbook + memo
python -m budget_analyst analyze data/sample_prns_operating_budget.csv

# capital monitoring: funds, encumbrances, available balances
python -m budget_analyst analyze data/sample_prns_capital_funds.csv

# live dashboard at http://localhost:8765 - edits to the file appear live
python -m budget_analyst dashboard data/sample_prns_capital_funds.csv

# 4-slide PowerPoint briefing
python -m budget_analyst brief data/sample_prns_capital_funds.csv

# plain-English Q&A (best with an API key)
python -m budget_analyst ask data/sample_prns_operating_budget.csv \
    "Which division is furthest over budget and by how much?"
```

Outputs land in `output/`: `budget_analysis.xlsx`, `budget_memo.md`,
`budget_briefing.pptx`, `schema_mapping.json`. Excel files with several
sheets are handled automatically (densest sheet wins) or pick one with
`--sheet "Budget Detail"`.

## Architecture

```
 any CSV/XLSX ──▶ ingest.py ──▶ sheet pick + header sniff + currency
                                cleanup ──▶ profile (columns, dtypes)
                                    │
                                    ▼
                  schema_mapper.py  ── Claude maps columns to canonical
                                       roles (period, fund, entity,
                                       project, budget, actual,
                                       encumbrance, revenue...);
                                       keyword heuristics without a key
                                    │
                                    ▼
                  analysis.py       ── deterministic pandas/NumPy:
                                       variance, encumbrance balances,
                                       revenue attainment, fund summary,
                                       trends, forecast, anomaly flags
                                    │
                        ┌───────────┼───────────────┐
                        ▼           ▼               ▼
                  agent.py      report.py       deck.py / dashboard.py
                  memo + Q&A    styled .xlsx    .pptx briefing / live
                  (Claude or    with chart +    localhost monitor,
                  template)     highlighting    stdlib HTTP only
```

## Real-data case study: San José park maintenance priorities

`scripts/` contains a worked example on **real, weekly-refreshed City of
San José data** — the PRNS Park Condition Assessment (field-staff scores
for 274 parks, 2021–present, from data.sanjoseca.gov):

```bash
python scripts/fetch_sanjose.py        # pull the latest published data
python scripts/park_conditions.py      # -> priority workbook + memo
```

It answers a question the department actually faces: *with limited
maintenance and district-based C&C capital funds, which parks get the
next dollar?* Each park gets three transparent flags — condition below
70/100, decline of 5+ points, and bottom-quartile Healthy Places Index
(the ActivateSJ equity lens) — and the workbook ranks parks, rolls up by
council district (the C&C fund structure), and surfaces systemic asset
gaps. Findings from the July 2026 data: drinking fountains are the
weakest asset category citywide (64.5/100 average, down 12.3 points in a
year), Council District 8 has the lowest average condition and fastest
decline, and 2 parks carry all three flags. See
[examples/san_jose_parks/](examples/san_jose_parks/) for the outputs.

## Mock mode vs. live mode

Without `ANTHROPIC_API_KEY` set, the tool runs fully offline: heuristic
schema mapping plus a template memo — built from the same computed facts,
so the numbers are identical. With a key (and `pip install anthropic`),
Claude handles schema mapping, memo writing, and Q&A. Force offline mode
anytime with `--mock`.

## Using real City of San José data

- **Operating budget:** export CSV views from the City's OpenGov
  transparency platform: https://sanjoseca.opengov.com/transparency
- **Capital budget / C&C funds:** budget documents at
  https://www.sanjoseca.gov/your-government/departments-offices/office-of-the-city-manager/budget
- **311 service requests (updated daily):**
  https://data.sanjoseca.gov/dataset/311-service-request-data

The bundled samples are **illustrative**: they mirror the real PRNS
division structure and capital fund portfolio (Construction & Conveyance
tax funds by council district, a parks bond fund, the Park Trust Fund),
but the dollars are representative, not the City's actual figures. Swap
in a real export before citing any numbers.

## Project structure

```
budget_analyst/
    ingest.py         load any CSV/Excel: sheet pick, header sniff,
                      currency-text cleanup, profiling
    schema_mapper.py  Claude (or heuristic) column-role mapping
    analysis.py       deterministic variance/encumbrance/revenue/fund/
                      trend/forecast/anomaly math
    agent.py          Claude narration + Q&A, mock fallback
    report.py         styled Excel workbook (chart, conditional formats)
    deck.py           PowerPoint briefing generator
    dashboard.py      live file-watching localhost dashboard (stdlib)
    cli.py            analyze / ask / dashboard / brief commands
data/                 sample generators + demo datasets (operating + capital)
data/real/            real San Jose open data (refresh with fetch_sanjose.py)
scripts/              real-data case study: fetch + park-priority analysis
tests/                18 tests, all offline: math identities, messy-Excel
                      ingestion, fund reconciliation, deck/dashboard outputs
```

## Testing

```bash
python -m pytest tests -q
```

The suite verifies the math as identities (variance = budget − actual;
available = budget − actual − encumbered; fund totals reconcile to the
source rows), exercises the messy-Excel path end-to-end, and builds the
workbook and deck for real. No network or API key needed.
