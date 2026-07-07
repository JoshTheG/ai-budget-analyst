"""Capital-funds pipeline: encumbrances, fund reconciliation, revenue."""

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CAPITAL = ROOT / "data" / "sample_prns_capital_funds.csv"

sys.path.insert(0, str(ROOT))

from budget_analyst import analysis, ingest, schema_mapper  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def sample_data():
    if not CAPITAL.exists():
        subprocess.run([sys.executable, str(ROOT / "data" / "make_sample.py")],
                       check=True)
    return CAPITAL


@pytest.fixture(scope="module")
def capital_result():
    df = ingest.load_table(str(CAPITAL))
    mapping = schema_mapper.map_schema(ingest.profile(df))
    return df, mapping, analysis.run_all(df, mapping)


def test_capital_roles_map(capital_result):
    _, mapping, _ = capital_result
    assert mapping["fund"] == "Fund"
    assert mapping["project"] == "Project"
    assert mapping["encumbrance"] == "Encumbrance"
    assert mapping["budget_amount"] == "Appropriation"
    # "Fund" must not be stolen by the entity role
    assert mapping.get("entity") != "Fund"


def test_available_balance_identity(capital_result):
    """available = budget - actual - encumbrance, row by row."""
    _, _, result = capital_result
    var = result["tables"]["variance_by_entity"]
    calc = var["budget"] - var["actual"] - var["encumbrance"]
    assert (calc - var["available"]).abs().max() < 0.01


def test_fund_summary_reconciles(capital_result):
    df, mapping, result = capital_result
    funds = result["tables"]["fund_summary"]
    assert len(funds) == 12  # 10 C&C districts + bond + trust
    latest = df["Fiscal Year"].max()
    latest_df = df[df["Fiscal Year"] == latest]
    expected = latest_df["Appropriation"].sum()
    assert abs(funds["appropriation"].sum() - expected) < 0.01
    # net activity = revenues - expenditures
    calc = funds["revenue_actual"] - funds["expended"]
    assert (calc - funds["net_activity"]).abs().max() < 0.01


def test_revenue_attainment(capital_result):
    _, _, result = capital_result
    rev = result["tables"]["revenue_vs_target"]
    facts = result["facts"]
    assert facts["total_revenue_target"] == round(float(rev["revenue_target"].sum()), 2)
    # attainment table is sorted weakest-first and matches the facts
    assert facts["weakest_revenue_attainment_pct"] == float(rev["attainment_pct"].iloc[0])


def test_committed_pct_counts_encumbrance(capital_result):
    _, _, result = capital_result
    f = result["facts"]
    expected = (f["total_actual"] + f["total_encumbrance"]) / f["total_budget"] * 100
    assert abs(f["overall_pct_committed"] - expected) < 0.01
    assert f["overall_pct_committed"] > f["overall_pct_spent"]
