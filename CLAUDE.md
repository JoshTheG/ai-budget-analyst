# CLAUDE.md

## What this project is

AI Budget Analyst: a CLI pipeline that analyzes any tabular budget dataset
(CSV/Excel) and produces an Excel variance workbook, trend + least-squares
forecast, z-score anomaly flags, and a written budget memo.

Built by Joshua Gonzalez as a portfolio project for the City of San Jose
PRNS Analyst I/II (Budget) application (job 202601655, closes July 15,
2026) and similar municipal analyst roles. The demo dataset mirrors the
real PRNS division structure; dollar figures are illustrative.

## Non-negotiable design rule

**The LLM never does arithmetic.** All figures are computed
deterministically in `analysis.py` (pandas/NumPy). Claude only maps
schemas (`schema_mapper.py`), narrates, and answers questions
(`agent.py`) from pre-computed facts. Never move calculation into a
prompt. The schema mapping is written to `schema_mapping.json` as an
audit trail — keep that behavior.

## Architecture

- `budget_analyst/ingest.py` — load CSV/xlsx, build a compact profile
  (only the profile is ever sent to the API, never the full dataset)
- `budget_analyst/schema_mapper.py` — Claude maps columns to canonical
  roles: period, entity, category, budget_amount, actual_amount,
  revenue_budget, revenue_actual. Keyword heuristics when no API key.
- `budget_analyst/analysis.py` — variance tables, trend, linear forecast,
  z-score anomalies; returns `{tables, facts}`; facts feed the narrator
- `budget_analyst/agent.py` — memo writer + Q&A; MockClient-free design:
  `get_client()` returns None without ANTHROPIC_API_KEY and every
  function has a template fallback using the same facts
- `budget_analyst/report.py` — openpyxl workbook + markdown memo
- `budget_analyst/cli.py` — `analyze` and `ask` subcommands

## Commands

```bash
python data/make_sample.py                                   # regen demo data
python -m budget_analyst analyze data/sample_prns_operating_budget.csv
python -m budget_analyst ask <file> "question"               # NL Q&A
python -m budget_analyst analyze <file> --mock               # force offline
pytest                                                       # 6 tests, all passing
```

## Current state (July 2026)

- Pipeline complete, 6/6 tests passing, mock mode fully offline
- Live Claude mode written but NOT yet run (owner has no API key yet)
- Not yet pushed to GitHub

## Next steps (in priority order)

1. Push to GitHub as public repo `ai-budget-analyst`
2. Get an Anthropic API key, `pip install anthropic`, verify live mode:
   schema mapping and memo on the sample data
3. Export a REAL dataset from https://sanjoseca.opengov.com/transparency
   and run against it — never cite the sample data's dollar figures;
   they are illustrative only
4. Optional generalization demo: the daily-updated 311 dataset at
   https://data.sanjoseca.gov/dataset/311-service-request-data
5. Update resume project bullet with real run numbers (rows, years,
   funds) once step 3 is done

## Conventions

- Python 3.10+, no dependencies beyond requirements.txt
  (anthropic optional, pytest for dev)
- Graceful degradation everywhere: any Claude failure falls back to
  heuristics/templates rather than crashing
- Keep the README's honesty guarantees true: every memo number traceable
  to `analysis.py`, sample data clearly labeled illustrative
