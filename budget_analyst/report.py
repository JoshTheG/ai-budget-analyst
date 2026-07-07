"""Excel workbook + markdown memo output."""

from __future__ import annotations

import json
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

HEADER_FILL = PatternFill("solid", fgColor="1F4E79")
HEADER_FONT = Font(bold=True, color="FFFFFF")
MONEY_COLS = {"budget", "actual", "variance", "total", "change"}


def _write_sheet(wb, name: str, df) -> None:
    ws = wb.create_sheet(name[:31])
    ws.append(list(df.columns))
    for cell in ws[1]:
        cell.fill, cell.font = HEADER_FILL, HEADER_FONT
        cell.alignment = Alignment(horizontal="center")
    for row in df.itertuples(index=False):
        ws.append(list(row))
    for i, col in enumerate(df.columns, start=1):
        letter = get_column_letter(i)
        width = max(len(str(col)) + 2, 14)
        ws.column_dimensions[letter].width = width
        if str(col).lower() in MONEY_COLS:
            for cell in ws[letter][1:]:
                cell.number_format = "#,##0.00"
    ws.freeze_panes = "A2"


def write_outputs(result: dict, memo: str, mapping: dict, out_dir: str) -> dict:
    """Write workbook, memo, and an audit trail of the schema mapping."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    wb = Workbook()
    ws = wb.active
    ws.title = "Summary"
    ws.append(["Metric", "Value"])
    for cell in ws[1]:
        cell.fill, cell.font = HEADER_FILL, HEADER_FONT
    for k, v in result["facts"].items():
        ws.append([k, v])
    ws.column_dimensions["A"].width = 30
    ws.column_dimensions["B"].width = 40
    for name, df in result["tables"].items():
        _write_sheet(wb, name, df)

    xlsx = out / "budget_analysis.xlsx"
    wb.save(xlsx)

    memo_path = out / "budget_memo.md"
    memo_path.write_text(memo, encoding="utf-8")

    audit = out / "schema_mapping.json"
    audit.write_text(json.dumps(mapping, indent=2), encoding="utf-8")

    return {"workbook": str(xlsx), "memo": str(memo_path), "mapping": str(audit)}
# EOF-SENTINEL
