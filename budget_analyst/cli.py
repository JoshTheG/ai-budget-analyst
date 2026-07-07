"""Command-line interface.

    python -m budget_analyst analyze data/sample_prns_operating_budget.csv
    python -m budget_analyst ask data.csv "Which division is most over budget?"
    python -m budget_analyst dashboard data.xlsx            # live monitor
    python -m budget_analyst brief data.csv                 # PowerPoint deck
"""

from __future__ import annotations

import argparse
import sys

from . import agent, analysis, ingest, report, schema_mapper


def _prepare(path: str, use_mock: bool, model: str, sheet: str | None = None):
    df = ingest.load_table(path, sheet=sheet)
    prof = ingest.profile(df)
    client = None if use_mock else agent.get_client()
    mapping = schema_mapper.map_schema(prof, client, model)
    mode = "mock" if client is None else "live"
    print(f"[{mode}] loaded {prof['n_rows']} rows x {prof['n_cols']} cols from {path}")
    mapped = {k: v for k, v in mapping.items() if k != "rationale"}
    print(f"[{mode}] schema mapping: {mapped}")
    result = analysis.run_all(df, mapping)
    return result, mapping, client


def main(argv=None) -> int:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--model", default=agent.DEFAULT_MODEL)
    common.add_argument("--mock", action="store_true",
                        help="force mock mode even if ANTHROPIC_API_KEY is set")
    common.add_argument("--sheet", default=None,
                        help="Excel sheet name (default: densest sheet)")

    ap = argparse.ArgumentParser(
        prog="budget_analyst",
        description="Automated budget analysis: deterministic math, Claude narration.")
    sub = ap.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("analyze", parents=[common],
                       help="full analysis -> Excel workbook + memo")
    a.add_argument("file")
    a.add_argument("--out", default="output")

    q = sub.add_parser("ask", parents=[common],
                       help="natural-language question over the data")
    q.add_argument("file")
    q.add_argument("question")

    d = sub.add_parser("dashboard", parents=[common],
                       help="live local dashboard that watches the file")
    d.add_argument("file")
    d.add_argument("--port", type=int, default=8765)

    b = sub.add_parser("brief", parents=[common],
                       help="4-slide PowerPoint briefing deck")
    b.add_argument("file")
    b.add_argument("--out", default="output")

    args = ap.parse_args(argv)

    if args.cmd == "dashboard":
        from . import dashboard
        client = None if args.mock else agent.get_client()
        dashboard.serve(args.file, port=args.port, sheet=args.sheet,
                        client=client, model=args.model)
        return 0

    result, mapping, client = _prepare(args.file, args.mock, args.model, args.sheet)

    if args.cmd == "analyze":
        memo = agent.write_memo(result, client, args.model)
        paths = report.write_outputs(result, memo, mapping, args.out)
        for label, p in paths.items():
            print(f"wrote {label}: {p}")
    elif args.cmd == "brief":
        from pathlib import Path

        from . import deck
        path = deck.write_deck(result, Path(args.file).name, args.out)
        print(f"wrote briefing deck: {path}")
    else:
        print(agent.answer_question(result, args.question, client, args.model))
    return 0


if __name__ == "__main__":
    sys.exit(main())
