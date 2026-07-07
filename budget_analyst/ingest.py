"""Load any tabular budget file and profile it for schema mapping.

Real municipal exports are messy: workbooks with several sheets, title
and logo rows above the real header, and dollars stored as text like
"$1,234.56" or "(500.00)". This module absorbs all of that so the rest
of the pipeline always sees a clean, typed DataFrame.
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

_EXCEL_SUFFIXES = {".xlsx", ".xls", ".xlsm"}
_CURRENCY_RE = re.compile(r"^\s*\(?\s*[$€£]?\s*-?[\d,]+(\.\d+)?\s*\)?\s*$")


def _pick_sheet(xl: pd.ExcelFile) -> str:
    """Choose the sheet that looks most like a data table (most cells)."""
    best, best_cells = xl.sheet_names[0], -1
    for name in xl.sheet_names:
        df = xl.parse(name, header=None, nrows=50)
        cells = int(df.notna().sum().sum())
        if cells > best_cells:
            best, best_cells = name, cells
    return best


def _sniff_header(raw: pd.DataFrame, scan_rows: int = 10) -> int:
    """Find the real header row in a sheet that may start with title rows.

    The header is the first row where most cells are non-null strings and
    the row below it exists - typical of exports with a report title,
    'As of <date>' line, or blank rows above the table.
    """
    best_row, best_score = 0, -1.0
    for i in range(min(scan_rows, len(raw))):
        row = raw.iloc[i]
        filled = row.notna()
        if filled.sum() < 2:
            continue
        texty = sum(isinstance(v, str) and v.strip() != "" for v in row)
        score = filled.mean() + texty / max(len(row), 1)
        if score > best_score:
            best_row, best_score = i, score
    return best_row


def _clean_currency(df: pd.DataFrame) -> pd.DataFrame:
    """Convert text columns that are really dollars into numbers.

    Handles "$1,234.56", "1,234", and accounting negatives "(500.00)".
    A column converts only if >=80% of its non-null values look like
    currency, so genuine text columns are never touched.
    """
    for col in df.columns:
        s = df[col]
        # object in pandas<3, "str" dtype in pandas>=3
        if not (pd.api.types.is_object_dtype(s) or pd.api.types.is_string_dtype(s)):
            continue
        vals = s.dropna().astype(str)
        if len(vals) == 0:
            continue
        looks = vals.str.match(_CURRENCY_RE)
        if looks.mean() < 0.8:
            continue
        cleaned = (s.astype(str)
                    .str.replace(r"[$€£,\s]", "", regex=True)
                    .str.replace(r"^\((.*)\)$", r"-\1", regex=True))
        df[col] = pd.to_numeric(cleaned, errors="coerce")
    return df


def load_table(path: str, sheet: str | None = None) -> pd.DataFrame:
    """Load a CSV or Excel file into a clean DataFrame.

    Excel: picks the densest sheet unless ``sheet`` names one, then
    sniffs past any title rows to the real header. All files get
    currency-string cleanup and stripped column names.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"No such file: {path}")
    if p.suffix.lower() in _EXCEL_SUFFIXES:
        xl = pd.ExcelFile(p)
        name = sheet if sheet is not None else _pick_sheet(xl)
        raw = xl.parse(name, header=None)
        header_row = _sniff_header(raw)
        df = xl.parse(name, header=header_row)
    elif p.suffix.lower() in {".csv", ".txt"}:
        df = pd.read_csv(p)
    else:
        raise ValueError(f"Unsupported file type: {p.suffix}")
    df.columns = [str(c).strip() for c in df.columns]
    df = df.dropna(axis=1, how="all").dropna(axis=0, how="all")
    return _clean_currency(df)


def profile(df: pd.DataFrame, sample_rows: int = 5) -> dict:
    """Summarize a DataFrame so the schema mapper can reason about it.

    Returns column names, inferred dtypes, null counts, distinct counts,
    numeric ranges, and a small sample of rows. This profile - not the
    full dataset - is what gets sent to the LLM, which keeps token use
    small and avoids shipping entire datasets to an API.
    """
    cols = []
    for c in df.columns:
        s = df[c]
        info = {
            "name": c,
            "dtype": str(s.dtype),
            "nulls": int(s.isna().sum()),
            "distinct": int(s.nunique(dropna=True)),
        }
        if pd.api.types.is_numeric_dtype(s):
            info["min"] = None if s.dropna().empty else float(s.min())
            info["max"] = None if s.dropna().empty else float(s.max())
        else:
            vals = s.dropna().astype(str).unique()[:8]
            info["examples"] = list(vals)
        cols.append(info)
    return {
        "n_rows": int(len(df)),
        "n_cols": int(df.shape[1]),
        "columns": cols,
        "sample": df.head(sample_rows).to_dict(orient="records"),
    }
