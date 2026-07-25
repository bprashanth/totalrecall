#!/usr/bin/env python3
"""Deterministic grader for the ecology ANR bench.

The bar is not "did it answer". The bar is: would a field ecologist keep talking to it. So the
checks are written against the way a good field-ecology book reads -- concrete nouns, a figure when
a figure was asked for, an honest "we never measured that" instead of a fabrication, and always a
next move.

Nine graded dimensions, all decided by regex or by the recorded tool trail, so two runs either side
of a skill-text change are directly comparable:

* visual_present  -- an `<!-- idli-result:... -->` marker on a turn that warrants a picture.
* right_tool      -- which capability the bridge actually ran, read from the session audit trail.
                     Falling back to the orientation map on a question that names a comparison, a
                     place or a species is a failure even when the prose sounds fine.
* has_evidence    -- a real figure when the user asked how much / which / where.
* honest_gap      -- absence is stated as absence, and something that does exist is named instead.
* traceable       -- the answer names the survey it came from, or offers the rows.
* jargon          -- build-side vocabulary in prose the user reads.
* language        -- 0-2 register score: sentence length, passive voice, database nouns, concrete
                     detail. Reported, not a hard gate.
* multi_turn      -- turn N carries the thing turn N-1 established, and does not re-ask for it.
* dead_end        -- an answer that leaves the user with nowhere to go is a failure however true.

Hard checks decide the turn. `language` and latency ride alongside.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import statistics
import sys

MARKER_RE = re.compile(r"<!--.*?-->", re.DOTALL)

# ---------------------------------------------------------------------------------------------
# jargon: exactly the build-side vocabulary an ecologist should never meet
# ---------------------------------------------------------------------------------------------
JARGON = [
    r"\bsite[- ]?packs?\b", r"\bpacks?\b", r"\bgated?\b", r"\bgating\b",
    r"\bcapabilit(?:y|ies)\b", r"capability_id", r"\bskills?\b", r"\benvelopes?\b",
    r"evidence[- ]class(?:es)?", r"evidence_class", r"\bresult service\b", r"\bsite_index\b",
    r"\badapters?\b", r"\bdata plane\b", r"\bcontrol plane\b", r"\bthe plane\b",
    r"\btarget cells?\b", r"\btarget map squares?\b", r"\bcell[_ ]ids?\b", r"g0\.\d{3}:",
    r"\bonboard(?:ed|ing)\b", r"\bindexed (?:data|records?|sources?|layers?|surfaces?)\b",
    r"\b(?:this|that|the) visual\b", r"\bresult_id\b", r"result-[0-9a-f]{8,}",
    r"\bcapability\b", r"\bevidence class\b",
]
JARGON_RE = re.compile("|".join(JARGON), re.IGNORECASE)

# Transport material pasted into prose.
LEAK_RE = re.compile(r"\{\s*\"|result-[0-9a-f]{8,}|g0\.\d{3}:|ent-[0-9a-f]{8,}|src-[0-9a-f]{8,}")

# A dead end: the user is told the machinery failed and given nothing to do next.
DEAD_END_RE = re.compile(
    r"(?:the route (?:failed|did not|didn'?t)|could not (?:be )?(?:produced|generated|completed)"
    r"|request failed|something went wrong|try again later|no result was returned"
    r"|i was unable to (?:produce|run|complete)|nothing (?:more )?i can do"
    r"|that is outside what i can do(?!\s*,)|i cannot help with)",
    re.IGNORECASE,
)

# A next move on offer: an explicit thing the person could do or ask for next.
NEXT_STEP_RE = re.compile(
    r"(?:if you want|if you'?d like|i can (?:show|pull|break|check|map|list|compare|run|go)"
    r"|shall i|would you like|next (?:step|i)|you could|worth (?:doing|checking|walking|starting)"
    r"|start (?:with|by)|i'?d (?:suggest|recommend)|recommend(?:ation)?"
    r"|the quickest way|say the word|tell me which|point me at)",
    re.IGNORECASE,
)

# Naming a source or offering rows. Written against the surveys this landscape actually holds.
TRACEABLE_RE = re.compile(
    r"(?:point counts?|belt transects?|time[- ]constrained|road[- ]event|weather station"
    r"|acoustic|camera|trail inventory|plant community|tree and habitat|seed[- ](?:fate|predation)"
    r"|frugivor\w+|butterfly|herpetofauna|mammal (?:occurrence|record)"
    r"|the (?:bird|mammal|butterfly|frog|tree|plant|seed|weather|acoustic)[- ]?\w* (?:survey|records?|counts?|data|study|work)"
    r"|survey|study|records? (?:from|behind|collected)|i can show you the (?:rows|records|underlying)"
    r"|the rows behind|underlying records?|collected (?:in|by|between)|recorded (?:in|by|between)"
    r"|comes? from|drawn from|dataset|published)",
    re.IGNORECASE,
)

ROWS_RE = re.compile(
    r"(?:\|.*\|)|(?:^\s*[-*]\s+\S)|(?:^\s*\d+[\).]\s)|(?:\brows?\b)|(?:\btable\b)", re.MULTILINE)

NUMBER_RE = re.compile(r"(?<![\w.])\d[\d,]*(?:\.\d+)?")

GAP_RE = re.compile(
    r"(?:do(?:es)? not (?:yet )?have|don'?t (?:yet )?have|doesn'?t (?:yet )?have|no one (?:has )?"
    r"(?:measured|recorded|counted|surveyed)|not (?:available|present|covered|included|recorded|measured)"
    r"|no (?:data|records?|information|figures?|measurements?|counts?) (?:on|for|about|of|here)"
    r"|nothing (?:on|about|here on)|isn'?t (?:covered|there|here)|never (?:been )?(?:measured|recorded|surveyed)"
    r"|not something (?:i|this data|these records) (?:have|has|covers?)|outside what (?:i|this) hold"
    r"|there is no |there are no |missing (?:from|here)|no direct (?:measure|record|count)"
    r"|not tracked|no repeat(?:ed)? (?:survey|visit|measurement)"
    # An absence can also be reported as a name that did not resolve, a route that returned
    # nothing, or a thing the records stop short of being. All three are the same news to a user.
    r"|no recorded \w+|not yet (?:being )?recorded|did not resolve|name non-?match"
    r"|returned no |no supporting |no \w+ rows|does not (?:hold|contain|include)"
    r"|not (?:a )?(?:ready-made|finished|direct|fitted)|only a guide|is not yet tied"
    r"|not (?:yet )?exposed|does not split that out|cannot (?:yet )?show|no ready)",
    re.IGNORECASE,
)

ALTERNATIVES_RE = re.compile(
    r"(?:what (?:i|we) (?:do )?have|what (?:does|is) (?:exist|here)|instead|closest|nearest thing"
    r"|i do hold|available here|the data (?:i|we) (?:do )?have|these (?:records|surveys)"
    r"|plant community|canopy|tree and habitat|restoration plot|point counts?|method notes?"
    r"|existing (?:method|survey|record|plot)|but (?:there|i) (?:is|are|do))",
    re.IGNORECASE,
)

CONFIDENCE_RE = re.compile(
    r"(?:confiden(?:ce|t)|not (?:very )?sure|fairly sure|reasonably sure|rough(?:ly)?|uncertain"
    r"|uncertainty|weak|strong|thin|indicative|suggestive|would not bet|i would bet|shaky"
    r"|cannot (?:tell|separate|rule out)|can'?t (?:tell|separate|rule out)|treat (?:it|this|that) as"
    r"|only as|at best|tentativ\w+|likely|probably|plausib\w+|no more than|careful|caution"
    # Confidence is often carried by a refusal to overclaim rather than by the word "confidence".
    r"|cannot call|can'?t call|would not (?:let|claim|call|stand behind)|wouldn'?t (?:let|claim)"
    r"|not proof|does not prove|is not evidence|descriptive only|only descriptive"
    r"|not yet|do(?:es)? not support|not enough to)",
    re.IGNORECASE,
)

GK_LABEL_RE = re.compile(
    r"(?:in general|generally|broadly speaking|general (?:knowledge|context|ecology|literature)"
    r"|outside (?:this|the) (?:data|site)|not from (?:this|the) (?:data|site|records)"
    r"|elsewhere in the|from the wider|published (?:work|literature|elsewhere)"
    r"|this site'?s own records|from (?:this|the) site'?s own|beyond what (?:this|the) (?:site|data))",
    re.IGNORECASE,
)

# How a join was actually made: same plot, same square, same year, or just the same landscape.
METHOD_RE = re.compile(
    r"(?:same (?:plot|square|place|grid|cell|year|season|visit|survey)|matched (?:on|by)"
    r"|joined (?:on|by)|paired (?:on|by)|within (?:the same|a) |compared (?:within|across)"
    r"|both (?:recorded|seen|counted) in|counted (?:in|within) the same|at the level of"
    r"|per (?:plot|square|visit|hour|transect)|(?:by|per) unit of effort|coarse|fine[- ]grained"
    r"|not (?:the )?same (?:plot|year|visit)"
    # A join can also be disclosed by saying what the table actually records, how unequal the
    # watching behind it was, or what would break comparability. Those are the same admission.
    r"|(?:table|list|ranking|map) is only|only \"?animal recorded|records? of being seen together"
    r"|watched (?:much )?more|watching effort|observation effort|folds? in (?:watching )?effort"
    r"|ranked by how often|rows? versus|records? versus|stand behind it|behind (?:it|them) (?:is|are)"
    r"|does not demonstrate|is not the same as|reflects? where (?:observers|people)"
    r"|stop being (?:cleanly )?comparable|same (?:core )?(?:field )?(?:package|method|definition|timing))",
    re.IGNORECASE,
)

# Asking the user to restate what they already said.
REASK_RE = re.compile(
    r"(?:which plot (?:did|do) you mean|which one (?:did|do) you mean|could you (?:tell|remind|specify)"
    r"|can you (?:tell|remind|specify) me which|what do you mean by|which (?:species|place|plot|area)"
    r" (?:are|were) you (?:referring|talking)|remind me which|i (?:do not|don'?t) know which)",
    re.IGNORECASE,
)

# Inventions: species and interventions this landscape's records do not hold. Used only where the
# spec says a fabrication would be the failure mode.
INVENTION_RE = re.compile(
    r"(?:weeding (?:trial|experiment|record|plot)s?|removal (?:trial|experiment|record)s?"
    r"|herbicide|slash(?:ing)? (?:trial|record)|cut[- ]stump|uprooting (?:record|trial)s?)"
    r"[^.]{0,60}(?:show|record|indicat|found|in this data|here)",
    re.IGNORECASE,
)

PASSIVE_RE = re.compile(
    r"\b(?:was|were|is|are|been|being)\s+(?:\w+ly\s+)?(?:recorded|measured|observed|collected|"
    r"reported|derived|computed|generated|produced|returned|surfaced|represented|considered|"
    r"identified|estimated|counted|sampled|noted|documented)\b",
    re.IGNORECASE,
)

# Database register that is not on the forbidden list but still reads like a console.
DB_NOUN_RE = re.compile(
    r"\b(?:query|queried|filter(?:ed)?|field|column|row-level|record set|attribute|parameter"
    r"|argument|identifier|the system|the tool|the route|the view|output|input)\b",
    re.IGNORECASE,
)

# The site's own named places. A square described only as "10.340-10.350 N, 76.890-76.900 E" is
# not somewhere a person can walk to or write into a proposal, and this landscape has 53 names
# for the places its records come from.
PLACE_NAMES = [
    "Andiparai", "Injiparai", "Injipara", "Iyerpadi", "Kalyanapandal", "Karian-Shola",
    "Karian Shola", "Korangamudi", "Manamboly", "Manamboli", "Murugaali", "Valparai",
    "Pannimade", "Puduthottam", "Puthuthottam", "Sangli", "Sankarankudi", "Selaliparai",
    "Surulimalai", "TataFinley", "Varagaliar", "Varatuparai", "Varattuparai", "Akkamalai",
    "Thenmalai", "Candura", "Kavarkal", "Stanmore", "Sirikundra", "Sholayar", "Anamalai",
]
PLACE_RE = re.compile("|".join(re.escape(p) for p in PLACE_NAMES), re.IGNORECASE)

CONCRETE_RE = re.compile(
    r"\b(?:hornbill|elephant|macaque|langur|gaur|civet|barbet|bulbul|myna|thrush|frog|butterfly"
    r"|lantana|maesa|ficus|fig|tree|seedling|canopy|plot|fragment|transect|rain|monsoon|estate"
    r"|tea|coffee|nest|fruit|seed|leaf|litter|stem|shade|bird|mammal)\w*\b",
    re.IGNORECASE,
)


def strip_markers(text: str) -> str:
    return MARKER_RE.sub(" ", text or "")


def sentences(prose: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+|\n+", prose)
    return [p.strip() for p in parts if p.strip()]


def language_score(prose: str) -> dict:
    """0-2 register score. 2 reads like a field-ecology book; 0 reads like a console."""
    sents = sentences(prose)
    if not sents:
        return {"score": 0.0, "mean_words": 0, "passive": 0, "db_nouns": 0, "concrete": 0}
    lengths = [len(s.split()) for s in sents]
    mean_words = statistics.mean(lengths)
    words = max(1, len(prose.split()))
    passive = len(PASSIVE_RE.findall(prose))
    db_nouns = len(DB_NOUN_RE.findall(prose))
    concrete = len(CONCRETE_RE.findall(prose))

    length_pts = 1.0 if mean_words <= 24 else (0.5 if mean_words <= 32 else 0.0)
    passive_rate = passive / (words / 100.0)
    passive_pts = 0.5 if passive_rate <= 1.5 else (0.25 if passive_rate <= 3.0 else 0.0)
    db_rate = db_nouns / (words / 100.0)
    db_pts = 0.3 if db_rate <= 0.5 else (0.15 if db_rate <= 1.5 else 0.0)
    concrete_pts = 0.2 if concrete >= 3 else (0.1 if concrete >= 1 else 0.0)
    score = round(length_pts + passive_pts + db_pts + concrete_pts, 2)
    return {
        "score": min(2.0, score * 2 / 2.0) if score <= 2 else 2.0,
        "mean_words": round(mean_words, 1),
        "passive": passive,
        "db_nouns": db_nouns,
        "concrete": concrete,
    }


def _check(name: str, ok: bool, detail: str = "") -> dict:
    return {"name": name, "ok": bool(ok), "detail": detail}


def grade_turn(spec_turn: dict, turn: dict) -> dict:
    """Apply the universal checks plus whatever this turn declares."""
    answer = turn.get("answer") or ""
    checks_spec = spec_turn.get("checks") or {}
    prose = strip_markers(answer)
    lowered = prose.lower()
    caps = [c for c in (turn.get("capabilities") or [])]
    results: list[dict] = []

    # --- universal ------------------------------------------------------------------------
    if turn.get("error"):
        results.append(_check("responded", False, turn["error"][:160]))
    else:
        results.append(_check("responded", len(prose.split()) >= 8, f"{len(prose.split())} words"))

    jargon_hits = sorted({m.group(0).lower() for m in JARGON_RE.finditer(prose)})
    results.append(_check("jargon", not jargon_hits, ", ".join(jargon_hits[:8])))

    leak_hits = sorted({m.group(0)[:24] for m in LEAK_RE.finditer(prose)})
    results.append(_check("no_transport_leak", not leak_hits, ", ".join(leak_hits[:4])))

    # A turn is a dead end when the person is left with nothing to do -- neither a move written in
    # the prose nor a button the interface could render. The two are graded apart because the fix
    # differs: prose is the bridge's to write, buttons are the interface's to render.
    dead_hits = sorted({m.group(0)[:40] for m in DEAD_END_RE.finditer(prose)})
    has_next_prose = bool(NEXT_STEP_RE.search(prose))
    has_buttons = int(turn.get("action_buttons") or 0) > 0
    results.append(_check("next_step_in_prose", has_next_prose,
                          "answer names no move the user could make next"))
    results.append(_check("dead_end", (not dead_hits) and (has_next_prose or has_buttons),
                          ", ".join(dead_hits[:3])
                          or "no next move in the prose and no buttons for the interface"))

    # --- declared -------------------------------------------------------------------------
    if checks_spec.get("expect_visual"):
        results.append(_check("visual_present", "<!-- idli-result:" in answer
                              or "<!--idli-result:" in answer,
                              "no result marker on a turn that warrants a picture"))

    if checks_spec.get("capabilities_any"):
        wanted = set(checks_spec["capabilities_any"])
        used = set(caps)
        ok = bool(used & wanted)
        results.append(_check("right_tool", ok,
                              f"ran {sorted(used) or ['nothing']}, wanted one of {sorted(wanted)}"))

    if checks_spec.get("capabilities_not_only"):
        banned_alone = set(checks_spec["capabilities_not_only"])
        used = set(caps)
        ok = not (used and used.issubset(banned_alone))
        results.append(_check("not_catch_all", ok,
                              f"answered a specific question with only {sorted(used)}"))

    if checks_spec.get("expect_numbers"):
        nums = [n for n in NUMBER_RE.findall(prose)]
        results.append(_check("has_evidence", len(nums) >= 1,
                              "no figure on a how-much / which / where question"))

    if checks_spec.get("expect_rows"):
        results.append(_check("rows", bool(ROWS_RE.search(prose)),
                              "no table, list or row language where the user asked for specifics"))

    if checks_spec.get("expect_traceable"):
        results.append(_check("traceable", bool(TRACEABLE_RE.search(prose)),
                              "no survey named and no path to the rows"))

    # These turns were written expecting the data to be absent. Where the product has since found
    # the data and answered with a figure, answering is strictly better than confessing, and the
    # dimension passes -- the thing being tested is "never invent, never dead-end", not "always
    # plead poverty". A turn that neither answers nor admits still fails.
    answered_with_evidence = bool(NUMBER_RE.search(prose))
    stated_gap = bool(GAP_RE.search(prose))

    if checks_spec.get("expect_gap"):
        results.append(_check("honest_gap", stated_gap or answered_with_evidence,
                              "neither a plain statement of what is missing nor a real figure"))

    if checks_spec.get("expect_gap_or_answer"):
        ok = bool(GAP_RE.search(prose)) or bool(NUMBER_RE.search(prose))
        results.append(_check("gap_or_answer", ok, "neither an answer nor an honest gap"))

    if checks_spec.get("expect_alternatives"):
        # Only binding when the answer actually claimed something was missing. Naming "what we
        # have instead" is meaningless when the thing asked for was produced.
        ok = (not stated_gap) or bool(ALTERNATIVES_RE.search(prose))
        results.append(_check("names_alternative", ok,
                              "gap stated without naming what does exist"))

    if checks_spec.get("expect_confidence"):
        results.append(_check("confidence", bool(CONFIDENCE_RE.search(prose)),
                              "no plain statement of how far to trust it"))

    if checks_spec.get("expect_gk_label"):
        results.append(_check("general_knowledge_labelled", bool(GK_LABEL_RE.search(prose)),
                              "site records and general knowledge not separated"))

    if checks_spec.get("expect_place_names"):
        places = sorted({m.group(0) for m in PLACE_RE.finditer(prose)})
        results.append(_check("place_names", bool(places),
                              "places given as coordinates or squares, never by their name"))

    if checks_spec.get("expect_method_disclosure"):
        results.append(_check("join_rule_disclosed", bool(METHOD_RE.search(prose)),
                              "asked how two things were matched, did not say"))

    if checks_spec.get("expect_no_invention"):
        hits = sorted({m.group(0)[:60] for m in INVENTION_RE.finditer(prose)})
        results.append(_check("no_invention", not hits, ", ".join(hits[:3])))

    if checks_spec.get("carry_any"):
        group = checks_spec["carry_any"]
        hit = next((t for t in group if t.lower() in lowered), None)
        results.append(_check("multi_turn", hit is not None,
                              f"dropped the thread: none of {group} came back"))

    if checks_spec.get("expect_no_reask") or checks_spec.get("carry_any"):
        reask = sorted({m.group(0)[:50] for m in REASK_RE.finditer(prose)})
        results.append(_check("no_reask", not reask, ", ".join(reask[:2])))

    if "max_questions" in checks_spec:
        limit = int(checks_spec["max_questions"])
        count = prose.count("?")
        results.append(_check("questions", count <= limit, f"{count} asked, limit {limit}"))

    if "max_sentences" in checks_spec:
        limit = int(checks_spec["max_sentences"])
        count = len(sentences(prose))
        results.append(_check("brevity", count <= limit, f"{count} sentences, limit {limit}"))

    lang = language_score(prose)
    return {
        "turn_id": spec_turn.get("id") or turn.get("id"),
        "user": turn.get("user") or spec_turn.get("user"),
        "answer": answer,
        "capabilities": caps,
        "latency_s": turn.get("latency_s"),
        "retries": turn.get("retries", 0),
        "checks": results,
        "failed": [c["name"] for c in results if not c["ok"]],
        "language": lang,
        "pass": all(c["ok"] for c in results),
    }


def grade_transcript(transcript: dict, spec: dict, notes: list[str] | None = None) -> dict:
    by_id = {c["id"]: c for c in spec["conversations"]}
    graded_convs = []
    for conv in transcript.get("conversations", []):
        source = by_id.get(conv["id"], {})
        spec_turns = {t["id"]: t for t in source.get("turns", [])}
        turns = [grade_turn(spec_turns.get(t["id"], {"id": t["id"]}), t)
                 for t in conv.get("turns", [])]
        graded_convs.append({
            "id": conv["id"],
            "title": source.get("title", conv["id"]),
            "categories": source.get("categories", []),
            "session_id": conv.get("session_id"),
            "turns": turns,
            "turn_pass_rate": round(
                sum(1 for t in turns if t["pass"]) / max(1, len(turns)), 3),
            "pass": all(t["pass"] for t in turns),
        })

    categories: dict[str, list[bool]] = {}
    check_totals: dict[str, list[bool]] = {}
    latencies: list[float] = []
    for conv in graded_convs:
        for turn in conv["turns"]:
            for cat in conv["categories"] or ["uncategorised"]:
                categories.setdefault(cat, []).append(turn["pass"])
            for check in turn["checks"]:
                check_totals.setdefault(check["name"], []).append(check["ok"])
            if turn.get("latency_s"):
                latencies.append(turn["latency_s"])

    all_turns = [t for c in graded_convs for t in c["turns"]]
    langs = [t["language"]["score"] for t in all_turns]
    return {
        "run": transcript.get("run", {}),
        "baseline_notes": notes if notes is not None else (spec.get("baseline_notes") or []),
        "conversations": graded_convs,
        "summary": {
            "turns": len(all_turns),
            "turns_passed": sum(1 for t in all_turns if t["pass"]),
            "turn_pass_rate": round(
                sum(1 for t in all_turns if t["pass"]) / max(1, len(all_turns)), 3),
            "conversations_clean": sum(1 for c in graded_convs if c["pass"]),
            "mean_language_score": round(statistics.mean(langs), 2) if langs else 0,
            "median_latency_s": round(statistics.median(latencies), 1) if latencies else None,
            "max_latency_s": round(max(latencies), 1) if latencies else None,
            "retried_turns": sum(1 for t in all_turns if t.get("retries")),
            "conversation_pass_rate": {
                c["id"]: c["turn_pass_rate"] for c in graded_convs},
            "category_pass_rate": {
                cat: round(sum(1 for ok in vals if ok) / len(vals), 3)
                for cat, vals in sorted(categories.items())},
            "check_pass_rate": {
                name: round(sum(1 for ok in vals if ok) / len(vals), 3)
                for name, vals in sorted(check_totals.items())},
            "check_counts": {name: len(vals) for name, vals in sorted(check_totals.items())},
        },
    }


def _excerpt(text: str, limit: int = 200) -> str:
    prose = " ".join(strip_markers(text).split())
    return (prose[:limit] + "...") if len(prose) > limit else prose


def render_results(graded: dict) -> str:
    run = graded.get("run", {})
    s = graded["summary"]
    out = ["# Ecology ANR bench - results", ""]
    out.append(f"Run: `{run.get('run_id', 'unknown')}`  |  endpoint: `{run.get('base_url', '')}`  "
               f"|  model: `{run.get('model', '')}`  |  started: {run.get('started', '')}")
    out.append("")
    out.append(f"**{s['turns_passed']}/{s['turns']} turns pass ({s['turn_pass_rate'] * 100:.0f}%)**, "
               f"{s['conversations_clean']}/{len(graded['conversations'])} conversations clean, "
               f"mean language score {s['mean_language_score']}/2, "
               f"median latency {s['median_latency_s']}s (max {s['max_latency_s']}s), "
               f"{s['retried_turns']} turns retried.")
    out.append("")
    notes = graded.get("baseline_notes") or []
    if notes:
        out.append("## How this number was baselined")
        out.append("")
        for note in notes:
            out.append(f"- {note}")
        out.append("")
    out.append("## Pass rate by dimension")
    out.append("")
    out.append("| Check | Pass rate | n |")
    out.append("| --- | --- | --- |")
    for name, rate in sorted(s["check_pass_rate"].items(), key=lambda kv: kv[1]):
        out.append(f"| `{name}` | {rate * 100:.0f}% | {s['check_counts'][name]} |")
    out.append("")
    out.append("## Pass rate by conversation")
    out.append("")
    out.append("| Conversation | Turn pass rate |")
    out.append("| --- | --- |")
    for conv in graded["conversations"]:
        out.append(f"| {conv['id']} - {conv['title']} | {conv['turn_pass_rate'] * 100:.0f}% |")
    out.append("")
    out.append("## Pass rate by category")
    out.append("")
    out.append("| Category | Turn pass rate |")
    out.append("| --- | --- |")
    for cat, rate in s["category_pass_rate"].items():
        out.append(f"| {cat} | {rate * 100:.0f}% |")
    out.append("")

    for conv in graded["conversations"]:
        out.append(f"## {conv['id']} - {conv['title']}")
        out.append("")
        out.append(f"Session: `{conv.get('session_id')}`  |  categories: "
                   f"{', '.join(conv['categories'])}")
        out.append("")
        out.append("| Turn | User | Result | Failed | Tools run | Lang | s | Excerpt |")
        out.append("| --- | --- | --- | --- | --- | --- | --- | --- |")
        for turn in conv["turns"]:
            verdict = "PASS" if turn["pass"] else "**FAIL**"
            failed = ", ".join(f"`{n}`" for n in turn["failed"]) or "-"
            latency = f"{turn['latency_s']:.0f}" if turn.get("latency_s") else "-"
            user = turn["user"].replace("|", "/")
            tools = ", ".join(turn["capabilities"]) or "-"
            excerpt = _excerpt(turn["answer"], 160).replace("|", "/")
            out.append(f"| {turn['turn_id']} | {user} | {verdict} | {failed} | {tools} | "
                       f"{turn['language']['score']} | {latency} | {excerpt} |")
        out.append("")
        for turn in conv["turns"]:
            if turn["pass"]:
                continue
            out.append(f"### {conv['id']} / {turn['turn_id']}")
            out.append("")
            out.append(f"User: {turn['user']}")
            out.append("")
            for check in turn["checks"]:
                if not check["ok"]:
                    out.append(f"- `{check['name']}`: {check['detail']}")
            out.append("")
            out.append("```")
            out.append(" ".join(strip_markers(turn["answer"]).split())[:1200] or "(empty)")
            out.append("```")
            out.append("")
    return "\n".join(out) + "\n"


def main(argv: list[str] | None = None) -> int:
    here = pathlib.Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("transcript", type=pathlib.Path)
    parser.add_argument("--conversations", type=pathlib.Path, default=here / "conversations.json")
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
