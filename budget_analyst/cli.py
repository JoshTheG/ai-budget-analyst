"""Command-line interface.

    python -m budget_analyst analyze data/sample_prns_operating_budget.csv
    python -m budget_analyst ask data.csv "Which division is most over budget?"
"""

from __future__ import annotations

import argparse
import sys

from . import agent, analysis, ingest, report, schema_mapper


def _prepare(path: str, use_mock: bool, model: str):
    df = ingest.load_table(path)
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

    args = ap.parse_args(argv)
    result, mapping, client = _prepare(args.file, args.mock, args.model)

    if args.cmd == "analyze":
        memo = agent.write_memo(result, client, args.model)
        paths = report.write_outputs(result, memo, mapping, args.out)
        for label, p in paths.items():
            print(f"wrote {label}: {p}")
    else:
        print(agent.answer_question(result, args.question, client, args.model))
    return 0


if __name__ == "__main__":
    sys.exit(main())
# EOF-SENTINEL
