# Putting this project on your resume

Target: **Analyst I/II (Budget) — Parks, Recreation & Neighborhood
Services, City of San José** (job 202601655). This file maps the project
to that posting. Present it honestly as a personal/portfolio project —
the samples are illustrative, not City data.

## Resume entry (pick 3-4 bullets)

**AI Budget Analyst — personal project** (Python, pandas, Excel/openpyxl,
PowerPoint, local LLM integration) · github.com/&lt;you&gt;/ai-budget-analyst

- Built an end-to-end budget monitoring toolkit that ingests any
  operating or capital budget export (CSV/Excel) and produces a
  formatted variance workbook, budget memo, and PowerPoint briefing in
  one command.
- Implemented the core municipal monitoring math: budget-vs-actual
  variance, encumbrance-aware available balances and % committed,
  revenue-vs-target attainment, per-fund reconciliation across a
  12-fund capital portfolio modeled on C&C tax, bond, and park trust
  funds, plus trend and least-squares projection.
- Developed a live budget dashboard (zero-dependency local web server)
  that watches the source workbook and refreshes KPIs, charts, and
  tables the moment the file is saved in Excel.
- Engineered robust data ingestion for real-world finance exports:
  multi-sheet workbooks, report-title rows above headers, and
  currency-as-text (`$1,234.56`, accounting negatives) — validated by an
  18-test suite that checks the math as identities (e.g., available =
  budget − actual − encumbered).
- Designed an auditable AI layer: an LLM maps unfamiliar column schemas
  and writes the memo narrative, but every figure is computed
  deterministically in pandas — the model never does arithmetic, and
  the schema mapping is saved as a JSON audit trail.

## How it maps to the posting

| Posting language | Where the project shows it |
|---|---|
| "monitoring and managing operating budgets... budget balances, revenue targets, and expenditure levels" | variance, % spent/committed, available balance, revenue attainment KPIs |
| "developing tools to improve budget tracking and reporting" | the whole toolkit; especially `dashboard` and the styled workbook |
| "tracking expenditures for capital improvement projects, reconciling revenues across capital and special funds" | `fund_summary`: per-fund appropriation/expended/encumbered/available/net activity over a C&C + bond + Park Trust portfolio |
| "assemble, array, process, and analyze data" | messy-Excel ingestion + schema mapping + deterministic analysis engine |
| "preparation and delivery of verbal and written reports and presentations" | budget memo, Excel workbook, PowerPoint briefing — all generated |
| "Microsoft Excel, Word, and PowerPoint" | reads and writes Excel (openpyxl), writes PowerPoint (python-pptx), memo is Word-ready markdown |

## Interview talking points

- **Why encumbrances matter:** % spent understates commitment; a fund can
  look healthy at 60% spent but be 95% committed. The tool reports both.
- **Why the forecast is deliberately simple:** with 3-10 annual points, a
  linear fit you can explain in one sentence beats a black box — same
  judgment call a budget office makes.
- **AI with controls:** the memo can quote only pre-computed figures; the
  design assumes the narrative layer is untrusted. Good answer to "how
  would you use AI responsibly in a government setting."
- **What you'd do at PRNS:** the same loop — load adopted budget into FMS,
  monitor actuals/encumbrances monthly, flag variances, brief management —
  which is exactly the pipeline this automates on public exports.

## Before you publish

1. Push to GitHub and put the link on the resume.
2. Run the demo once and screenshot the dashboard + workbook for the repo.
3. Replace `<you>` above; keep the "illustrative data" disclaimer visible.
