"""inspect — human-browsable HTML reports over run traces.

  python3 inspect.py                    -> report.html in EVERY run dir + runs/index.html
  python3 inspect.py tick-023-gen-006   -> report.html for one run

Per question: score badge, the IR tree rendered node-by-node (op-colored, holes highlighted),
gold tree, per-node execution provenance (which connector each SELECT routed to, row counts),
repair events (brace-completion, peephole unmerge, provenance demotion, lints, mech synthesis),
execution outcome/detail, synthesis prose if present. Self-contained files, no JS dependencies.
"""
import glob
import html
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
RUNS = os.path.abspath(os.path.join(HERE, "..", "runs"))

CSS = """
body{font-family:system-ui,sans-serif;margin:20px auto;max-width:1100px;color:#1a1a1a}
.q{border:1px solid #ddd;border-radius:8px;margin:14px 0;padding:12px 16px}
.q h3{margin:2px 0 8px}
.badge{display:inline-block;border-radius:10px;padding:1px 10px;color:#fff;font-size:13px}
.g{background:#2e7d32}.y{background:#f9a825}.r{background:#c62828}
.tree{font-family:ui-monospace,monospace;font-size:13px;background:#fafafa;border-radius:6px;padding:8px 12px;overflow-x:auto}
.tree ul{list-style:none;margin:0;padding-left:18px;border-left:1px dotted #bbb}
.op{font-weight:700}.op-SELECT{color:#1565c0}.op-RELATE{color:#6a1b9a}.op-AGGREGATE{color:#00695c}
.op-COMPARE{color:#e65100}.op-RANK{color:#ad1457}.op-ESTIMATE{color:#b71c1c}.op-REGION{color:#555}
.hole{background:#fff3cd;border:1px solid #f0c36d;border-radius:4px;padding:0 4px;font-weight:700}
.kv{color:#444}.lbl{font-size:12px;color:#777;text-transform:uppercase;letter-spacing:.05em;margin-top:10px}
table{border-collapse:collapse;font-size:13px}td,th{border:1px solid #ddd;padding:3px 8px;text-align:left}
.ev{font-family:ui-monospace,monospace;font-size:12px;background:#eef;border-radius:4px;padding:1px 6px;margin:2px;display:inline-block}
.syn{background:#f0f7f0;border-radius:6px;padding:8px 12px;font-style:italic}
details summary{cursor:pointer;color:#1565c0;font-size:13px}
"""


def render_tree(node):
    if node is None:
        return "<i>null (no tree)</i>"
    if isinstance(node, str):
        v = html.escape(node)
        return f'<span class="hole">{v}</span>' if node.startswith("?") else v
    if isinstance(node, list):
        return "<ul>" + "".join(f"<li>{render_tree(x)}</li>" for x in node) + "</ul>"
    if not isinstance(node, dict):
        return html.escape(json.dumps(node))
    op = node.get("op", "")
    parts = []
    for k, v in node.items():
        if k == "op":
            continue
        if isinstance(v, (dict, list)) and (isinstance(v, list) or "op" in v or k in ("time",)):
            parts.append(f"<li><span class='kv'>{k}:</span> {render_tree(v)}</li>")
        else:
            vs = html.escape(json.dumps(v))
            if isinstance(v, str) and v.startswith("?"):
                vs = f'<span class="hole">{html.escape(v)}</span>'
            parts.append(f"<li><span class='kv'>{k}</span> = {vs}</li>")
    return (f"<span class='op op-{op}'>{op}</span><ul>" + "".join(parts) + "</ul>")


