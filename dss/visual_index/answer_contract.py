#!/usr/bin/env python3
"""What must be said about one result, carried by that result, and checked on the way out.

Four rounds of benchmarking produced one durable finding: a requirement written into the global
prompt displaces another requirement already living there. Adding "say how the two things were
matched" cost the confidence statement; adding "keep sentences short" cost the alternative; the
dimensions took turns failing while the prompt grew. The three fixes that never seesawed were the
three that changed the data the model was given rather than the instructions it was told to
follow.

So requirements move into the data. A result knows what must be said about it — a shared-square
map knows that a shared square is not an interaction, an estimate knows its own confidence basis,
a cell answer knows how big its square is — and each of those travels with that result, competing
with nothing. The producer already writes these sentences into its limitations; this module lifts
them into an explicit contract:

    required_statements: [{id, statement, must_include, why}]

`must_include` is what a deterministic check looks for, so "was it actually said" is a test rather
than a hope. Nothing here invents prose: every statement is one the producing capability already
wrote, and the check either finds it or reports that it is missing.

The second half is `review_answer`, which enforces the invariants that need no judgement at all —
banned wording, sentence length, a figure without its survey, a missing required statement, a
missing next step. It repairs only what can be repaired without authorship: it substitutes the
plain phrase a result already carries, and it splits an over-long sentence at a boundary that is
already in the text. Everything else it reports, for the caller to render or to re-ask.
"""

from __future__ import annotations

import argparse
import json
import re
from typing import Any

CONTRACT_VERSION = "idli-answer-contract/1"

# Wording that belongs to the plumbing, with the phrase a reader would use instead. These are
# substituted, not asked for: a model told to avoid a phrase still repeats the phrase it was
# handed, and this is the only class of fix that needs no judgement at all.
BANNED_WORDING: tuple[tuple[str, str], ...] = (
    (r"\btarget cells\b", "squares inside this site's boundary"),
    (r"\btarget cell\b", "square inside this site's boundary"),
    (r"\bonboarded site records\b", "the data this site has"),
    (r"\bonboarded\b", "recorded"),
    (r"\bsite records\b", "the records"),
    (r"\bindexed (metric|record|event|row)s?\b", r"recorded \1s"),
    (r"\bthis visual\b", "this map"),
    (r"\bsite pack\b", "this site's data"),
    (r"\bparameteris(e|ed|ing)\b", r"point\1 at specific records"),
)

# A grid square's internal id. It is exact, unreadable, and reads to a user as though their
# coordinates were silently replaced.
CELL_ID_IN_TEXT = re.compile(r"\bg\d+\.\d+:-?\d+\.\d+:-?\d+\.\d+")
SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+|\n+")
NUMBER = re.compile(r"(?<![\w.])\d[\d,]*(?:\.\d+)?")
# An offer the reader can accept, rather than a plan being announced at them.
NEXT_STEP = re.compile(
    r"(?:if you want|if you'?d like|would you like|shall i|say the word|tell me which"
    r"|i can (?:show|pull|break|check|map|list|compare|run|plot|split|give)"
    r"|do you want|which (?:one|of these) )",
    re.IGNORECASE,
)
MAX_SENTENCE_WORDS = 26
# Where a long sentence may be broken without rewriting it. Only joins whose second half is
# already an independent clause qualify: splitting at ", which ..." or ", because ..." leaves a
# fragment, and repairing a fragment would mean writing prose, which this module must not do.
# Each entry is (join, what the new sentence starts with).
SPLIT_POINTS: tuple[tuple[str, str], ...] = (
    ("; ", ""),
    (", and ", ""),
    (", but ", "But "),
    (", so ", "So "),
    (". And ", "And "),
)


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split())


def _statement(
    statement_id: str, statement: str, must_include: list[str], why: str
) -> dict[str, Any]:
    return {
        "id": statement_id,
        "statement": _clean(statement),
        # Any one of these appearing in the answer counts as having said it. They are written
        # loosely on purpose: this checks that the point was made, not that it was copied.
        "must_include": [item.casefold() for item in must_include if item],
        "why": _clean(why),
    }


