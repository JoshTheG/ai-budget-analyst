"""Load any tabular budget file and profile it for schema mapping."""

from pathlib import Path

import pandas as pd


def load_table(path: str) -> pd.DataFrame:
    """Load a CSV or Excel file into a DataFrame."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"No such file: {path}")
    if p.suffix.lower() in {".xlsx", ".xls", ".xlsm"}:
        df = pd.read_excel(p)
    elif p.suffix.lower() in {".csv", ".txt"}:
        df = pd.read_csv(p)
    else:
        raise ValueError(f"Unsupported file type: {p.suffix}")
    df.columns = [str(c).strip() for c in df.columns]
    return df


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
# EOF-SENTINEL
