"""Live local dashboard: point it at a CSV/Excel file and watch it.

    python -m budget_analyst dashboard data/sample_prns_operating_budget.csv

Serves http://localhost:8765 with KPI tiles, a budget-vs-actual chart,
and every analysis table. The page polls /data.json every 2 seconds;
the server re-ingests and re-analyzes ONLY when the file's mtime
changes, so you can keep the workbook open in Excel, save, and see the
numbers move. Standard library HTTP server - no extra dependencies,
nothing leaves the machine.
"""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pandas as pd

from . import analysis, ingest, schema_mapper


def compute_snapshot(path: str, sheet: str | None = None,
                     client=None, model: str = "claude-sonnet-5") -> dict:
    """Ingest, map, analyze; return a JSON-safe snapshot dict."""
    df = ingest.load_table(path, sheet=sheet)
    mapping = schema_mapper.map_schema(ingest.profile(df), client, model)
    result = analysis.run_all(df, mapping)
    tables = {}
    for name, t in result["tables"].items():
        clean = t.astype(object).where(pd.notna(t), None)
        tables[name] = {"columns": list(t.columns),
                        "rows": clean.to_dict(orient="records")}
    facts = {k: (None if isinstance(v, float) and pd.isna(v) else v)
             for k, v in result["facts"].items()}
    return {"facts": facts, "tables": tables,
            "mapping": {k: v for k, v in mapping.items() if k != "rationale"},
            "source": Path(path).name}


class _State:
    """Cached snapshot, refreshed only when the source file changes."""

    def __init__(self, path: str, sheet: str | None, client, model: str):
        self.path, self.sheet = path, sheet
        self.client, self.model = client, model
        self._lock = threading.Lock()
        self._mtime: float | None = None
        self._snapshot: dict | None = None

    def get(self) -> dict:
        mtime = Path(self.path).stat().st_mtime
        with self._lock:
            if self._snapshot is None or mtime != self._mtime:
                try:
                    self._snapshot = compute_snapshot(
                        self.path, self.sheet, self.client, self.model)
                    self._snapshot["error"] = None
                except Exception as exc:  # noqa: BLE001 - mid-save reads fail
                    if self._snapshot is None:
                        raise
                    self._snapshot["error"] = f"refresh failed, showing last good data: {exc}"
                self._mtime = mtime
            return self._snapshot


