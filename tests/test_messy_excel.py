"""The 'any real data' claim: messy Excel workbooks still ingest cleanly."""

import sys
from pathlib import Path

import pytest
from openpyxl import Workbook

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from budget_analyst import analysis, ingest, schema_mapper  # noqa: E402


@pytest.fixture
def messy_workbook(tmp_path) -> Path:
    """A workbook the way finance systems actually export them:

    - a junk 'Notes' first sheet (so sheet selection matters)
    - report title + as-of date + blank row above the real header
    - dollars stored as text: "$1,234.56" and accounting "(500.00)"
    """
    wb = Workbook()
    notes = wb.active
    notes.title = "Notes"
    notes["A1"] = "Prepared by ASD"

    ws = wb.create_sheet("Budget Detail")
    ws.append(["PRNS Operating Budget Report"])
    ws.append(["As of: June 30, 2026"])
    ws.append([])
    ws.append(["Fiscal Year", "Division", "Adopted Budget", "Actual Expenditure"])
    rows = [
        ["FY 2025-26", "Parks Ops", "$1,000,000.00", "$950,000.00"],
        ["FY 2025-26", "Recreation", "$2,500,000.50", "$2,600,000.00"],
        ["FY 2025-26", "Zoo", "$800,000.00", "(50,000.00)"],
        ["FY 2025-26", "Admin", "$400,000.00", "$390,000.00"],
    ]
    for r in rows:
        ws.append(r)
    path = tmp_path / "messy_export.xlsx"
    wb.save(path)
    return path


def test_messy_excel_end_to_end(messy_workbook):
    df = ingest.load_table(str(messy_workbook))
    # picked the data sheet, skipped the title rows
    assert "Division" in df.columns
    assert len(df) == 4
    # currency text became numbers, accounting negative included
    assert df["Adopted Budget"].sum() == pytest.approx(4_700_000.50)
    assert df["Actual Expenditure"].min() == pytest.approx(-50_000.00)

    mapping = schema_mapper.map_schema(ingest.profile(df))
    result = analysis.run_all(df, mapping)
    assert result["facts"]["total_budget"] == pytest.approx(4_700_000.50)


def test_explicit_sheet_selection(messy_workbook):
    df = ingest.load_table(str(messy_workbook), sheet="Budget Detail")
    assert "Adopted Budget" in df.columns


def test_plain_text_columns_untouched(tmp_path):
    """Currency cleanup must not mangle genuine text columns."""
    import pandas as pd
    p = tmp_path / "t.csv"
    pd.DataFrame({
        "Division": ["A", "B"],
        "Notes": ["on track", "watch Q4"],
        "Budget": ["$100.00", "$200.00"],
    }).to_csv(p, index=False)
    df = ingest.load_table(str(p))
    assert df["Notes"].tolist() == ["on track", "watch Q4"]
    assert df["Budget"].sum() == 300.0
