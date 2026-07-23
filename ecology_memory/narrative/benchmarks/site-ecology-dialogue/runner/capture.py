#!/usr/bin/env python3
"""Capture deterministic wide/narrow UI contracts and the latest ecology visual."""

from __future__ import annotations

import argparse
import pathlib
import sqlite3
from types import SimpleNamespace

from playwright.sync_api import sync_playwright


HERE = pathlib.Path(__file__).resolve().parent
BENCH = HERE.parent
IDLISSEUS = pathlib.Path("/home/beeps/src/github.com/bprashanth/idlisseus/chatbots/odysseus")


def latest_document(prefix: str):
    db_path = IDLISSEUS / "data/app.db"
    with sqlite3.connect(db_path) as db:
        row = db.execute(
            "SELECT id, title, current_content FROM documents "
            "WHERE id LIKE ? ORDER BY created_at DESC LIMIT 1",
            (prefix + "%",),
        ).fetchone()
    return SimpleNamespace(id=row[0], title=row[1], current_content=row[2]) if row else None


def fixture_html(style: str) -> str:
    return f"""<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><style>
:root{{--fg:#26332e;--bg:#f7f5ef;--border:#d9ddd8;--accent:#397b62;--red:#a23b36;
--color-error:#b8443f;--mono:ui-monospace,monospace}}body{{margin:0;padding:30px;
background:var(--bg);color:var(--fg);font:15px/1.5 system-ui,sans-serif}}
.msg-assistant{{max-width:760px;margin:auto}}.body{{padding-top:2px}}h1{{margin:0 0 12px}}
{style}</style></head><body><article class="msg-assistant">
<details class="insight-why"><summary><span class="insight-why-label">Why</span>
<span class="insight-why-count">3 skills</span></summary><ul class="insight-skill-list">
<li class="insight-skill" data-status="done"><span class="insight-skill-mark">✓</span>
<code>merged-taxon-occurrence-search</code><div class="insight-skill-result">
Finished · 43 source-linked occurrence rows · donor region retained in audit</div></li>
<li class="insight-skill" data-status="done"><span class="insight-skill-mark">✓</span>
<code>compile-scientific-algebra-9b</code><div class="insight-skill-result">
Validated ESTIMATE · environmental gate recorded</div></li>
<li class="insight-skill" data-status="done"><span class="insight-skill-mark">✓</span>
<code>build-ecology-field-map</code><div class="insight-skill-result">
Designed · 9 stable field points</div></li></ul>
<div class="insight-audit-id">Audit site-dialogue-example/3</div></details>
<div class="insight-evidence" aria-label="Evidence used in this answer">
<span class="insight-evidence-badge" data-kind="local_asset"><span>⌂</span>Local asset</span>
<span class="insight-evidence-badge" data-kind="public_connector"><span>↗</span>Public data</span>
<span class="insight-evidence-badge" data-kind="modelled"><span>≈</span>Modelled</span>
<span class="insight-evidence-badge" data-kind="designed"><span>✦</span>Designed</span>
<span class="insight-evidence-badge" data-kind="data_gap"><span>!</span>Data gap</span></div>
<section class="body"><h1>Where field checks add most information</h1>
<p>The environmental transfer did not return a fine-scale ranking surface. The map therefore
shows nine <strong>designed</strong> confirmation points, not predicted presence.</p>
<p><a href="#">Open field map</a></p></section></article></body></html>"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", required=True)
    parser.add_argument("--document-prefix", default="idli-dashboard-")
    args = parser.parse_args()
    output = BENCH / "runs" / args.run / "screenshots"
    output.mkdir(parents=True, exist_ok=True)
    style = (IDLISSEUS / "static/style.css").read_text(encoding="utf-8")
    document = latest_document(args.document_prefix)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        for name, viewport in (
            ("wide", {"width": 1440, "height": 1000}),
            ("narrow", {"width": 390, "height": 844}),
        ):
            page = browser.new_page(viewport=viewport)
            page.set_content(fixture_html(style), wait_until="load")
            page.screenshot(path=str(output / f"chat-evidence-{name}.png"), full_page=True)
            page.close()
        if document is not None:
            for name, viewport in (
                ("wide", {"width": 1440, "height": 1000}),
                ("narrow", {"width": 390, "height": 844}),
            ):
                page = browser.new_page(viewport=viewport)
                page.set_content(document.current_content, wait_until="load")
                page.screenshot(
                    path=str(output / f"{args.document_prefix.rstrip('-')}-{name}.png"),
                    full_page=True,
                )
                page.close()
        browser.close()
    print(output)


if __name__ == "__main__":
    main()