def render_record(r):
    sc = r.get("scores", {})
    ov = sc.get("overall", 0)
    cls = "g" if ov >= 0.85 else ("y" if ov >= 0.6 else "r")
    ex = r.get("execution", {})
    out = [f"<div class='q'><h3>{html.escape(r.get('id',''))} "
           f"<span class='badge {cls}'>{ov}</span> "
           f"<small>{html.escape(r.get('sector',''))}/{html.escape(r.get('type',''))}</small></h3>",
           f"<p><b>Q:</b> {html.escape(r.get('question',''))}</p>",
           "<div class='lbl'>parsed IR tree</div>",
           f"<div class='tree'>{render_tree(r.get('ir'))}</div>"]
    if r.get("repair_events"):
        out.append("<div class='lbl'>repair / lint events</div><div>" +
                   "".join(f"<span class='ev'>{html.escape(e)}</span>"
                           for e in r["repair_events"]) + "</div>")
    prov = ex.get("provenance") or []
    if prov:
        out.append("<div class='lbl'>execution provenance (per node)</div><table>"
                   "<tr><th>op</th><th>route</th><th>note</th></tr>")
        for p in prov:
            out.append(f"<tr><td>{html.escape(str(p.get('op','')))}</td>"
                       f"<td>{html.escape(str(p.get('route','') or p.get('relation','') or p.get('how','') or p.get('gate','') or ''))}</td>"
                       f"<td>{html.escape(str(p.get('note','') or json.dumps(p.get('gate')) if p.get('gate') else p.get('note','') or ''))}</td></tr>")
        out.append("</table>")
    status = ex.get("status", "?")
    detail = ex.get("detail")
    out.append(f"<div class='lbl'>outcome</div><p><b>{html.escape(str(status))}</b>"
               f"{(' — ' + html.escape(json.dumps(detail)[:220])) if detail else ''}"
               f" &nbsp; evidence: <b>{html.escape(str(ex.get('label') or r.get('execution',{}).get('label') or 'n/a'))}</b></p>")
    if r.get("synthesis"):
        ss = r.get("synthesis_scores") or {}
        out.append(f"<div class='lbl'>synthesized answer (score {ss.get('overall','-')})</div>"
                   f"<div class='syn'>{html.escape(r['synthesis'])}</div>")
    if r.get("gold_ir"):
        out.append("<details><summary>gold tree</summary>"
                   f"<div class='tree'>{render_tree(r['gold_ir'])}</div></details>")
    dims = {k: v for k, v in sc.items() if k != "overall"}
    out.append("<details><summary>score dims</summary><p>" +
               " · ".join(f"{k}={'1' if v else '0'}" for k, v in dims.items()) + "</p></details>")
    out.append("</div>")
    return "".join(out)


def report(run_dir):
    path = os.path.join(run_dir, "traces.jsonl")
    if not os.path.exists(path):
        return None
    rows = [json.loads(l) for l in open(path)]
    name = os.path.basename(run_dir)
    n = len(rows)
    ov = sum(r.get("scores", {}).get("overall", 0) for r in rows) / max(n, 1)
    body = "".join(render_record(r) for r in rows)
    html_doc = (f"<!doctype html><meta charset='utf-8'><title>{name}</title><style>{CSS}</style>"
                f"<h1>{name}</h1><p>{n} questions · mean overall {ov:.3f} · "
                f"model {html.escape(str(rows[0].get('model','?')) if rows else '?')}</p>{body}")
    out = os.path.join(run_dir, "report.html")
    with open(out, "w") as f:
        f.write(html_doc)
    return {"name": name, "n": n, "overall": round(ov, 3),
            "model": rows[0].get("model", "?") if rows else "?"}


def index():
    entries = []
    for d in sorted(glob.glob(os.path.join(RUNS, "*"))):
        if os.path.isdir(d):
            meta = report(d)
            if meta:
                entries.append(meta)
    rows = "".join(
        f"<tr><td><a href='{e['name']}/report.html'>{e['name']}</a></td>"
        f"<td>{e['model']}</td><td>{e['n']}</td><td>{e['overall']}</td></tr>"
        for e in reversed(entries))
    doc = (f"<!doctype html><meta charset='utf-8'><title>runs index</title><style>{CSS}</style>"
           f"<h1>Benchmark runs ({len(entries)})</h1>"
           f"<table><tr><th>run</th><th>model</th><th>n</th><th>overall</th></tr>{rows}</table>")
    out = os.path.join(RUNS, "index.html")
    with open(out, "w") as f:
        f.write(doc)
    print(f"index: {out}  ({len(entries)} runs)")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        d = sys.argv[1]
        if not os.path.isdir(d):
            d = os.path.join(RUNS, d)
        meta = report(d)
        print(f"report: {os.path.join(d, 'report.html')}  {meta}")
    else:
        index()
