"""Deterministic analysis engine. Every number in the memo comes from here.

No LLM involvement: variance, trends, forecasts, and anomaly flags are
computed with pandas/NumPy so every figure is exact and reproducible.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def _num(df: pd.DataFrame, col: str) -> pd.Series:
    return pd.to_numeric(df[col], errors="coerce")


def variance_table(df: pd.DataFrame, m: dict, by: str) -> pd.DataFrame | None:
    """Budget vs. actual by entity or category for the latest period."""
    b, a = m.get("budget_amount"), m.get("actual_amount")
    if not (b and a and by in df.columns):
        return None
    work = df.copy()
    if m.get("period"):
        latest = work[m["period"]].dropna().max()
        work = work[work[m["period"]] == latest]
    g = work.groupby(by, dropna=False).agg(
        budget=(b, "sum"), actual=(a, "sum")).reset_index()
    g["variance"] = g["budget"] - g["actual"]
    g["variance_pct"] = np.where(g["budget"] != 0,
                                 (g["actual"] - g["budget"]) / g["budget"] * 100, np.nan)
    g["pct_spent"] = np.where(g["budget"] != 0, g["actual"] / g["budget"] * 100, np.nan)
    return g.sort_values("variance_pct", ascending=False).round(2)


def trend_table(df: pd.DataFrame, m: dict) -> pd.DataFrame | None:
    """Totals by period with period-over-period change."""
    p = m.get("period")
    val = m.get("actual_amount") or m.get("budget_amount")
    if not (p and val):
        return None
    g = df.groupby(p).agg(total=(val, "sum")).reset_index().sort_values(p)
    g["change"] = g["total"].diff()
    g["change_pct"] = (g["total"].pct_change() * 100).round(2)
    return g.round(2)


def forecast_next(trend: pd.DataFrame | None) -> dict | None:
    """Least-squares projection of the next period's total.

    Simple by design: with 3-10 annual observations a linear fit is more
    defensible than anything fancier, and the method is explainable to a
    non-technical reviewer in one sentence.
    """
    if trend is None or len(trend) < 3:
        return None
    y = trend["total"].to_numpy(dtype=float)
    x = np.arange(len(y), dtype=float)
    slope, intercept = np.polyfit(x, y, 1)
    pred = float(slope * len(y) + intercept)
    resid = y - (slope * x + intercept)
    ss_res, ss_tot = float((resid ** 2).sum()), float(((y - y.mean()) ** 2).sum())
    r2 = 1 - ss_res / ss_tot if ss_tot else float("nan")
    return {"projection": round(pred, 2), "slope_per_period": round(float(slope), 2),
            "r_squared": round(r2, 4), "n_periods": int(len(y))}


def anomalies(var: pd.DataFrame | None, by: str, z_thresh: float = 1.5) -> pd.DataFrame | None:
    """Flag entities whose variance % is a statistical outlier."""
    if var is None or len(var) < 4:
        return None
    v = var["variance_pct"].astype(float)
    if v.std(ddof=0) == 0 or np.isnan(v.std(ddof=0)):
        return None
    z = (v - v.mean()) / v.std(ddof=0)
    out = var.assign(z_score=z.round(2))
    out = out[abs(out["z_score"]) >= z_thresh]
    return out.sort_values("z_score", key=abs, ascending=False) if len(out) else None


def run_all(df: pd.DataFrame, mapping: dict) -> dict:
    """Run every applicable analysis; return tables plus a flat facts dict.

    The facts dict is the only thing the narration layer sees - plain
    computed numbers with unambiguous names.
    """
    m = mapping
    tables: dict[str, pd.DataFrame] = {}
    facts: dict = {"row_count": int(len(df))}

    for col in ("budget_amount", "actual_amount", "revenue_budget", "revenue_actual"):
        if m.get(col):
            df[m[col]] = _num(df, m[col])

    by_entity = variance_table(df, m, m.get("entity")) if m.get("entity") else None
    by_cat = variance_table(df, m, m.get("category")) if m.get("category") else None
    trend = trend_table(df, m)
    fc = forecast_next(trend)
    anom = anomalies(by_entity, m.get("entity"))

    if by_entity is not None:
        tables["variance_by_entity"] = by_entity
        facts["total_budget"] = round(float(by_entity["budget"].sum()), 2)
        facts["total_actual"] = round(float(by_entity["actual"].sum()), 2)
        facts["total_variance"] = round(float(by_entity["variance"].sum()), 2)
        facts["overall_pct_spent"] = round(
            facts["total_actual"] / facts["total_budget"] * 100, 2) if facts["total_budget"] else None
        top_over = by_entity.iloc[0]
        facts["largest_overrun_entity"] = str(top_over[m["entity"]])
        facts["largest_overrun_pct"] = float(top_over["variance_pct"])
        top_under = by_entity.iloc[-1]
        facts["largest_underspend_entity"] = str(top_under[m["entity"]])
        facts["largest_underspend_pct"] = float(top_under["variance_pct"])
    if m.get("period") and m.get("period") in df.columns:
        facts["latest_period"] = str(df[m["period"]].dropna().max())
        facts["n_periods"] = int(df[m["period"]].nunique())
    if by_cat is not None:
        tables["variance_by_category"] = by_cat
    if trend is not None:
        tables["trend_by_period"] = trend
        facts["latest_total"] = float(trend["total"].iloc[-1])
        if len(trend) >= 2 and not pd.isna(trend["change_pct"].iloc[-1]):
            facts["latest_change_pct"] = float(trend["change_pct"].iloc[-1])
    if fc:
        facts["forecast_next_period"] = fc["projection"]
        facts["forecast_r_squared"] = fc["r_squared"]
        facts["forecast_method"] = f"linear least-squares over {fc['n_periods']} periods"
    if anom is not None:
        tables["anomalies"] = anom
        facts["anomaly_count"] = int(len(anom))

    return {"tables": tables, "facts": facts}
# EOF-SENTINEL
