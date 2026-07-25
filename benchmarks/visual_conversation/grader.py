#!/usr/bin/env python3
"""Deterministic grader for the visual conversation bench.

No model is used to judge a turn. Every check is a regex or a count over the answer text, so a
rerun after a skill-text change is directly comparable to the run before it. The grader reads a
transcript written by `bench.py` and emits both a JSON verdict and the RESULTS.md table.

What is graded, per turn:

* marker      -- the `<!-- idli-result:... -->` marker is present when the turn warrants a visual.
* jargon      -- build-side vocabulary ("pack", "capability", "envelope", "sqlite", ...) must not
                 appear in the prose the user reads. Marker comments are stripped before scanning,
                 because the browser consumes those and the user never sees them.
* refusal     -- keyword-shaped refusals ("no variable called ...", "unknown metric") are failures
                 regardless of how politely they are phrased.
* vocab       -- the user's own term, or one of its stated interpretations, comes back.
* leak        -- raw envelope material (JSON braces, result ids, cell ids) pasted into prose.
* questions   -- at most one clarifying question per turn.
* readability -- a model-free heuristic: sentence length, share of very long sentences, and whether
                 numbers carry a unit. Reported as a soft score, not a hard pass/fail.

Hard checks decide turn pass/fail. Readability is reported alongside.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import statistics
import sys

MARKER_RE = re.compile(r"<!--.*?-->", re.DOTALL)

# Build-side vocabulary. These are the words the serving stack uses about itself; a programme
# officer in Valparai has no reason to meet any of them.
JARGON = [
    r"site[- ]?pack", r"\bpacks?\b", r"\bgated?\b", r"\bgating\b", r"\bcapabilit(?:y|ies)\b",
    r"capability_id", r"\bskills?\b", r"\benvelopes?\b", r"evidence[- ]class(?:es)?",
    r"evidence_class", r"result service", r"site_index", r"\bsqlite\b", r"result_id",
    r"\bschema\b", r"\bjson\b", r"\bprovenance\b", r"\bconnectors?\b", r"data contract",
    r"\bview_id\b", r"\bcell_id\b", r"\bgeojson\b", r"\bendpoints?\b", r"\bpayloads?\b",
    r"\blineage\b", r"\bingest(?:ed|ion)?\b", r"\bAOI\b", r"\bmarker\b", r"\bidli-\w+",
    r"\bdenominator\b", r"\bnormalis(?:ed|ation)\b", r"\bnormaliz(?:ed|ation)\b",
    r"\bqueryable\b", r"\bindexed\b", r"\bmetadata\b", r"\bupstream\b", r"\bharness\b",
    r"\bonboard(?:ed|ing)\b", r"\b(?:this|that|the|a) visual\b", r"\bsite records\b",
]
JARGON_RE = re.compile("|".join(JARGON), re.IGNORECASE)

# Keyword-shaped refusals. The failure mode is telling a person their words do not exist.
REFUSAL = [
    r"no variable (?:called|named)", r"no such (?:variable|metric|column|field|dataset)",
    r"unknown (?:metric|variable|field|column)", r"unrecognis?zed (?:metric|variable|term)",
    r"not a (?:recognis|recogniz)ed (?:variable|metric|term)",
    r"no (?:matching|registered) (?:capability|skill|metric)",
    r"(?:i )?(?:can(?:no|')t|cannot|could not|couldn't) (?:find|identify) any (?:variable|metric|field)",
    r"unsupported (?:metric|query|variable)", r"invalid (?:metric|variable|argument)",
    r"i (?:do not|don't) understand (?:the|your) (?:term|word)",
    # The same failure wearing a politer coat: the user's own word is bounced back as not being
    # a name the system holds, with no plain-language menu of what it does hold.
    r"(?:does|did|do) not (?:recognis|recogniz)e", r"(?:doesn'?t|didn'?t) (?:recognis|recogniz)e",
    r"not (?:a )?(?:registered|valid|recognis|recogniz)\w* (?:metric|measure|variable|name)",
    r"registry (?:still )?(?:does not|doesn'?t)", r"(?:in|from) the (?:local|metric) registry",
    r"(?:did|does) not match (?:the|any|`)", r"no indexed metric matched",
    r"exact (?:registered measure|metric name)", r"is (?:still )?ambiguous in the",
]
REFUSAL_RE = re.compile("|".join(REFUSAL), re.IGNORECASE)

# Prose leakage of transport-level material.
LEAK_RE = re.compile(r"\{\s*\"|result-[0-9a-f]{8,}|g0\.\d{3}:|ent-[0-9a-f]{8,}|evt-[0-9a-f]{8,}")

# Machine syntax the user is expected to type or read: argument templates, identifiers with
# underscores or colons, and statistics notation. A programme officer cannot act on any of it.
MACHINE_RE = re.compile(
    r"`[^`]*[_:<>{}]+[^`]*`|at:<|R²|\bR2\b|\bp-value\b|\bCI\b|\bregex\b|--\w+"
)

GAP_RE = re.compile(
    r"(?:do(?:es)? not (?:yet )?have|don'?t (?:yet )?have|doesn'?t (?:yet )?have"
    r"|not (?:available|present|covered|included)"
    r"|no (?:data|records?|information|figures?)|nothing (?:on|about)|isn'?t (?:covered|there)"
    r"|not something (?:i|this data) (?:have|has|covers?)|outside what (?:i|this) hold"
    r"|not a direct (?:count|measure|figure)|cannot give you a (?:number|count)"
    r"|can'?t give you a (?:number|count)|there is nothing here (?:on|about))",
    re.IGNORECASE,
)

NON_ABSENCE_RE = re.compile(
    r"(?:does not mean|doesn'?t mean|not the same as|is not proof|no(?:t)? evidence of absence"
    r"|absence of (?:a )?(?:match|record)|not (?:recorded|collected) here does not"
    r"|only that (?:it|this) (?:was|is) not (?:recorded|collected)"
    r"|means (?:it )?(?:was )?not (?:recorded|collected|surveyed)"
    r"|cannot conclude|can'?t conclude|no one (?:has )?(?:looked|measured)"
    r"|(?:i am|i'?m) not saying[^.]{0,80}(?:absent|does not exist|doesn'?t exist|no \w+ data))",
    re.IGNORECASE,
)

ALTERNATIVES_RE = re.compile(
    r"(?:what (?:i|we) (?:do )?have|instead|closest|nearest thing|i do hold|available here"
    r"|does (?:exist|cover)|the data (?:i|we) have|these (?:sources|records)"
    r"|household survey|wage|estate labour|public works|migration)",
    re.IGNORECASE,
)

ESTIMATE_RE = re.compile(
    r"(?:estimate[ds]?|estimated|roughly|approximately|about \d|around \d|in the range|likely"
    r"|best guess|order of)",
    re.IGNORECASE,
)

# Confidence stated the way people speak, not as a coefficient.
CONFIDENCE_RE = re.compile(
    r"(?:confiden(?:ce|t)|not very sure|fairly sure|reasonably sure|rough|uncertain|uncertainty"
    r"|weak|strong|low|moderate|high|treat (?:it|this) as|would not bet|shaky|indicative"
    r"|take it as a (?:rough|broad))",
    re.IGNORECASE,
)

GK_LABEL_RE = re.compile(
    r"(?:in general|generally|broadly speaking|as (?:a )?general (?:context|point|guide)"
    r"|from general knowledge|outside (?:this|the) data|not from (?:this|the) data"
    r"|general context|common(?:ly)? (?:known|reported)|background knowledge"
    r"|this (?:is|comes from) general|typically, )",
    re.IGNORECASE,
)

DATA_ATTRIB_RE = re.compile(
    r"(?:in (?:this|the) (?:data|records|dataset)|from (?:this|the) (?:data|records|dataset)"
    r"|the (?:data|records) here|this site'?s? records|onboarded|recorded here|the survey"
    r"|the wage (?:data|records)|these records|according to (?:this|the) data"
    r"|the figures? (?:here|in this)|per the data)",
    re.IGNORECASE,
)

ROWS_RE = re.compile(
    r"(?:\|.*\|)|(?:^\s*\d+[\).]\s)|(?:\brows?\b)|(?:\btable\b)|(?:\btop \d)", re.MULTILINE
)

NUMBER_RE = re.compile(r"(?<![\w.])\d[\d,]*(?:\.\d+)?")
UNIT_RE = re.compile(
    r"\d[\d,.]*\s*(?:%|per cent|percent|rupees?|rs\.?|inr|days?|households?|workers?|visits?"
    r"|people|persons?|years?|records?|events?|villages?|estates?|jobs?|hours?|month|/)",
    re.IGNORECASE,
)

TRANSLATION_RE = re.compile(
    r"(?:means|meaning|in other words|that is|i\.e\.|simply|refers to|stands for|it is just"
    r"|it'?s just|think of it as|counts?|how (?:much|many))",
    re.IGNORECASE,
)


def strip_markers(text: str) -> str:
    """Return only what a reader sees: HTML comment markers are browser transport, not prose."""
    return MARKER_RE.sub(" ", text or "")


def sentences(prose: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+|\n+", prose)
    return [p.strip() for p in parts if p.strip()]


def readability(prose: str) -> dict:
    """A model-free proxy for 'can a programme officer read this out loud'.

    Three components: average sentence length, the share of very long sentences, and whether the
    numbers in the answer carry a unit a person can act on.
    """
    sents = sentences(prose)
    if not sents:
        return {"score": 0.0, "mean_words": 0, "long_share": 0.0, "numbers_with_units": True}
    lengths = [len(s.split()) for s in sents]
    mean_words = statistics.mean(lengths)
    long_share = sum(1 for n in lengths if n > 30) / len(lengths)
    numbers = NUMBER_RE.findall(prose)
    united = UNIT_RE.findall(prose)
    units_ok = (not numbers) or (len(united) >= max(1, len(numbers) // 3))
    length_score = max(0.0, min(1.0, 1.0 - max(0.0, mean_words - 20.0) / 20.0))
    score = 0.6 * length_score + 0.2 * (1.0 - long_share) + 0.2 * (1.0 if units_ok else 0.0)
    return {
        "score": round(score, 2),
        "mean_words": round(mean_words, 1),
        "long_share": round(long_share, 2),
        "numbers_with_units": units_ok,
    }


def _check(name: str, ok: bool, detail: str = "") -> dict:
    return {"name": name, "ok": bool(ok), "detail": detail}


def grade_turn(turn: dict, answer: str, latency_s: float | None = None) -> dict:
    """Apply every check declared on this turn plus the three that apply to every turn."""
    checks_spec = turn.get("checks") or {}
    prose = strip_markers(answer)
    lowered = prose.lower()
    results: list[dict] = []

    # --- checks that apply to every turn -------------------------------------------------
    jargon_hits = sorted({m.group(0).lower() for m in JARGON_RE.finditer(prose)})
    results.append(_check("jargon", not jargon_hits, ", ".join(jargon_hits[:8])))

    refusal_hits = sorted({m.group(0).lower() for m in REFUSAL_RE.finditer(prose)})
    results.append(_check("no_keyword_refusal", not refusal_hits, ", ".join(refusal_hits[:4])))

    leak_hits = sorted({m.group(0)[:24] for m in LEAK_RE.finditer(prose)})
    results.append(_check("no_transport_leak", not leak_hits, ", ".join(leak_hits[:4])))

    machine_hits = sorted({m.group(0)[:32] for m in MACHINE_RE.finditer(prose)})
    results.append(_check("no_machine_syntax", not machine_hits, ", ".join(machine_hits[:6])))

    results.append(_check("non_empty", len(prose.split()) >= 8, f"{len(prose.split())} words"))

    # --- declared checks ------------------------------------------------------------------
    if checks_spec.get("expect_visual"):
        has_marker = "<!-- idli-result:" in answer or "<!--idli-result:" in answer
        results.append(_check("visual_marker", has_marker,
                              "no idli-result marker on a turn that warrants a visual"))

    for group in checks_spec.get("vocab_any") or []:
        hit = next((term for term in group if term.lower() in lowered), None)
        results.append(_check(f"vocab[{group[0]}]", hit is not None,
                              f"none of {group} appear in the answer" if not hit else f"used '{hit}'"))

    if checks_spec.get("expect_rows"):
        results.append(_check("rows", bool(ROWS_RE.search(prose)),
                              "no table, numbered list or row language"))

    if checks_spec.get("expect_numbers"):
        results.append(_check("numbers", bool(NUMBER_RE.search(prose)), "no concrete figure"))

    if checks_spec.get("expect_gap"):
        results.append(_check("honest_gap", bool(GAP_RE.search(prose)),
                              "no plain statement that the data is missing"))

    if checks_spec.get("expect_gap_or_answer"):
        ok = bool(GAP_RE.search(prose)) or bool(NUMBER_RE.search(prose))
        results.append(_check("gap_or_answer", ok, "neither an answer nor an honest gap"))

    if checks_spec.get("expect_alternatives"):
        results.append(_check("offers_alternative", bool(ALTERNATIVES_RE.search(prose)),
                              "gap stated without saying what data does exist"))

    if checks_spec.get("expect_non_absence"):
        results.append(_check("non_match_is_not_absence", bool(NON_ABSENCE_RE.search(prose)),
                              "did not separate 'not recorded' from 'not happening'"))

    if checks_spec.get("expect_estimate"):
        results.append(_check("estimate_given", bool(ESTIMATE_RE.search(prose)),
                              "no estimate offered after the user supplied the location"))

    if checks_spec.get("expect_confidence"):
        results.append(_check("confidence_in_plain_words", bool(CONFIDENCE_RE.search(prose)),
                              "no everyday statement of how much to trust the number"))

    if checks_spec.get("expect_gk_label"):
        results.append(_check("general_knowledge_labelled", bool(GK_LABEL_RE.search(prose)),
                              "general context not marked as general"))

    if checks_spec.get("require_number_attribution"):
        user_numbers = {n.replace(",", "") for n in checks_spec.get("user_numbers") or []}
        found = {n.replace(",", "") for n in NUMBER_RE.findall(prose)}
        novel = {n for n in found if n not in user_numbers and len(n) >= 3}
        ok = (not novel) or bool(DATA_ATTRIB_RE.search(prose)) or bool(GK_LABEL_RE.search(prose))
        results.append(_check("numbers_attributed", ok,
                              f"unattributed figures: {sorted(novel)[:5]}"))

    for term in checks_spec.get("expect_translation_of") or []:
        ok = term.lower() in lowered and bool(TRANSLATION_RE.search(prose))
        results.append(_check(f"translates[{term}]", ok,
                              f"'{term}' not restated in everyday words"))

    if "max_questions" in checks_spec:
        limit = int(checks_spec["max_questions"])
        count = prose.count("?")
        results.append(_check("clarifying_questions", count <= limit,
                              f"{count} questions asked, limit {limit}"))

    if "max_sentences" in checks_spec:
        limit = int(checks_spec["max_sentences"])
        count = len(sentences(prose))
        results.append(_check("brevity", count <= limit,
                              f"{count} sentences, limit {limit}"))

    read = readability(prose)
    hard = [c for c in results]
    passed = all(c["ok"] for c in hard)
    return {
        "turn_id": turn.get("id"),
        "user": turn.get("user"),
        "answer": answer,
        "latency_s": latency_s,
        "checks": results,
        "failed": [c["name"] for c in results if not c["ok"]],
        "readability": read,
        "readable": read["score"] >= 0.6,
        "pass": passed,
    }


def grade_transcript(transcript: dict, spec: dict) -> dict:
    by_id = {c["id"]: c for c in spec["conversations"]}
    graded_convs = []
    for conv in transcript.get("conversations", []):
        source = by_id.get(conv["id"], {})
        spec_turns = {t["id"]: t for t in source.get("turns", [])}
        turns = []
        for turn in conv.get("turns", []):
            spec_turn = spec_turns.get(turn["id"], {"id": turn["id"], "user": turn.get("user")})
            turns.append(grade_turn(spec_turn, turn.get("answer") or "", turn.get("latency_s")))
        graded_convs.append({
            "id": conv["id"],
            "title": source.get("title", conv["id"]),
            "categories": source.get("categories", []),
            "session_id": conv.get("session_id"),
            "turns": turns,
            "pass": all(t["pass"] for t in turns),
        })

    # Category pass rates are computed per turn: a turn belongs to every category its conversation
    # declares, which is how the spec asked for the rollup.
    categories: dict[str, list[bool]] = {}
    check_totals: dict[str, list[bool]] = {}
    latencies: list[float] = []
    for conv in graded_convs:
        for turn in conv["turns"]:
            for cat in conv["categories"] or ["uncategorised"]:
                categories.setdefault(cat, []).append(turn["pass"])
            for check in turn["checks"]:
                check_totals.setdefault(check["name"].split("[")[0], []).append(check["ok"])
            if turn.get("latency_s"):
                latencies.append(turn["latency_s"])

    all_turns = [t for c in graded_convs for t in c["turns"]]
    return {
        "run": transcript.get("run", {}),
        "conversations": graded_convs,
        "summary": {
            "turns": len(all_turns),
            "turns_passed": sum(1 for t in all_turns if t["pass"]),
            "turn_pass_rate": round(
                sum(1 for t in all_turns if t["pass"]) / max(1, len(all_turns)), 3),
            "conversations_passed": sum(1 for c in graded_convs if c["pass"]),
            "readable_share": round(
                sum(1 for t in all_turns if t["readable"]) / max(1, len(all_turns)), 3),
            "median_latency_s": round(statistics.median(latencies), 1) if latencies else None,
            "max_latency_s": round(max(latencies), 1) if latencies else None,
            "category_pass_rate": {
                cat: round(sum(1 for ok in vals if ok) / len(vals), 3)
                for cat, vals in sorted(categories.items())
            },
            "check_pass_rate": {
                name: round(sum(1 for ok in vals if ok) / len(vals), 3)
                for name, vals in sorted(check_totals.items())
            },
        },
    }


def _excerpt(text: str, limit: int = 220) -> str:
    prose = " ".join(strip_markers(text).split())
    return (prose[:limit] + "...") if len(prose) > limit else prose


def render_results(graded: dict) -> str:
    run = graded.get("run", {})
    s = graded["summary"]
    out = ["# Visual conversation bench - results", ""]
    out.append(f"Run: `{run.get('run_id', 'unknown')}`  |  endpoint: `{run.get('base_url', '')}`  "
               f"|  started: {run.get('started', '')}")
    out.append("")
    out.append(f"**{s['turns_passed']}/{s['turns']} turns pass "
               f"({s['turn_pass_rate'] * 100:.0f}%)**, "
               f"{s['conversations_passed']}/{len(graded['conversations'])} conversations clean, "
               f"readable share {s['readable_share'] * 100:.0f}%, "
               f"median latency {s['median_latency_s']}s (max {s['max_latency_s']}s).")
    out.append("")
    out.append("## Pass rate by category")
    out.append("")
    out.append("| Category | Turn pass rate |")
    out.append("| --- | --- |")
    for cat, rate in s["category_pass_rate"].items():
        out.append(f"| {cat} | {rate * 100:.0f}% |")
    out.append("")
    out.append("## Pass rate by check")
    out.append("")
    out.append("| Check | Pass rate |")
    out.append("| --- | --- |")
    for name, rate in sorted(s["check_pass_rate"].items(), key=lambda kv: kv[1]):
        out.append(f"| `{name}` | {rate * 100:.0f}% |")
    out.append("")

    for conv in graded["conversations"]:
        out.append(f"## {conv['id']} - {conv['title']}")
        out.append("")
        out.append(f"Categories: {', '.join(conv['categories'])}  |  session: "
                   f"`{conv.get('session_id')}`")
        out.append("")
        out.append("| Turn | User (Indian English) | Result | Failed checks | Read | s | Excerpt |")
        out.append("| --- | --- | --- | --- | --- | --- | --- |")
        for turn in conv["turns"]:
            verdict = "PASS" if turn["pass"] else "**FAIL**"
            failed = ", ".join(f"`{n}`" for n in turn["failed"]) or "-"
            latency = f"{turn['latency_s']:.0f}" if turn.get("latency_s") else "-"
            user = turn["user"].replace("|", "/")
            excerpt = _excerpt(turn["answer"], 180).replace("|", "/")
            out.append(f"| {turn['turn_id']} | {user} | {verdict} | {failed} | "
                       f"{turn['readability']['score']} | {latency} | {excerpt} |")
        out.append("")
        for turn in conv["turns"]:
            if turn["pass"]:
                continue
            out.append(f"### {conv['id']} / {turn['turn_id']} - failure detail")
            out.append("")
            out.append(f"User: {turn['user']}")
            out.append("")
            for check in turn["checks"]:
                if not check["ok"]:
                    out.append(f"- `{check['name']}`: {check['detail']}")
            out.append("")
            out.append("```")
            out.append(" ".join(strip_markers(turn["answer"]).split())[:900])
            out.append("```")
            out.append("")
    return "\n".join(out) + "\n"


def main(argv: list[str] | None = None) -> int:
    here = pathlib.Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("transcript", type=pathlib.Path)
    parser.add_argument("--conversations", type=pathlib.Path,
                        default=here / "conversations.json")
    parser.add_argument("--results", type=pathlib.Path, default=None)
    parser.add_argument("--graded", type=pathlib.Path, default=None)
    args = parser.parse_args(argv)

    transcript = json.loads(args.transcript.read_text())
    spec = json.loads(args.conversations.read_text())
    graded = grade_transcript(transcript, spec)
    if args.graded:
        args.graded.write_text(json.dumps(graded, indent=2, ensure_ascii=False))
    text = render_results(graded)
    if args.results:
        args.results.write_text(text)
    else:
        sys.stdout.write(text)
    print(json.dumps(graded["summary"], indent=2), file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
