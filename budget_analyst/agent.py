"""Claude narration layer plus mock fallback.

Claude receives ONLY pre-computed facts and table summaries - it writes
prose and prioritizes findings, it never calculates. Mock mode produces
the same memo structure from the same facts using templates, so the tool
runs end-to-end (and correctly) without an API key.
"""

from __future__ import annotations

import json
import os

DEFAULT_MODEL = "claude-sonnet-5"

MEMO_SYSTEM = (
    "You are a municipal budget analyst writing for a department director. "
    "You will receive verified, pre-computed figures as JSON facts and "
    "markdown tables. Write a concise budget memo with sections: Summary, "
    "Key Findings, Risks & Anomalies, Outlook, Recommended Actions. "
    "STRICT RULE: use only numbers present in the input - never compute, "
    "extrapolate, or invent figures. Cite figures exactly as given. "
    "Plain professional prose, no hype."
)

QA_SYSTEM = (
    "You are a municipal budget analyst answering a question using ONLY "
    "the verified facts and tables provided as JSON. If the answer is not "
    "derivable from the provided figures, say so and name what additional "
    "data would be needed. Never invent or compute new numbers."
)


def get_client():
    """Return an Anthropic client if a key is configured, else None (mock)."""
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return None
    try:
        import anthropic
        return anthropic.Anthropic()
    except ImportError:
        return None


def _fmt_money(v) -> str:
    try:
        return f"${v:,.0f}"
    except (TypeError, ValueError):
        return str(v)


def mock_memo(facts: dict) -> str:
    """Template memo built from the same computed facts Claude would get."""
    f = facts
    lines = ["# Budget Analysis Memo", "", "## Summary", ""]
    if "total_budget" in f:
        lines.append(
            f"For {f.get('latest_period', 'the latest period')}, total budgeted "
            f"expenditures were {_fmt_money(f['total_budget'])} against actuals of "
            f"{_fmt_money(f['total_actual'])} — {f.get('overall_pct_spent', 'n/a')}% "
            f"of budget spent, a net variance of {_fmt_money(f['total_variance'])}.")
    lines += ["", "## Key Findings", ""]
    if "largest_overrun_entity" in f:
        lines.append(
            f"- Highest spending vs. budget: {f['largest_overrun_entity']} "
            f"({f['largest_overrun_pct']:+.1f}% relative to budget).")
        lines.append(
            f"- Largest underspend: {f['largest_underspend_entity']} "
            f"({f['largest_underspend_pct']:+.1f}% relative to budget).")
    if "latest_change_pct" in f:
        lines.append(
            f"- Latest period total of {_fmt_money(f['latest_total'])} changed "
            f"{f['latest_change_pct']:+.1f}% versus the prior period.")
    lines += ["", "## Risks & Anomalies", ""]
    lines.append(
        f"- {f['anomaly_count']} unit(s) flagged as statistical variance outliers "
        f"(|z| >= 1.5); see Anomalies sheet." if f.get("anomaly_count")
        else "- No statistical variance outliers flagged at |z| >= 1.5.")
    lines += ["", "## Outlook", ""]
    if "forecast_next_period" in f:
        lines.append(
            f"- Next-period projection: {_fmt_money(f['forecast_next_period'])} "
            f"({f['forecast_method']}, R² = {f['forecast_r_squared']}).")
    else:
        lines.append("- Insufficient period history for a defensible projection.")
    lines += ["", "## Recommended Actions", "",
              "- Review flagged outlier units with program managers before quarter close.",
              "- Reconcile top variance line items against encumbrances and timing effects.",
              "- Re-run this analysis when the next monthly actuals post.",
              "", "---",
              "*Generated in mock mode (no API key): template narrative over "
              "deterministically computed figures. Set ANTHROPIC_API_KEY for "
              "Claude-written narrative.*"]
    return "\n".join(lines)


def _tables_md(tables: dict, max_rows: int = 12) -> str:
    parts = []
    for name, t in tables.items():
        parts.append(f"### {name}\n\n{t.head(max_rows).to_markdown(index=False)}")
    return "\n\n".join(parts)


def write_memo(result: dict, client=None, model: str = DEFAULT_MODEL) -> str:
    """Produce the memo via Claude, or the template when no client."""
    if client is None:
        return mock_memo(result["facts"])
    payload = (
        "FACTS (verified, pre-computed):\n" + json.dumps(result["facts"], indent=2)
        + "\n\nTABLES:\n" + _tables_md(result["tables"])
    )
    msg = client.messages.create(
        model=model, max_tokens=2000, system=MEMO_SYSTEM,
        messages=[{"role": "user", "content": payload}],
    )
    return msg.content[0].text


def answer_question(result: dict, question: str, client=None,
                    model: str = DEFAULT_MODEL) -> str:
    """Natural-language Q&A over the computed facts."""
    if client is None:
        return ("Mock mode (no API key). Verified facts available to answer "
                "questions:\n" + json.dumps(result["facts"], indent=2))
    payload = (
        "FACTS:\n" + json.dumps(result["facts"], indent=2)
        + "\n\nTABLES:\n" + _tables_md(result["tables"])
        + f"\n\nQUESTION: {question}"
    )
    msg = client.messages.create(
        model=model, max_tokens=1000, system=QA_SYSTEM,
        messages=[{"role": "user", "content": payload}],
    )
    return msg.content[0].text
# EOF-SENTINEL
