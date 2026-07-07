"""End-to-end pipeline tests. Run in mock mode - no API key required."""

import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "data" / "sample_prns_operating_budget.csv"

sys.path.insert(0, str(ROOT))

from budget_analyst import analysis, ingest, schema_mapper  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def sample_data():
    if not SAMPLE.exists():
        subprocess.run([sys.executable, str(ROOT / "data" / "make_sample.py")],
                       check=True)
    return SAMPLE


def _result():
    df = ingest.load_table(str(SAMPLE))
    mapping = schema_mapper.map_schema(ingest.profile(df))
    return df, mapping, analysis.run_all(df, mapping)


def test_heuristic_mapping_finds_all_roles():
    df = ingest.load_table(str(SAMPLE))
    mapping = schema_mapper.map_schema(ingest.profile(df))
    for role in ("period", "entity", "budget_amount", "actual_amount"):
        assert role in mapping, f"missing role: {role}"


def test_variance_math_is_exact():
    df, mapping, result = _result()
    var = result["tables"]["variance_by_entity"]
    latest = df["Fiscal Year"].max()
    expected_budget = df[df["Fiscal Year"] == latest]["Adopted Budget"].sum()
    assert abs(var["budget"].sum() - expected_budget) < 0.01
    # variance identity: budget - actual == variance, row by row
    assert ((var["budget"] - var["actual"]) - var["variance"]).abs().max() < 0.01


def test_facts_match_tables():
    _, _, result = _result()
    facts, var = result["facts"], result["tables"]["variance_by_entity"]
    assert facts["total_budget"] == round(float(var["budget"].sum()), 2)
    assert facts["total_actual"] == round(float(var["actual"].sum()), 2)


def test_mock_memo_uses_only_computed_facts():
    from budget_analyst.agent import mock_memo
    _, _, result = _result()
    memo = mock_memo(result["facts"])
    assert "Budget Analysis Memo" in memo
    # the headline totals in the memo must be the computed ones
    assert f"{result['facts']['total_budget']:,.0f}" in memo


def test_cli_end_to_end(tmp_path):
    proc = subprocess.run(
        [sys.executable, "-m", "budget_analyst", "analyze", str(SAMPLE),
         "--out", str(tmp_path), "--mock"],
        cwd=ROOT, capture_output=True, text=True, check=True)
    assert (tmp_path / "budget_analysis.xlsx").exists()
    assert (tmp_path / "budget_memo.md").exists()
    assert (tmp_path / "schema_mapping.json").exists()


def test_handles_unknown_schema():
    """The 'any data' claim: differently-named columns still map."""
    df = pd.DataFrame({
        "FY": ["2024", "2024", "2025", "2025"],
        "Program Unit": ["A", "B", "A", "B"],
        "Approved Budget Amt": [100.0, 200.0, 110.0, 210.0],
        "Expended Amt": [90.0, 205.0, 100.0, 220.0],
    })
    mapping = schema_mapper.map_schema(ingest.profile(df))
    result = analysis.run_all(df, mapping)
    assert "variance_by_entity" in result["tables"]
    assert result["facts"]["total_budget"] == 320.0
# EOF-SENTINEL