PAGE = """<!doctype html>
<html><head><meta charset="utf-8"><title>Budget Monitor</title>
<style>
:root { --navy:#1F4E79; --bg:#f4f6f9; --card:#ffffff; --red:#c0392b; --green:#1e8449; --ink:#1c2833; }
* { box-sizing:border-box; margin:0; }
body { font:14px/1.45 "Segoe UI",system-ui,sans-serif; background:var(--bg); color:var(--ink); padding:20px; }
header { display:flex; align-items:baseline; gap:14px; flex-wrap:wrap; margin-bottom:16px; }
h1 { font-size:20px; color:var(--navy); }
#meta { color:#5d6d7e; font-size:12px; }
#live { display:inline-block; width:9px; height:9px; border-radius:50%; background:var(--green); margin-right:5px; animation:pulse 2s infinite; }
@keyframes pulse { 50% { opacity:.35; } }
#error { color:var(--red); font-size:12px; }
.kpis { display:grid; grid-template-columns:repeat(auto-fit,minmax(180px,1fr)); gap:12px; margin-bottom:18px; }
.kpi { background:var(--card); border-radius:8px; padding:12px 16px; box-shadow:0 1px 3px rgba(0,0,0,.08); border-top:3px solid var(--navy); }
.kpi .label { font-size:11px; text-transform:uppercase; letter-spacing:.06em; color:#5d6d7e; }
.kpi .value { font-size:22px; font-weight:600; margin-top:2px; }
.kpi .value.bad { color:var(--red); } .kpi .value.good { color:var(--green); }
section { background:var(--card); border-radius:8px; padding:16px; margin-bottom:18px; box-shadow:0 1px 3px rgba(0,0,0,.08); overflow-x:auto; }
section h2 { font-size:14px; color:var(--navy); margin-bottom:10px; text-transform:capitalize; }
table { border-collapse:collapse; width:100%; font-size:12.5px; }
th { background:var(--navy); color:#fff; padding:6px 10px; text-align:left; white-space:nowrap; }
td { padding:5px 10px; border-bottom:1px solid #e5e8ec; white-space:nowrap; }
td.num { text-align:right; font-variant-numeric:tabular-nums; }
td.neg { color:var(--red); font-weight:600; }
svg text { font:11px "Segoe UI",sans-serif; fill:#5d6d7e; }
.legend { font-size:11px; color:#5d6d7e; margin-top:4px; }
.sw { display:inline-block; width:10px; height:10px; border-radius:2px; margin:0 4px 0 10px; vertical-align:-1px; }
</style></head><body>
<header><h1>Budget Monitor</h1><div id="meta"></div><div id="error"></div></header>
<div class="kpis" id="kpis"></div>
<section id="chartbox" style="display:none"><h2 id="charttitle"></h2><svg id="chart" width="100%" height="300"></svg>
<div class="legend"><span class="sw" style="background:#1F4E79"></span>Budget<span class="sw" style="background:#7FB3D5"></span>Actual</div></section>
<div id="tables"></div>
<script>
const $ = id => document.getElementById(id);
const money = v => v==null ? "" : "$" + Number(v).toLocaleString(undefined,{maximumFractionDigits:0});
const pct = v => v==null ? "" : Number(v).toFixed(1) + "%";
const KPIS = [
  ["total_budget","Total Budget",money],
  ["total_actual","Actual Spent",money],
  ["overall_pct_spent","% Spent",pct],
  ["total_available","Available Balance",money],
  ["overall_pct_committed","% Committed",pct],
  ["revenue_attainment_pct","Revenue Attainment",pct],
  ["forecast_next_period","Next-Period Projection",money],
  ["anomaly_count","Outliers Flagged",v=>v==null?"0":v],
];
function drawKpis(f){
  $("kpis").innerHTML = KPIS.filter(([k])=>f[k]!==undefined).map(([k,label,fmt])=>{
    let cls = "";
    if (k==="overall_pct_spent"||k==="overall_pct_committed") cls = f[k]>100?"bad":"good";
    if (k==="revenue_attainment_pct") cls = f[k]<100?"bad":"good";
    if (k==="anomaly_count") cls = f[k]>0?"bad":"good";
    if (k==="total_available") cls = f[k]<0?"bad":"good";
    return `<div class="kpi"><div class="label">${label}</div><div class="value ${cls}">${fmt(f[k])}</div></div>`;
  }).join("");
}
function drawChart(data){
  const t = data.tables.variance_by_entity;
  if (!t){ $("chartbox").style.display="none"; return; }
  $("chartbox").style.display="";
  const ent = data.facts.entity_column;
  $("charttitle").textContent = `Budget vs. Actual by ${ent} — ${data.facts.latest_period||"all periods"}`;
  const rows = t.rows.slice(0,12);
  const svg = $("chart"), W = svg.clientWidth||900, H = 300, padL=70, padB=90, padT=10;
  const max = Math.max(...rows.flatMap(r=>[r.budget||0,r.actual||0]))*1.08 || 1;
  const bw = (W-padL-10)/rows.length;
  let out = "";
  for (let g=0; g<=4; g++){
    const y = padT+(H-padB-padT)*g/4, val = max*(1-g/4);
    out += `<line x1="${padL}" y1="${y}" x2="${W-5}" y2="${y}" stroke="#e5e8ec"/>`+
           `<text x="${padL-6}" y="${y+4}" text-anchor="end">${(val/1e6).toFixed(1)}M</text>`;
  }
  rows.forEach((r,i)=>{
    const x = padL + i*bw, h1 = (r.budget||0)/max*(H-padB-padT), h2 = (r.actual||0)/max*(H-padB-padT);
    out += `<rect x="${x+bw*0.12}" y="${H-padB-h1}" width="${bw*0.32}" height="${h1}" fill="#1F4E79"/>`+
           `<rect x="${x+bw*0.48}" y="${H-padB-h2}" width="${bw*0.32}" height="${h2}" fill="#7FB3D5"/>`;
    const label = String(r[ent]??"").slice(0,24);
    out += `<text x="${x+bw/2}" y="${H-padB+12}" transform="rotate(28 ${x+bw/2} ${H-padB+12})">${label}</text>`;
  });
  svg.setAttribute("viewBox",`0 0 ${W} ${H}`);
  svg.innerHTML = out;
}
function drawTables(data){
  $("tables").innerHTML = Object.entries(data.tables).map(([name,t])=>{
    const head = t.columns.map(c=>`<th>${c}</th>`).join("");
    const body = t.rows.map(r=>"<tr>"+t.columns.map(c=>{
      const v = r[c];
      if (typeof v === "number"){
        const isPct = /pct|attainment/.test(c);
        const neg = (v<0 && /variance|available|net/.test(c)) || (isPct && /spent|committed/.test(c) && v>100);
        return `<td class="num${neg?" neg":""}">${isPct?pct(v):money(v)}</td>`;
      }
      return `<td>${v??""}</td>`;
    }).join("")+"</tr>").join("");
    return `<section><h2>${name.replaceAll("_"," ")}</h2><table><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table></section>`;
  }).join("");
}
async function tick(){
  try {
    const data = await (await fetch("data.json")).json();
    $("meta").innerHTML = `<span id="live"></span>${data.source} &middot; ${data.facts.latest_period||""} &middot; updated ${new Date().toLocaleTimeString()}`;
    $("error").textContent = data.error || "";
    drawKpis(data.facts); drawChart(data); drawTables(data);
  } catch (e) { $("error").textContent = "connection lost - is the server still running?"; }
}
tick(); setInterval(tick, 2000);
</script></body></html>
"""


def _make_handler(state: _State):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802 - http.server API
            if self.path.split("?")[0] in ("/", "/index.html"):
                body, ctype = PAGE.encode(), "text/html; charset=utf-8"
            elif self.path.split("?")[0] == "/data.json":
                body, ctype = json.dumps(
                    state.get(), default=str).encode(), "application/json"
            else:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):  # silence per-request noise
            pass

    return Handler


def serve(path: str, port: int = 8765, sheet: str | None = None,
          client=None, model: str = "claude-sonnet-5") -> None:
    """Run the dashboard server until Ctrl+C."""
    state = _State(path, sheet, client, model)
    state.get()  # fail fast on unreadable files before binding the port
    httpd = ThreadingHTTPServer(("127.0.0.1", port), _make_handler(state))
    print(f"Budget Monitor: http://localhost:{port}  (watching {path})")
    print("Save the file in Excel and the page updates itself. Ctrl+C to stop.")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")
    finally:
        httpd.server_close()