def required_statements(envelope: dict[str, Any]) -> list[dict[str, Any]]:
    """The things that must be said about THIS result, taken from the result itself.

    Ordered by how badly the answer misleads without them. Nothing is invented: each statement is
    the producing capability's own wording, promoted from a limitation it already declared.
    """
    if not isinstance(envelope, dict):
        return []
    statements: list[dict[str, Any]] = []
    audit = envelope.get("audit") if isinstance(envelope.get("audit"), dict) else {}
    answer = envelope.get("answer") if isinstance(envelope.get("answer"), dict) else {}
    limitations = [
        item for item in (envelope.get("limitations") or []) if isinstance(item, dict)
    ]
    by_code = {str(item.get("code") or ""): item for item in limitations}

    # 1. How two things were matched. A shared-square map is the one result most likely to be
    #    read as something it is not, and it already says so in its own words.
    join = by_code.get("shared-square-is-not-interaction")
    if join is not None:
        statements.append(_statement(
            "join-rule", join.get("message"),
            ["same square", "same 1.1 km", "same map square", "not an interaction",
             "not proof", "recorded in the same"],
            "A reader who is not told the join rule will read co-occurrence as contact.",
        ))
    same_year = by_code.get("records-not-contemporaneous") or by_code.get("same-year-only")
    if same_year is not None:
        statements.append(_statement(
            "same-year", same_year.get("message"),
            ["same year", "any time", "different years"],
            "Two records in one square may be years apart.",
        ))

    # 2. An estimate that is not said to be worked out reads as a measurement.
    estimate = audit.get("estimate") if isinstance(audit.get("estimate"), dict) else {}
    if estimate.get("estimate") is not None:
        statements.append(_statement(
            "estimate-is-modelled",
            "This value is worked out from other squares, not counted on the ground.",
            ["worked out", "modelled", "estimate", "not counted", "not measured"],
            "A modelled value presented flat is indistinguishable from an observation.",
        ))
        basis = _clean(estimate.get("confidence_basis"))
        if basis:
            statements.append(_statement(
                "estimate-confidence",
                f"Say how far to trust it and why, in everyday words: {basis}",
                ["rough", "reasonably solid", "confiden", "trust", "wide", "narrow",
                 "learned from", "learnt from", "surveyed squares"],
                "A range without its basis invites the reader to treat it as precise.",
            ))
    # 3. Which square, said as an extent rather than an id.
    description = _clean(estimate.get("cell_description_short"))
    if description:
        statements.append(_statement(
            "which-square", f"Name the square as {description}.",
            ["km square", "square covering", "spanning"],
            "The grid labels squares by their south-west corner, so an id reads as a "
            "changed coordinate.",
        ))

    # 4. Pairs, priority rankings and record counts each carry one claim they must not overstate.
    if audit.get("interaction_pairs"):
        statements.append(_statement(
            "pairs-are-records",
            "These are records of being seen together, not proof that seed was moved.",
            ["seen together", "recorded together", "not proof", "does not prove",
             "not demonstrate"],
            "A frugivory pair list is otherwise read as a demonstrated function.",
        ))
    if audit.get("survey_priority"):
        statements.append(_statement(
            "gap-not-richness",
            "This ranks where the data is thinnest, not where the ecology is richest.",
            ["thinnest", "least", "gap", "not where the ecology", "not richest",
             "little or no"],
            "A priority list is otherwise read as a ranking of ecological value.",
        ))
    if audit.get("co_occurrence"):
        statements.append(_statement(
            "effort-shapes-overlap",
            "Where records overlap partly shows where people looked.",
            ["where people looked", "survey effort", "watching effort", "looked",
             "recording effort"],
            "Overlap follows observers as well as animals.",
        ))

    # 5. Any figure must name the survey it came from. The wrong attribution sent a user to
    #    revisit the wrong plots, which is worse than no attribution at all.
    sources = [
        _clean(item.get("title")) for item in (audit.get("source_versions") or [])
        if isinstance(item, dict) and item.get("title")
    ]
    if sources and NUMBER.search(_clean(answer.get("headline"))):
        statements.append(_statement(
            "name-the-survey",
            "Name the survey each figure came from: " + "; ".join(sources[:4]) + ".",
            [word for title in sources[:4] for word in _significant_words(title)],
            "A real count attributed to the wrong survey sends someone to the wrong plots.",
        ))
    return statements


def _significant_words(title: str) -> list[str]:
    """The words from a survey title that would identify it if quoted in a sentence."""
    stop = {
        "the", "a", "an", "of", "and", "or", "in", "at", "on", "for", "from", "with", "to",
        "survey", "records", "record", "data", "study", "synthetic", "dataset",
    }
    words = [
        word.casefold() for word in re.findall(r"[A-Za-z][A-Za-z-]{3,}", title or "")
        if word.casefold() not in stop
    ]
    return words[:4]


