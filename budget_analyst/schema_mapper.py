"""Map arbitrary column names onto canonical budget-analysis roles.

Roles:
    period          fiscal year / month / quarter column
    fund            capital or special fund name (C&C funds, bond, trust)
    entity          department, division, program, or agency name
    project         capital project / site / facility name
    category        expenditure category (personal services, supplies, ...)
    budget_amount   adopted/modified budget or appropriation dollars
    actual_amount   actual expenditure dollars
    encumbrance     encumbered/committed-but-unspent dollars
    revenue_budget  budgeted/target revenue dollars
    revenue_actual  actual revenue dollars

With an API key set, Claude reads the dataset profile and returns the
mapping as JSON - this is what lets the tool accept *any* data. Without
a key, a keyword heuristic covers common government export formats.
"""

from __future__ import annotations

import json
import re

ROLES = [
    "period", "fund", "entity", "project", "category",
    "budget_amount", "actual_amount", "encumbrance",
    "revenue_budget", "revenue_actual",
]

# Order matters: roles are matched top to bottom and a column can only be
# claimed once, so "fund" must win the word Fund before "entity" scans.
_HEURISTICS = {
    "period": r"(fiscal.?year|^fy|year|period|month|quarter|date)",
    "fund": r"\bfund",
    "entity": r"(department|division|program|agency|unit|cost.?center)",
    "project": r"(project|site|facility|location)",
    "category": r"(category|object|account|type|class)",
    "budget_amount": r"(adopted|approved|modified|revised)?.*budget(?!.*rev)|appropriat",
    "actual_amount": r"(actual|expend|spent|expense)(?!.*rev)",
    "encumbrance": r"(encumbr|committed|obligat)",
    "revenue_budget": r"(revenue|receipt).*(budget|target|estimate)|(budget|target|estimate).*(revenue|receipt)",
    "revenue_actual": r"(revenue|receipt).*(actual)|(actual).*(revenue|receipt)",
}

SYSTEM_PROMPT = (
    "You are a municipal budget data specialist. You will receive a JSON "
    "profile of a tabular dataset (column names, dtypes, examples, sample "
    "rows). Map columns onto these roles: " + ", ".join(ROLES) + ". "
    "Reply with ONLY a JSON object of role -> column name (omit roles that "
    "have no matching column), plus a key 'rationale' with one short "
    "sentence per mapped role."
)


def heuristic_map(profile: dict) -> dict:
    """Keyword-based fallback mapping. Deterministic, no API required."""
    mapping, rationale = {}, {}
    names = [c["name"] for c in profile["columns"]]
    numeric = {c["name"] for c in profile["columns"]
               if c["dtype"].startswith(("int", "float"))}
    dollar_roles = {"budget_amount", "actual_amount", "encumbrance",
                    "revenue_budget", "revenue_actual"}
    for role in ROLES:
        pat = re.compile(_HEURISTICS[role], re.I)
        for name in names:
            if name in mapping.values():
                continue
            if pat.search(name):
                if role in dollar_roles and name not in numeric:
                    continue
                mapping[role] = name
                rationale[role] = f"column name '{name}' matched keyword pattern"
                break
    mapping["rationale"] = rationale
    return mapping


def claude_map(profile: dict, client, model: str) -> dict:
    """Ask Claude to map the schema. Falls back to heuristics on failure."""
    try:
        msg = client.messages.create(
            model=model,
            max_tokens=1000,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": json.dumps(profile, default=str)}],
        )
        text = msg.content[0].text
        start, end = text.find("{"), text.rfind("}") + 1
        mapping = json.loads(text[start:end])
        # validate: mapped columns must exist
        cols = {c["name"] for c in profile["columns"]}
        for role in list(mapping):
            if role != "rationale" and mapping[role] not in cols:
                del mapping[role]
        return mapping
    except Exception as exc:  # noqa: BLE001 - degrade gracefully
        fallback = heuristic_map(profile)
        fallback["rationale"]["_warning"] = f"Claude mapping failed ({exc}); used heuristics"
        return fallback


def map_schema(profile: dict, client=None, model: str = "claude-sonnet-5") -> dict:
    """Return role -> column mapping using Claude when available."""
    if client is None:
        return heuristic_map(profile)
    return claude_map(profile, client, model)
