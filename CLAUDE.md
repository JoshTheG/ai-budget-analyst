# CLAUDE.md

## What this project is

AI Budget Analyst: a CLI toolkit that analyzes any tabular budget dataset
(CSV/Excel) — operating or capital — and produces an Excel variance
workbook, a written budget memo, a PowerPoint briefing deck, and a live
file-watching dashboard. Covers variance, encumbrance/available-balance
tracking, revenue-vs-target attainment, per-fund reconciliation, trend,
least-squares forecast, and z-score anomaly flags.

Built by Joshua Gonzalez as a portfolio project for the City of San Jose
PRNS Analyst I/II (Budget) application (job 202601655, closes July 15,
2026) and similar municipal analyst roles. The demo datasets mirror the
real PRNS division structure and capital fund portfolio (10 C&C tax
funds, bond fund, Park Trust Fund); dollar figures are illustrative.

## Non-negotiable design rule

**The LLM never does arithmetic.** All figures are computed
deterministically in `analysis.py` (pandas/NumPy). Claude only maps
schemas (`schema_mapper.py`), narrates, and answers questions
(`agent.py`) from pre-computed facts. Never move calculation into a
prompt. The schema mapping is written to `schema_mapping.json` as an
audit trail — keep that behavior. The deck and dashboard follow the same
rule: facts in, formatting out.

## Architecture

- `budget_analyst/ingest.py` — load CSV/xlsx: multi-sheet pick (densest
  wins, `--sheet` overrides), header-row sniffing past title rows,
  currency-text cleanup (`$1,234.56`, `(500.00)`); builds a compact
  profile (only the profile is ever sent to the API, never the dataset)
- `budget_analyst/schema_mapper.py` — Claude maps columns to canonical
  roles: period, fund, entity, project, category, budget_amount,
  actual_amount, encumbrance, revenue_budget, revenue_actual. Keyword
  heuristics when no API key. Role order matters: fund must claim the
  word "Fund" before entity scans.
- `budget_analyst/analysis.py` — variance (encumbrance-aware), revenue
  attainment, fund_summary reconciliation, trend, linear forecast,
  z-score anomalies; returns `{tables, facts}`; facts feed the narrator.
  Entity falls back to project, then fund, for capital extracts.
- `budget_analyst/agent.py` — memo writer + Q&A; `get_client()` returns
  None without ANTHROPIC_API_KEY and every function has a template
  fallback using the same facts
- `budget_analyst/report.py` — openpyxl workbook: styled headers,
  currency/percent formats, red/green conditional rules, embedded
  budget-vs-actual BarChart, summary sheet
- `budget_analyst/deck.py` — python-pptx 4-slide briefing (title,
  headline figures, native chart, findings/actions)
- `budget_analyst/dashboard.py` — stdlib ThreadingHTTPServer; page polls
  /data.json every 2s; server re-analyzes only on mtime change and keeps
  the last good snapshot if a mid-save read fails
- `budget_analyst/cli.py` — `analyze` / `ask` / `dashboard` / `brief`

## Commands

```bash
venv/Scripts/python.exe data/make_sample.py     # regen both demo datasets
venv/Scripts/python.exe -m budget_analyst analyze data/sample_prns_operating_budget.csv
venv/Scripts/python.exe -m budget_analyst analyze data/sample_prns_capital_funds.csv
venv/Scripts/python.exe -m budget_analyst dashboard <file>   # localhost:8765
venv/Scripts/python.exe -m budget_analyst brief <file>       # .pptx deck
venv/Scripts/python.exe -m budget_analyst ask <file> "question"
venv/Scripts/python.exe -m pytest tests -q     # 18 tests, all offline
```

Windows note: the venv lives at repo root (`venv/`), created from
python 3.14. pandas 3.x is installed — string columns are dtype `str`,
not `object` (ingest's currency cleaner handles both).

## Current state (July 2026)

- v0.2.0: capital-funds module, encumbrances, revenue attainment, live
  dashboard, PowerPoint deck, messy-Excel ingestion; 18/18 tests passing
- **Real-data case study shipped**: `scripts/fetch_sanjose.py` pulls the
  City's weekly Park Condition Assessment (1,616 assessments, 274 parks,
  2021-2025); `scripts/park_conditions.py` produces the equity-weighted
  park maintenance priority workbook + memo (outputs in
  examples/san_jose_parks/). Real findings as of 2026-07-08: drinking
  fountains weakest asset citywide (64.5/100, -12.3 YoY), District 8
  lowest avg condition, tier-3 parks = McLaughlin + Meadowfair.
- Live Claude mode written but NOT yet run (owner has no API key yet)
- Dashboard verified end-to-end: save the watched file and totals update
- The city open-data portal (data.sanjoseca.gov, CKAN API) has NO
  budget-dollar datasets; financials live on OpenGov (gated JS app).
  Real budget-vs-actual dollars would need manual export from
  sanjoseca.opengov.com/transparency or transcription from adopted
  budget PDFs.

## Next steps (in priority order)

1. Add dashboard + workbook screenshots to the README
2. Get an Anthropic API key, `pip install anthropic`, verify live mode:
   schema mapping and memo on the sample data
3. Manually export a real dollars dataset from
   https://sanjoseca.opengov.com/transparency and run the core budget
   pipeline on it — never cite the sample data's dollar figures; they
   are illustrative only
4. Optional generalization demo: the daily-updated 311 dataset at
   https://data.sanjoseca.gov/dataset/311-service-request-data

## Conventions

- Python 3.10+, no dependencies beyond requirements.txt
  (anthropic optional, pytest for dev)
- Graceful degradation everywhere: any Claude failure falls back to
  heuristics/templates rather than crashing; dashboard serves the last
  good snapshot on read errors
- Keep the README's honesty guarantees true: every memo/deck/dashboard
  number traceable to `analysis.py`, sample data clearly labeled
  illustrative
- Tests assert math as identities (variance = budget − actual;
  available = budget − actual − encumbered; fund totals reconcile)