def repair_wording(text: str, cell_description: str = "") -> tuple[str, list[str]]:
    """Substitute plumbing wording for the reader's wording. No judgement, no new claims."""
    repaired = str(text or "")
    applied: list[str] = []
    for pattern, replacement in BANNED_WORDING:
        repaired, count = re.subn(pattern, replacement, repaired, flags=re.IGNORECASE)
        if count:
            applied.append(re.sub(r"\\b|\(|\)|\?|\+|\*", "", pattern))
    if CELL_ID_IN_TEXT.search(repaired):
        repaired = CELL_ID_IN_TEXT.sub(cell_description or "that map square", repaired)
        applied.append("grid square id")
    return repaired, applied


def split_long_sentences(text: str, limit: int = MAX_SENTENCE_WORDS) -> tuple[str, int]:
    """Break over-long sentences at joins the writer already used. Never rewrites words."""
    if not text:
        return text, 0
    split_count = 0
    out_lines = []
    for line in text.split("\n"):
        if not line.strip() or line.lstrip().startswith(("|", ">", "#", "<!--", "```")):
            out_lines.append(line)
            continue
        pieces = []
        for sentence in SENTENCE_SPLIT.split(line):
            if not sentence.strip():
                continue
            current = sentence
            while len(current.split()) > limit:
                cut = _best_split(current)
                if cut is None:
                    break
                start, end, prefix = cut
                head, tail = current[:start].rstrip(" ,;"), current[end:].lstrip()
                if not tail:
                    break
                if not head.endswith((".", "!", "?")):
                    head += "."
                pieces.append(head)
                current = prefix + (tail if prefix else tail[0].upper() + tail[1:])
                split_count += 1
            if current.strip():
                pieces.append(current.strip())
        out_lines.append(" ".join(pieces) if pieces else line)
    return "\n".join(out_lines), split_count


def _best_split(sentence: str) -> tuple[int, int, str] | None:
    """The join nearest the middle of the sentence, so both halves stay readable."""
    middle = len(sentence) / 2
    best: tuple[float, int, int, str] | None = None
    for marker, prefix in SPLIT_POINTS:
        start = 0
        while True:
            found = sentence.find(marker, start)
            if found == -1:
                break
            head_words = len(sentence[:found].split())
            tail_words = len(sentence[found + len(marker):].split())
            if head_words >= 5 and tail_words >= 5:
                distance = abs(found - middle)
                if best is None or distance < best[0]:
                    best = (distance, found, found + len(marker), prefix)
            start = found + 1
    if best is None:
        return None
    return best[1], best[2], best[3]


def review_answer(
    text: str, statements: list[dict[str, Any]] | None = None,
    *, cell_description: str = "", expect_next_step: bool = True,
    limit: int = MAX_SENTENCE_WORDS,
) -> dict[str, Any]:
    """Enforce the invariants that need no judgement, and report the ones that do.

    Repairs are limited to substituting wording the result already carries and splitting a
    sentence at a join already present in it. Anything that would need new prose — a missing
    required statement, a missing offer — is reported, never written.
    """
    original = str(text or "")
    repaired, substitutions = repair_wording(original, cell_description)
    repaired, splits = split_long_sentences(repaired, limit)
    prose = re.sub(r"<!--.*?-->", " ", repaired, flags=re.DOTALL)
    lowered = prose.casefold()

    missing = []
    for item in statements or []:
        include = item.get("must_include") or []
        if include and not any(token in lowered for token in include):
            missing.append({
                "id": item.get("id"), "statement": item.get("statement"),
                "why": item.get("why"),
            })
    sentences = [item for item in SENTENCE_SPLIT.split(prose) if item.strip()]
    long_sentences = [item for item in sentences if len(item.split()) > limit]
    issues: list[dict[str, Any]] = []
    if missing:
        issues.append({
            "code": "required-statement-missing",
            "detail": [item["id"] for item in missing],
        })
    if long_sentences:
        issues.append({
            "code": "sentence-too-long",
            "detail": [len(item.split()) for item in long_sentences][:5],
        })
    if expect_next_step and not NEXT_STEP.search(prose):
        issues.append({"code": "no-next-step", "detail": []})
    return {
        "schema_version": CONTRACT_VERSION,
        "text": repaired,
        "changed": repaired != original,
        "substitutions": substitutions,
        "sentences_split": splits,
        "missing_statements": missing,
        "issues": issues,
        "mean_sentence_words": (
            round(sum(len(item.split()) for item in sentences) / len(sentences), 1)
            if sentences else 0.0
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--result", type=argparse.FileType("r"), required=True)
    parser.add_argument("--answer", type=argparse.FileType("r"))
    args = parser.parse_args(argv)
    envelope = json.load(args.result)
    statements = required_statements(envelope)
    if args.answer is None:
        print(json.dumps(statements, indent=2, ensure_ascii=False))
        return 0
    print(json.dumps(
        review_answer(args.answer.read(), statements), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
