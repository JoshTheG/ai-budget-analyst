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

    The header is the earliest dense row of non-numeric labels - typical
    of exports with a report title, 'As of <date>' line, filter rows, or
    blanks above the table. Currency-looking strings and numbers count
    against a row so data rows never outscore the header.
    """
    def counts(row):
        texty = numbery = 0
        for v in row:
            if isinstance(v, str) and v.strip():
                if _CURRENCY_RE.match(v):
                    numbery += 1
                else:
                    texty += 1
            elif isinstance(v, (int, float)) and not pd.isna(v):
                numbery += 1
        return texty, numbery

    best_row, best_score = 0, -1.0
    for i in range(min(scan_rows, len(raw))):
        row = raw.iloc[i]
        filled = row.notna()
        if filled.sum() < 2:
            continue
        texty, numbery = counts(row)
        score = filled.mean() + (texty - numbery) / max(len(row), 1)
        # a real header is followed by data: bonus if the next non-blank
        # row carries numbers (distinguishes it from filter/title rows)
        for j in range(i + 1, len(raw)):
            if raw.iloc[j].notna().sum() == 0:
                continue
            if counts(raw.iloc[j])[1] >= 2:
                score += 0.5
            break
        if score > best_score:
            best_row, best_score = i, score
    return best_row


def _read_csv_smart(p: Path) -> pd.DataFrame:
    """Read a CSV that may have ragged title/filter rows above the header."""
    import csv

    try:
        text_rows = list(csv.reader(p.open(newline="", encoding="utf-8-sig")))
    except UnicodeDecodeError:
        text_rows = list(csv.reader(p.open(newline="", encoding="latin-1")))
    width = max((len(r) for r in text_rows), default=0)
    raw = pd.DataFrame([r + [None] * (width - len(r)) for r in text_rows])
    raw = raw.replace("", None)
    hdr = _sniff_header(raw)
    df = raw.iloc[hdr + 1:].reset_index(drop=True)
    names, seen = [], {}
    for j, v in enumerate(raw.iloc[hdr]):
        name = (str(v).strip() if pd.notna(v) and str(v).strip()
                else f"Unnamed: {j}")
        seen[name] = seen.get(name, 0) + 1
        names.append(name if seen[name] == 1 else f"{name}.{seen[name]}")
    df.columns = names
    return df


# columns like "September 2012-13 Actual", "FY2024 Adopted", "2023-24"
_PERIOD_COL_RE = re.compile(r"(20\d{2}\s*[-/]\s*\d{2,4}|FY\s?'?\d{2,4}|20\d{2})", re.I)
_TOTAL_LABELS = {"total", "grand total", "totals"}


def _maybe_melt(df: pd.DataFrame) -> pd.DataFrame:
    """Reshape crosstab exports (years across columns) into long form.

    OpenGov-style downloads pivot periods into columns. When 3+ numeric
    columns carry period-like names and dominate the table, melt them
    into a single Period column; the value column is named for the
    measure the columns share (Actual/Budget), and Total rows are
    dropped so they can't double-count.
    """
    period_cols = [c for c in df.columns
                   if _PERIOD_COL_RE.search(str(c))
                   and pd.api.types.is_numeric_dtype(df[c])]
    if len(period_cols) < 3 or len(period_cols) < 0.5 * len(df.columns):
        return df
    id_cols = [c for c in df.columns if c not in period_cols]
    for measure in ("Actual", "Budget", "Adopted", "Estimate"):
        if all(measure.lower() in str(c).lower() for c in period_cols):
            value_name = measure
            break
    else:
        value_name = "Amount"
    if id_cols:
        mask = pd.Series(False, index=df.index)
        for c in id_cols:
            mask |= df[c].astype(str).str.strip().str.lower().isin(_TOTAL_LABELS)
        df = df[~mask]
    long = df.melt(id_vars=id_cols, value_vars=period_cols,
                   var_name="Period", value_name=value_name)
    return long.dropna(subset=[value_name]).reset_index(drop=True)


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
        df = _read_csv_smart(p)
    else:
        raise ValueError(f"Unsupported file type: {p.suffix}")
    df.columns = [str(c).strip() for c in df.columns]
    df = df.dropna(axis=1, how="all").dropna(axis=0, how="all")
    # crosstab row labels often have a blank header cell
    renames = {c: "Row Label" for c in df.columns if str(c).startswith("Unnamed:")}
    if len(renames) == 1:
        df = df.rename(columns=renames)
    return _maybe_melt(_clean_currency(df))


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
