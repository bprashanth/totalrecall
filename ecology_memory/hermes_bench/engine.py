#!/usr/bin/env python3
"""General compiler → deterministic executor → audited responder experiment engine.

No question/topic regex is used here. The compiler receives the frozen algebra and the executor's
machine-readable capability catalog, then emits an IR tree. Evidence labels remain code-owned.
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
from copy import deepcopy
from typing import Callable


HERE = os.path.dirname(os.path.abspath(__file__))
MEMORY = os.path.dirname(HERE)
HARNESS = os.path.join(MEMORY, "harness")
RUNTIME = os.path.join(MEMORY, "integration", "runtime")
for path in (HARNESS, RUNTIME):
    if path not in sys.path:
        sys.path.insert(0, path)

import connectors as C  # noqa: E402
import parser as P  # noqa: E402
from executor import execute  # noqa: E402
from ir_schema import ALLOWED_FIELDS, canonicalize, validate  # noqa: E402
from llm import chat  # noqa: E402


SITE_ALIASES = {"ebtl", "ebtl analysis bbox", "elephants by the lake", "our site", "the site",
                "restoration site"}
SITE_CANONICAL = "Elephants by the Lake"


StageObserver = Callable[[str, dict], None]


def _observe(observer: StageObserver | None, stage: str, **payload) -> None:
    """Expose real pipeline boundaries to diagnostic clients without changing production flow."""
    if observer is not None:
        observer(stage, payload)


def _bind_context(value, context, parent_key=None):
    """Bind only the explicitly selected dialogue context, never a benchmark-default place."""
    if context != "ebtl":
        return value
    if isinstance(value, list):
        return [_bind_context(item, context, parent_key) for item in value]
    if isinstance(value, dict):
        out = {key: _bind_context(item, context, key) for key, item in value.items()}
        if out.get("op") == "REGION":
            place = " ".join(str(out.get("place", "")).lower().split()).strip(" .,;:")
            if place in SITE_ALIASES or place == "?place":
                out["place"] = SITE_CANONICAL
        return out
    if parent_key in {"region", "target"} and value == "?place":
        return {"op": "REGION", "place": SITE_CANONICAL}
    return value


GENERIC_FEWSHOT = [
    P.DEFAULT_FEWSHOT[0],   # scalar count
    P.DEFAULT_FEWSHOT[1],   # trend
    P.DEFAULT_FEWSHOT[2],   # relation
    P.DEFAULT_FEWSHOT[3],   # transfer
    P.DEFAULT_FEWSHOT[4],   # honest holes
    P.DEFAULT_FEWSHOT[10],  # chained positive/negative relation
    P.DEFAULT_FEWSHOT[12],  # n-ary ranking
    {"q": "What is the elevation at the monitoring sites in Quito?",
     "ir": {"op": "ANNOTATE", "layer": "elevation",
            "source": {"op": "SELECT", "entity": "monitoring site",
                       "region": {"op": "REGION", "place": "Quito, Ecuador"},
                       "time": None}}},
    {"q": "Why do households near Kisumu collect fuelwood?",
     "ir": {"op": "SELECT", "entity": "?proxy", "region": "?place", "time": None}},
]

RESPONDER_SYSTEM = """You are the final response layer for a conservation NGO analyst.
The JSON evidence pack below was produced by deterministic algebra and connectors. Answer the
CURRENT question in clear everyday English, normally 1-3 short paragraphs.

Hard rules:
1. Use only facts, names and numbers present in the CURRENT AUDITED RESULT, a PRIOR AUDITED RESULT
   explicitly included in conversation context, or explicitly supplied by the user. Prior answer
   prose is not evidence and will not be supplied.
2. Preserve evidence class and spatial/temporal grain. Say proxy/modelled/indirect/regional when
   those labels apply. An analysis bbox is not the property; a record is not abundance; non-detection
   is not absence; transfer is not local observation.
3. If status=data_request, say what is unknown and make one concrete DATA REQUEST: what to measure,
   where, when/effort. Do not guess a number.
4. Lead with the answer. Do not mention JSON, IR, algebra, internal routing, plans or thought process.
5. Never add a species, causal mechanism, recommendation or measurement that is absent from the
   audited result. You may explain the practical implication of a stated limitation.
6. "Documented for the property" is not the same as "encountered during this survey". Preserve
   record_status and any explicit encountered-versus-older split.
7. In a transfer audit, locally_observed=true with transfer_admissible=false means transfer is
   unnecessary because the item is already observed; it never means local observations are absent.
8. Never expose typed-hole names such as ?proxy or ?place. Describe the missing measurement in
   ordinary language. For a data request you may propose a standard measurement design directly
   implied by the user's request, but do not invent a site fact.
9. If reason=ambiguous_request, data is not missing. Ask one short clarification and offer the
   supplied candidate capabilities in everyday language; never claim the record contains no data.
10. Do not classify a numeric result as low, high, minimal, severe, safe or risky unless the
    audited result supplies an explicit threshold or category. Without one, report the number and
    say that it is not itself a calibrated risk class.
11. A field survey cannot definitively prove ecological absence. Request repeat detection/non-
    detection effort with its place, season and method. Never recommend deliberately approaching
    wildlife merely to turn indirect evidence into a direct encounter.
12. Preserve declared measurement names and units exactly. Do not rename records, pixels,
    pixel-fire-days, densities, indices or proxy scores as animals, events, fires, area or risk.
13. A zero sensor or database result must be phrased as zero detections/records by that source,
    never as “no observed fires/animals,” “none exist,” or proof that the phenomenon did not occur.
14. A declared analysis bbox, search bbox, buffer or centre point is never the surveyed property
    polygon. Use its exact supplied name and do not attach the property's acreage to it. When the
    result contains measurements at two or more spatial grains, describe each measurement under
    its own supplied scope; never substitute one scope for another or merge their findings.
15. If value.kind is conversation_evidence, keep every ledger row's evidence boundary intact.
    Do not move a species, evidence class, survey method or data request from one row to another.
    Match each proposed collection to the decision gap it actually closes. A requested short brief
    may use up to 300 words; otherwise remain within 230 words. Never group ledger rows carrying
    different labels under one shared label. If a ledger assessment says locally_observed=true,
    never describe that species as unobserved, regional-only, or a transfer candidate.
16. Preserve the distinct meanings of a per-cell similarity floor and a fraction-of-target-cells
    pass threshold. Use only explicitly named threshold fields; never infer a global threshold from
    one candidate's observed fraction. A request for local observations validates presence and does
    not change a previously failed environmental gate.
17. Never claim that one field effort can confirm, prove, establish or rule out ecological absence.
    Report detections and non-detections under the stated method, season and effort instead.
18. A returned occurrence-record count is not a named-taxon count. When both are supplied, report
    them separately and never describe the record count as species or taxa.
19. If local_interaction_admissible=false, say the local interaction is unknown or unsupported.
    Never turn a zero local record count into a claim that the interaction cannot occur.
20. If value.grain is occurrence-proximity-relation, report the left/right record denominators,
    matched-left count, threshold and search scope. Call it a spatial occurrence-record proxy.
    It does not establish interaction, avoidance, habitat preference, simultaneous presence, or
    target-site occurrence when the search region is broader than the target.
21. If value.grain is target-bbox-suitability-fraction, describe it only as the fraction of target
    analysis cells classified suitable by the named model. It is not a calibrated probability of
    occurrence, occupancy, abundance, prevalence, or current presence. Do not call the fraction
    low/high or infer limited/likely/widespread presence unless the audited result supplies an
    explicit calibration category for that inference.
22. If any spatial support has method=bbox-approx, explicitly call the search support an
    approximate bbox (or approximate search extent). Never call it an exact radius polygon,
    surveyed boundary, property, or complete survey area.
"""


def strip_reasoning(text: str) -> str:
    """Remove serving-shim reasoning leakage without altering answer prose."""
    text = (text or "").strip()
    if "</think>" in text:
        text = text.rsplit("</think>", 1)[-1].strip()
    text = re.sub(r"^Thinking Process:.*?(?=\n\s*[^\d*#-])", "", text,
                  flags=re.DOTALL | re.IGNORECASE).strip()
    # Some chat-tuned local models serialize an assistant message instead of returning its content.
    # Unwrap only a whole, valid JSON object with a string `content`; never scrape arbitrary braces.
    if text.startswith("{") and text.endswith("}"):
        try:
            envelope = json.loads(text)
            if isinstance(envelope, dict) and isinstance(envelope.get("content"), str):
                text = envelope["content"].strip()
        except json.JSONDecodeError:
            pass
    # Local responder shims can serialize a short plan before and/or after an otherwise usable
    # answer. Strip only paragraphs that announce the response-writing task; factual first-person
    # prose in the middle remains untouched.
    plan_edge = re.compile(
        r"^(?:The user (?:is asking|wants)|Let me |I (?:need|should|have) |"
        r"I(?:'ll| will) |Now I |Looking at |Alright, let me|I've read|First, I)", re.I)
    paragraphs = [item.strip() for item in re.split(r"\n\s*\n", text) if item.strip()]
    while len(paragraphs) > 1 and plan_edge.match(paragraphs[0]):
        paragraphs.pop(0)
    while len(paragraphs) > 1 and plan_edge.match(paragraphs[-1]):
        paragraphs.pop()
    text = "\n\n".join(paragraphs)
    return text


def sanitize_user_answer(text: str) -> str:
    """Remove internal protocol vocabulary without discarding useful grounded prose."""
    replacements = (
        (r"\bcurrent audited result\b", "available record"),
        (r"\ba\s+[`\"']?data_request[`\"']?\s+status\b", "a need for new data"),
        (r"[`\"']?data_request[`\"']?\s+status\b", "need for new data"),
        (r"[`\"']?unbound_holes[`\"']?", "missing measurements"),
        (r"[`\"']?data_request[`\"']?", "need for new data"),
        (r"\bconfirm the presence or absence of\b",
         "record detections and non-detections under the stated effort for"),
        (r"\bconfirm or rule out the presence of\b",
         "record detections and non-detections under the stated effort for"),
        (r"\bconfirm the absence of\b",
         "record non-detections under the stated effort for"),
    )
    for pattern, replacement in replacements:
        text = re.sub(pattern, replacement, text, flags=re.I)
    return text


def _semantic_critic(question: str, ir: dict | None, critic: str,
                     history: list[dict], capabilities: list[dict] | None = None
                     ) -> tuple[dict | None, str, list[str]]:
    """General LLM IR verifier: measurement faithfulness, catalog selection, and tree shape."""
    messages = P.build_messages(
        question, fewshot=GENERIC_FEWSHOT, history=history,
        capabilities=capabilities or C.capability_catalog()
    )
    messages.extend([
        {"role": "assistant", "content": json.dumps(ir, ensure_ascii=False)},
        {"role": "user", "content": (
            "Act as a semantic compiler verifier. The previous tree may validate syntactically but "
            "still answer the wrong measurement. Recompile the SAME current question. Select a "
            "catalog capability only when its returned measurement can answer the request; a broad "
            "site summary is not evidence about a named unsupported human, treatment, causal, or "
            "time-series measure. Human motives/resource use require ?proxy. Preserve an honest "
            "hole when the requested measure is absent. Obey every catalog required shape, "
            "especially ANNOTATE layers. A valid composed root is semantic: never collapse RELATE, "
            "ESTIMATE, COMPARE, RANK, or AGGREGATE into a convenient SELECT. RELATE needs both "
            "requested operands; occurrence proximity is not interaction or same-time observation. "
            "BUFFER controls search extent while RELATE.threshold_km controls pairwise distance. "
            "ESTIMATE needs donor records and a distinct target; do not wrap a RELATE result in "
            "ESTIMATE because joint-relation transfer has no admitted contract. A selected data row "
            "with binding=compiler_entity is a connector class, never a literal SELECT entity: bind "
            "each leaf to the concrete entity or taxon named in the current request. A selected "
            "region support row supplies its declared place to the relevant search leaves. Do not add facts or "
            "explain. Output ONLY the corrected "
            "complete JSON tree."
        )},
    ])
    try:
        raw = chat(critic, messages, temperature=0.0, max_tokens=3000, use_cache=True,
                   timeout=90, retries=1)
    except RuntimeError as exc:
        return ir, f"[llm-error] {exc}", ["semantic_critic:call_failed"]
    events: list[str] = []
    candidate = P.extract_json(raw, events)
    candidate = P.faithfulness_pass(P.mech_repair(candidate), question + " " + " ".join(
        str(item.get("content") or "") for item in history if isinstance(item, dict)))
    if candidate is None or not validate(candidate)["valid"]:
        return ir, raw, events + ["semantic_critic:invalid_rejected"]
    if json.dumps(candidate, sort_keys=True) == json.dumps(ir, sort_keys=True):
        events.append("semantic_critic:confirmed")
    else:
        events.append("semantic_critic:corrected")
    return candidate, raw, events


def _select_capabilities(question: str, selector: str,
                         history: list[dict],
                         observer: StageObserver | None = None
                         ) -> tuple[list[dict], str, list[str], str]:
    """Use an LLM as a semantic capability lookup, not as an evidence source."""
    selector, verify_sep, verifier = selector.partition(">")
    catalog = C.capability_catalog()
    compact = [{key: item.get(key) for key in
                ("entity", "kind", "source_entity", "description", "grain", "evidence",
                 "includes", "excludes", "binding", "ops", "requires", "place", "scope",
                 "scope_policy")
                if item.get(key) is not None}
               for item in catalog]
    context = [{"role": item.get("role"), "content": str(item.get("content") or "")[:700]}
               for item in history[-6:] if isinstance(item, dict)]
    prompt = (
        "Select executable capabilities for compiling the CURRENT user request. Capabilities are "
        "measurements, not facts. Return ONLY JSON "
        "{\"mode\":\"execute\"|\"clarify\"|\"synthesize_history\",\"entities\":[exact catalog entity names]}. "
        "Use clarify when the request names a place or subject but gives no measurement and several "
        "different catalog capabilities are equally plausible; return the few candidate entities. "
        "Use synthesize_history only when the current request explicitly asks to summarize, brief, "
        "or prioritize evidence already established in this conversation without collecting a new "
        "measurement; then return no entities. Otherwise use execute. "
        "For execute, return the smallest sufficient SET of at most four ingredients. An atomic "
        "request normally needs one data capability. A relation, estimate, comparison, ranking, or "
        "buffered search may require an operator capability, one or more data capabilities, and a "
        "declared region support capability. Operator and region rows are executable grammar/support, "
        "not datasets and never replace the operands. Do not add capabilities for variables the user "
        "explicitly asks you to identify as missing. If the required measurement or operand is not "
        "declared, return an empty list. When a request names taxa and explicitly asks for occurrence "
        "records in a widened or nonlocal search region, use the generic named-taxon occurrence "
        "capability for every taxon operand; do not also select a site-only event, inventory, or "
        "overview merely because a taxon or place name overlaps. Do "
        "not choose a broad site summary merely because the place matches. If the request is for "
        "an unsupported human behavior, treatment comparison, causal claim, or time series, return "
        "an empty list so the compiler emits a typed hole/DataRequest. A raster layer capability "
        "is valid only through its declared ANNOTATE shape. Conversation context resolves follow-"
        "ups but does not add capabilities.\n\nCATALOG:\n" +
        json.dumps(compact, ensure_ascii=False) + "\n\nCONTEXT:\n" +
        json.dumps(context, ensure_ascii=False) + "\n\nCURRENT REQUEST:\n" + question
    )
    try:
        raw = chat(selector, [{"role": "user", "content": prompt}], temperature=0.0,
                   max_tokens=400, use_cache=True, timeout=90, retries=1)
        obj = P.extract_json(raw)
    except RuntimeError as exc:
        return (catalog, f"[llm-error] {exc}",
                ["capability_selector:call_failed_all_retained"], "execute")
    mode = obj.get("mode", "execute") if isinstance(obj, dict) else "execute"
    if mode not in {"execute", "clarify", "synthesize_history"}:
        mode = "execute"
    names = obj.get("entities") if isinstance(obj, dict) else None
    has_audited_history = any(
        isinstance(item, dict) and item.get("role") == "assistant" and
        str(item.get("content") or "").startswith("AUDITED EVIDENCE: ")
        for item in history
    )
    # A first-turn request cannot be a history synthesis. Ask the semantic selector to resolve the
    # same wording against current capabilities instead of inventing an empty conversation brief.
    if mode == "synthesize_history" and not has_audited_history:
        retry_prompt = (prompt +
            "\n\nCONSTRAINT: There are no prior audited results in this conversation, so "
            "synthesize_history is impossible. Reselect a current executable capability or use "
            "clarify. Return only the required JSON object.")
        try:
            retry_raw = chat(selector, [{"role": "user", "content": retry_prompt}],
                             temperature=0.0, max_tokens=400, use_cache=True,
                             timeout=90, retries=1)
            retry_obj = P.extract_json(retry_raw)
            retry_mode = retry_obj.get("mode") if isinstance(retry_obj, dict) else None
            retry_names = retry_obj.get("entities") if isinstance(retry_obj, dict) else None
            if retry_mode in {"execute", "clarify"} and isinstance(retry_names, list):
                raw = retry_raw
                obj = retry_obj
                mode = retry_mode
                names = retry_names
        except RuntimeError:
            mode = "clarify"
            names = []
    if not isinstance(names, list) or not all(isinstance(name, str) for name in names):
        return catalog, raw, ["capability_selector:invalid_all_retained"], "execute"
    by_name = {item["entity"]: item for item in catalog}
    selected = [{**by_name[name], "selected": True} for name in names if name in by_name]
    # Clarification represents a real choice among measurements. If semantic lookup has already
    # narrowed the request to exactly one executable capability, execute it instead of asking the
    # user to choose that same single item again.
    if mode == "clarify" and len(selected) == 1:
        mode = "execute"
    _observe(
        observer, "capability_selected", model=selector, prompt=prompt,
        raw_output=raw, parsed={"mode": mode, "entities": names},
        selected=selected,
    )
    verify_raw = None
    if verify_sep and mode == "execute" and selected:
        verify_prompt = (
            "Audit a semantic capability selection for the CURRENT request. Capabilities return "
            "only the measurements in their descriptions. Return the smallest sufficient SET of "
            "zero to four catalog capabilities. An atomic request normally needs one data row; a "
            "composed request may need operator, operand-data, and region-support rows. Operator and "
            "region rows are ingredients, never answer datasets. Prefer a declared composite data "
            "capability when it includes all needed leaves. "
            "Variables that the user asks you to identify as MISSING are evidence gaps, not extra "
            "capabilities to execute. If the request genuinely needs multiple independent capabilities "
            "and the catalog lacks a required operator or operand, return none. You may retain the initial "
            "selection, replace a relevant-but-too-broad capability with a more specific catalog "
            "capability, or return no capability when the measurement is unsupported. Retain a capability when its described "
            "domain and fields directly supply the evidence needed to answer, including when the "
            "request explicitly asks whether that evidence is insufficient for a stronger claim. "
            "Insufficient relevant evidence is useful; an unrelated source is not. A broad overview cannot "
            "establish absence of a named treatment outcome, causal claim, time series, or human "
            "behavior. For a relation, both operand measurements plus the RELATE operator must be "
            "admitted; a site summary is not an operand. Return ONLY JSON {\"entities\":[zero to "
            "four exact catalog names]}."
            "\n\nREQUEST:\n" + question + "\n\nSELECTED:\n" +
            json.dumps(selected, ensure_ascii=False) + "\n\nFULL CATALOG:\n" +
            json.dumps(compact, ensure_ascii=False)
        )
        try:
            verify_raw = chat(verifier, [{"role": "user", "content": verify_prompt}],
                              temperature=0.0, max_tokens=5000, use_cache=True,
                              timeout=120, retries=2)
            verified_obj = P.extract_json(verify_raw)
            verified_names = verified_obj.get("entities") if isinstance(verified_obj, dict) else None
            admitted = set(by_name)
            if isinstance(verified_names, list) and len(verified_names) <= 4 and all(
                    isinstance(name, str) and name in admitted for name in verified_names):
                initial_names = [item["entity"] for item in selected]
                # An empty verifier decision contradicts a non-empty semantic selection. Resolve
                # that disagreement explicitly rather than allowing either model to win by role.
                # This is a general semantic adjudication pass over the same declared catalog; it
                # does not inspect topic words or authorize undeclared connector behavior.
                if (not verified_names and initial_names and
                        any(item.get("includes") for item in selected)):
                    adjudication_prompt = (
                        verify_prompt + "\n\nDISAGREEMENT: The initial selector chose " +
                        json.dumps(initial_names, ensure_ascii=False) +
                        " but the verifier returned no capability. Adjudicate whether one exact "
                        "catalog capability SET directly supplies the requested measurement. "
                        "A broad overview does not answer a treatment, causal, human-behavior or "
                        "time-series request. For a requested interaction or relationship between "
                        "two entities, the set must include a relation operator and executable data "
                        "for both operands; evidence about only one subject is insufficient. A "
                        "capability that explicitly returns the requested "
                        "audit, gates, insufficiency or bounded proxy is relevant even if it cannot "
                        "support the stronger conclusion. Return ONLY JSON {\"entities\":[zero to "
                        "four exact catalog names]}."
                    )
                    try:
                        adjudication_raw = chat(
                            selector, [{"role": "user", "content": adjudication_prompt}],
                            temperature=0.0, max_tokens=1000, use_cache=True,
                            timeout=90, retries=1)
                        adjudication_obj = P.extract_json(adjudication_raw)
                        adjudicated_names = (adjudication_obj.get("entities")
                                             if isinstance(adjudication_obj, dict) else None)
                    except RuntimeError:
                        adjudicated_names = None
                    if (isinstance(adjudicated_names, list) and
                            len(adjudicated_names) <= 4 and all(
                                isinstance(name, str) and name in admitted
                                for name in adjudicated_names)):
                        selected = [{**by_name[name], "selected": True}
                                    for name in adjudicated_names]
                        events = ["capability_verifier:disagreement_adjudicated:" +
                                  ",".join(adjudicated_names)]
                    else:
                        selected = []
                        events = ["capability_verifier:disagreement_failed_closed"]
                elif not verified_names and initial_names:
                    selected = []
                    events = ["capability_verifier:empty_atomic_failed_closed"]
                else:
                    selected = [{**by_name[name], "selected": True} for name in verified_names]
                    disposition = "retained" if verified_names == initial_names else "reselected"
                    events = [f"capability_verifier:{disposition}:" + ",".join(verified_names)]
            else:
                selected = []
                events = ["capability_verifier:invalid_failed_closed"]
        except RuntimeError:
            # A frontier verifier outage must not authorize a broader executable set. Give the
            # already-running selector one constrained adequacy pass, then fail closed if that is
            # also unavailable or invalid.
            try:
                fallback_raw = chat(selector, [{"role": "user", "content": verify_prompt}],
                                    temperature=0.0, max_tokens=1000, use_cache=True,
                                    timeout=90, retries=1)
                fallback_obj = P.extract_json(fallback_raw)
                fallback_names = (fallback_obj.get("entities")
                                  if isinstance(fallback_obj, dict) else None)
                if isinstance(fallback_names, list) and len(fallback_names) <= 4 and all(
                        isinstance(name, str) and name in by_name for name in fallback_names):
                    selected = [{**by_name[name], "selected": True} for name in fallback_names]
                    events = ["capability_verifier:fallback_selector:" +
                              ",".join(fallback_names)]
                else:
                    selected = []
                    events = ["capability_verifier:fallback_invalid_failed_closed"]
            except RuntimeError:
                selected = []
                events = ["capability_verifier:call_failed_closed"]
    else:
        events = []
    # Operator dependencies are part of the catalog contract. Expand them mechanically so a
    # selector cannot authorize ESTIMATE/RELATE while omitting the executable data leaf it needs.
    required_names = {name for item in selected for name in item.get("requires", [])}
    present_names = {item["entity"] for item in selected}
    for name in required_names - present_names:
        if name in by_name:
            selected.append({**by_name[name], "selected": True})
            events.append("capability_selector:required_added:" + name)
    # Capability containment is declared by the connector, so a composite capability can dominate
    # redundant leaves without a question/topic rule. This is what lets dynamic discovery expose a
    # single executable contract even when the selector asks for both its local and regional parts.
    covered = {name for item in selected for name in item.get("includes", [])}
    if covered:
        selected = [item for item in selected if item["entity"] not in covered]
    # A declared nonlocal search support plus a generic region-bindable data leaf makes site-only
    # rows incompatible redundant ingredients. This is metadata containment, not a topic route.
    # It prevents a local event card from replacing one operand of a regional point relation.
    has_region_support = (any(item.get("binding") == "region" for item in selected) or
                          any("BUFFER" in item.get("ops", []) for item in selected))
    has_region_data = any(item.get("binding") == "compiler_entity" and
                          item.get("scope") == "requested region" for item in selected)
    has_composition = any(item.get("binding") == "operator" for item in selected)
    if has_region_support and has_region_data and has_composition:
        selected = [item for item in selected if item.get("scope") != "declared EBTL site"]
    unknown = [name for name in names if name not in by_name]
    events.insert(0, "capability_selector:selected:" +
                  ",".join(item["entity"] for item in selected))
    if unknown:
        events.append("capability_selector:unknown_ignored:" + ",".join(unknown))
    events.append("capability_selector:mode:" + mode)
    _observe(
        observer, "capability_verified", model=(verifier if verify_sep else None),
        raw_output=verify_raw, mode=mode, selected=selected, events=events,
    )
    return selected, raw, events, mode


def _history_synthesis_execution(history: list[dict]) -> dict:
    """Expose prior code-owned audit summaries as a dialogue-layer evidence ledger.

    The frozen algebra deliberately represents one data question, not a request to summarize a
    conversation. Keeping this operation outside the IR prevents an invented ANNOTATE layer while
    still giving the responder only auditable material.
    """
    rows = []
    pending_question = None
    for item in history:
        if not isinstance(item, dict):
            continue
        role = item.get("role")
        content = str(item.get("content") or "")
        if role == "user":
            pending_question = content
        elif role == "assistant" and content.startswith("AUDITED EVIDENCE: "):
            try:
                evidence = json.loads(content[len("AUDITED EVIDENCE: "):])
            except json.JSONDecodeError:
                continue
            rows.append({"question": pending_question, **evidence})
    if not rows:
        return {"status": "data_request", "reason": "no_audited_history",
                "detail": {"hint": "ask and execute the underlying data questions first"}}
    return {
        "status": "answer",
        "label": "mixed",
        "value": {"kind": "conversation_evidence", "rows": rows, "source":
                  "prior deterministic executions in this conversation",
                  "note": "dialogue synthesis only; no new connector fact or measurement"},
        "provenance": [{"op": "DIALOGUE", "route": "audited-history-ledger",
                        "output_rows": len(rows)}],
    }


def audited_history_entry(question: str, compiled: dict) -> dict:
    """Build compact code-owned dialogue memory without retaining responder prose.

    The deterministic summary is useful for retrieval, but alone it can erase distinctions such
    as survey encounter versus older record or local observation versus rejected transfer.  This
    bounded ledger preserves those declared fields while excluding raw connector traces and large
    regional inventories.
    """
    execution = compiled.get("execution") or {}
    value = execution.get("value") if isinstance(execution.get("value"), dict) else {}
    facts = {
        "kind": value.get("kind"),
        "source": value.get("source"),
        "grain": value.get("grain"),
        "note": value.get("note"),
    }
    named_records = []
    for row in (value.get("rows") or [])[:20]:
        if not isinstance(row, dict):
            continue
        name = row.get("common_name") or row.get("scientific_name") or row.get("finding")
        item = {"name": name} if name else {}
        for key in ("scientific_name", "record_status", "label", "group", "survey_dates",
                    "medically_venomous"):
            if row.get(key) is not None:
                item[key] = row[key]
        if item:
            named_records.append(item)
    if named_records:
        facts["named_records"] = named_records
    assessments = []
    for item in (value.get("assessments") or [])[:12]:
        if not isinstance(item, dict):
            continue
        assessment = {key: item.get(key) for key in
                      ("species", "locally_observed", "transfer_admissible")
                      if item.get(key) is not None}
        for source_key, target_key in (("feature_gate", "feature_gate"),
                                       ("climate_gate", "climate_gate")):
            gate = item.get(source_key)
            if isinstance(gate, dict):
                assessment[target_key] = {key: gate.get(key) for key in
                    ("pass", "strength", "reason", "target_analog_fraction",
                     "target_analog_fraction_threshold", "target_in_envelope_fraction",
                     "target_in_envelope_fraction_threshold") if gate.get(key) is not None}
        assessments.append(assessment)
    if assessments:
        facts["assessments"] = assessments
    for key in ("gate", "gate_contract", "assessment_counts", "admitted_transfer_candidates",
                "measurement_scopes", "relation", "threshold_km", "left_entity",
                "right_entity", "left_record_count", "right_record_count",
                "matched_left_count", "matched_right_count", "left_region", "right_region",
                "matched_left_fraction", "matched_right_fraction", "matched_left_percent",
                "matched_right_percent", "temporal_alignment", "donor_entity", "donor_region",
                "donor_record_count", "target_region"):
        if value.get(key) is not None:
            facts[key] = value[key]
    detail = execution.get("detail")
    if execution.get("status") != "answer" and isinstance(detail, dict):
        facts["data_request"] = {
            key: detail.get(key) for key in ("hint", "ask", "error") if detail.get(key)}
    facts = {key: val for key, val in facts.items() if val not in (None, [], {}, "")}
    return {
        "status": execution.get("status"),
        "label": execution.get("label"),
        "reason": execution.get("reason"),
        "summary": deterministic_render(question, compiled),
        "facts": facts,
    }


def _selected_examples(capabilities: list[dict]) -> list[dict]:
    """Turn retrieved capability metadata into last-mile algebra curriculum examples."""
    examples = []
    selected = [item for item in capabilities if item.get("selected")]
    selected_ops = {op for item in selected for op in item.get("ops", [])}
    region_support = next((item for item in selected if item.get("binding") == "region"), None)
    generic_data = any(item.get("binding") == "compiler_entity" for item in selected)
    if "RELATE" in selected_ops and generic_data:
        region = ({"op": "REGION", "place": region_support["place"]}
                  if region_support else "?search_region")
        examples.append({
            "q": "Across the selected search region, are Species Alpha and Species Beta occurrence records within 5 km?",
            "ir": {"op": "RELATE", "relation": "cooccur", "threshold_km": 5.0,
                   "left": {"op": "SELECT", "entity": "Species Alpha",
                            "region": region, "time": None},
                   "right": {"op": "SELECT", "entity": "Species Beta",
                             "region": region, "time": None}},
        })
    if {"RELATE", "BUFFER"} <= selected_ops and generic_data:
        buffered = {"op": "BUFFER", "radius_km": 25.0,
                    "source": {"op": "REGION", "place": "?place"}}
        examples.insert(0, {
            "q": "Search a 25 km buffer around here, then find Species Alpha records within 5 km of Species Beta records.",
            "ir": {"op": "RELATE", "relation": "within", "threshold_km": 5.0,
                   "left": {"op": "SELECT", "entity": "Species Alpha",
                            "region": buffered, "time": None},
                   "right": {"op": "SELECT", "entity": "Species Beta",
                             "region": buffered, "time": None}},
        })
    if "ESTIMATE" in selected_ops and generic_data:
        donor = ({"op": "REGION", "place": region_support["place"]}
                 if region_support else "?donor_region")
        examples.append({
            "q": "Estimate Species Alpha at the target from occurrence records in the selected donor region.",
            "ir": {"op": "ESTIMATE", "method": "feature",
                   "source": {"op": "SELECT", "entity": "Species Alpha",
                              "region": donor, "time": None},
                   "target": "?target_region"},
        })
    for item in capabilities:
        if not item.get("selected"):
            continue
        region = "?place"
        binding = item.get("binding")
        ops = item.get("ops") or []
        if binding == "operator" and "RELATE" in ops:
            ir = {"op": "RELATE", "relation": "cooccur", "threshold_km": 5.0,
                  "left": {"op": "SELECT", "entity": "?left_taxon",
                           "region": "?search_region", "time": None},
                  "right": {"op": "SELECT", "entity": "?right_taxon",
                            "region": "?search_region", "time": None}}
        elif binding == "operator" and "ESTIMATE" in ops:
            ir = {"op": "ESTIMATE", "method": "feature",
                  "source": {"op": "SELECT", "entity": "?taxon",
                             "region": "?donor_region", "time": None},
                  "target": "?target_region"}
        elif binding == "operator" and "BUFFER" in ops:
            ir = {"op": "SELECT", "entity": "?entity",
                  "region": {"op": "BUFFER", "radius_km": 25.0,
                             "source": {"op": "REGION", "place": "?place"}},
                  "time": None}
        elif binding == "region":
            ir = {"op": "SELECT", "entity": "?entity",
                  "region": {"op": "REGION", "place": item["place"]}, "time": None}
        elif str(item.get("kind", "SELECT")).startswith("ANNOTATE"):
            ir = {"op": "ANNOTATE", "layer": item["entity"],
                  "source": {"op": "SELECT", "entity": item["source_entity"],
                             "region": region, "time": None}}
        else:
            ir = {"op": "SELECT", "entity": item["entity"],
                  "region": region, "time": None}
        examples.append({
            "q": f"Selected capability `{item['entity']}`: compile it for this place.",
            "ir": ir,
        })
    return examples


def _bind_single_capability(draft: dict | None, capabilities: list[dict]) -> dict | None:
    """Bind an atomic declared dataset without destroying compiler-owned composition.

    Capability retrieval supplies ingredients. It never has authority to change a valid root
    operator. In particular, a RELATE/ESTIMATE/COMPARE tree must not collapse to whichever single
    catalog row looked most semantically similar to the question.
    """
    selected = [item for item in capabilities if item.get("selected")]
    if not isinstance(draft, dict):
        return draft
    root = draft.get("op")
    region_support = [item for item in selected if item.get("binding") == "region"
                      and item.get("place")]
    if len(region_support) == 1 and root in {"RELATE", "ESTIMATE"}:
        place = region_support[0]["place"]

        def bind_search_regions(node):
            if not isinstance(node, dict):
                return node
            out = {key: bind_search_regions(value) if isinstance(value, dict) else value
                   for key, value in node.items()}
            if out.get("op") == "SELECT":
                out["region"] = {"op": "REGION", "place": place}
            return out

        out = deepcopy(draft)
        if root == "ESTIMATE":
            out["source"] = bind_search_regions(out.get("source"))
        else:
            out = bind_search_regions(out)
        draft = out
    authorized_ops = {op for item in selected if item.get("binding") == "operator"
                      for op in item.get("ops", [])}
    if authorized_ops:
        def project_selected_operators(node):
            if not isinstance(node, dict):
                return node
            out = {key: (project_selected_operators(value) if isinstance(value, dict) else
                         [project_selected_operators(item) if isinstance(item, dict) else item
                          for item in value] if isinstance(value, list) else value)
                   for key, value in node.items()}
            op = out.get("op")
            if op in authorized_ops and op in ALLOWED_FIELDS:
                out = {key: value for key, value in out.items() if key in ALLOWED_FIELDS[op]}
            return out

        draft = project_selected_operators(draft)
    if root not in {"SELECT", "ANNOTATE"}:
        return draft
    if len(selected) != 1:
        return draft
    item = selected[0]
    if item.get("binding") in {"compiler_entity", "operator", "region"}:
        return draft
    time_value = None

    def find_time(node):
        nonlocal time_value
        if isinstance(node, dict):
            if node.get("op") == "SELECT" and node.get("time") is not None and time_value is None:
                time_value = node.get("time")
            for value in node.values():
                find_time(value)
        elif isinstance(node, list):
            for value in node:
                find_time(value)

    find_time(draft)
    source = {"op": "SELECT", "entity": item.get("source_entity") or item["entity"],
              "region": "?place", "time": time_value}
    if str(item.get("kind", "SELECT")).startswith("ANNOTATE"):
        return {"op": "ANNOTATE", "layer": item["entity"], "source": source}
    source["entity"] = item["entity"]
    return source


def compile_turn(question: str, compiler: str, history: list[dict], context: str = "ebtl",
                 observer: StageObserver | None = None) -> dict:
    """Compile with the selected model and execute with deterministic code."""
    started = time.time()
    compile_spec, _, critic = compiler.partition("+")
    selector, sep, base_compiler = compile_spec.partition("@")
    if not sep:
        base_compiler, selector = selector, ""
    capability_selector, verifier_sep, ir_verifier = selector.partition(">")
    capabilities = C.capability_catalog()
    raw_selector = None
    selector_events: list[str] = []
    dialogue_mode = "execute"
    if selector:
        capabilities, raw_selector, selector_events, dialogue_mode = _select_capabilities(
            question, selector, history, observer=observer
        )
    if dialogue_mode == "synthesize_history":
        execution = _history_synthesis_execution(history)
        _observe(observer, "execution_preview", ir=None,
                 schema={"valid": True, "errors": [], "holes": [], "ops": []},
                 dialogue_mode=dialogue_mode, selected_capabilities=[])
        _observe(observer, "execution_complete", execution=execution,
                 dialogue_mode=dialogue_mode)
        return {
            "compiler": compiler, "base_compiler": base_compiler, "selector": selector,
            "critic": critic or None, "dialogue_mode": dialogue_mode, "question": question,
            "ir": None, "raw_compiler": None, "raw_selector": raw_selector,
            "raw_critic": None, "parse_valid": True, "repair_events": selector_events,
            "schema": {"valid": True, "errors": [], "holes": [], "ops": []},
            "execution": execution,
            "compile_execute_latency_s": round(time.time() - started, 3),
        }
    if dialogue_mode == "clarify":
        choices = [item["entity"] for item in capabilities if item.get("selected")][:6]
        execution = {"status": "data_request", "reason": "ambiguous_request",
                     "detail": {"ask": "Which measurement should I use?",
                                "candidate_capabilities": choices}}
        _observe(observer, "execution_preview", ir=None,
                 schema={"valid": True, "errors": [], "holes": [], "ops": []},
                 dialogue_mode=dialogue_mode, selected_capabilities=capabilities)
        _observe(observer, "execution_complete", execution=execution,
                 dialogue_mode=dialogue_mode)
        return {
            "compiler": compiler, "base_compiler": base_compiler, "selector": selector,
            "critic": critic or None, "dialogue_mode": dialogue_mode, "question": question,
            "ir": None, "raw_compiler": None, "raw_selector": raw_selector,
            "raw_critic": None, "parse_valid": True, "repair_events": selector_events,
            "schema": {"valid": True, "errors": [], "holes": [], "ops": []},
            "execution": execution,
            "compile_execute_latency_s": round(time.time() - started, 3),
        }
    parsed = P.parse(
        question,
        role=base_compiler,
        fewshot=GENERIC_FEWSHOT + _selected_examples(capabilities),
        history=history,
        capabilities=capabilities,
        semantic_repairs=False,
    )
    raw_critic = None
    critic_events: list[str] = []
    draft_ir = parsed.get("ir")
    if selector and not [item for item in capabilities if item.get("selected")]:
        draft_ir = {"op": "SELECT", "entity": "?proxy", "region": "?place", "time": None}
        selector_events.append("capability_binding:empty_to_typed_hole")
    bound_ir = _bind_single_capability(draft_ir, capabilities) if selector else draft_ir
    if json.dumps(bound_ir, sort_keys=True) != json.dumps(draft_ir, sort_keys=True):
        selector_events.append("capability_binding:declared_contract_applied")
    draft_ir = bound_ir
    _observe(
        observer, "algebra_compiled", model=base_compiler,
        raw_output=parsed.get("raw"), ir=draft_ir,
        parser_events=parsed.get("events", []), selected_capabilities=capabilities,
    )
    if verifier_sep:
        draft_ir, raw_critic, verifier_events = _semantic_critic(
            question, draft_ir, ir_verifier, history, capabilities=capabilities
        )
        critic_events.extend("ir_verifier:" + event for event in verifier_events)
        rebound = _bind_single_capability(draft_ir, capabilities)
        if json.dumps(rebound, sort_keys=True) != json.dumps(draft_ir, sort_keys=True):
            selector_events.append("capability_binding:post_verifier_declared_contract")
        draft_ir = rebound
        _observe(
            observer, "algebra_verified", model=ir_verifier,
            raw_output=raw_critic, ir=draft_ir, events=verifier_events,
        )
    if critic:
        draft_ir, raw_critic, final_critic_events = _semantic_critic(
            question, draft_ir, critic, history, capabilities=capabilities
        )
        critic_events.extend(final_critic_events)
    ir = canonicalize(_bind_context(draft_ir, context))
    schema = validate(ir) if ir is not None else {
        "valid": False, "errors": ["no IR"], "holes": [], "ops": [], "unbound": True,
    }
    _observe(
        observer, "execution_preview", ir=ir,
        schema={"valid": schema["valid"], "errors": schema["errors"],
                "holes": [h.get("name") for h in schema.get("holes", [])],
                "ops": schema.get("ops", [])},
        dialogue_mode=dialogue_mode, selected_capabilities=capabilities,
    )
    if ir is None:
        execution = {"status": "error", "reason": "no_ir", "detail": {}}
    elif not schema["valid"]:
        execution = {"status": "data_request", "reason": "invalid_ir",
                     "detail": {"errors": schema["errors"]}}
    else:
        try:
            execution = execute(ir)
        except Exception as exc:  # benchmark trace, never turn a crash into prose
            execution = {"status": "error", "reason": "executor_crash",
                         "detail": {"error": f"{type(exc).__name__}: {str(exc)[:300]}"}}
    _observe(observer, "execution_complete", execution=execution,
             dialogue_mode=dialogue_mode)
    return {
        "compiler": compiler,
        "base_compiler": base_compiler,
        "selector": selector or None,
        "critic": critic or None,
        "dialogue_mode": dialogue_mode,
        "question": question,
        "ir": ir,
        "raw_compiler": parsed.get("raw"),
        "raw_selector": raw_selector,
        "raw_critic": raw_critic,
        "parse_valid": parsed.get("parse_valid", False),
        "repair_events": selector_events + parsed.get("events", []) + critic_events,
        "schema": {"valid": schema["valid"], "errors": schema["errors"],
                   "holes": [h.get("name") for h in schema.get("holes", [])],
                   "ops": schema.get("ops", [])},
        "execution": execution,
        "compile_execute_latency_s": round(time.time() - started, 3),
    }


def response_pack(compiled: dict) -> dict:
    """Bounded but loss-aware evidence view for the natural-language responder."""
    execution = deepcopy(compiled["execution"])
    value = execution.get("value")
    if isinstance(value, dict) and isinstance(value.get("rows"), list):
        rows = value["rows"]
        value["n_rows"] = len(rows)
        # Complete small inventories; bounded samples for large occurrence sets.
        value["rows"] = rows if len(rows) <= 30 else rows[:20]
        if len(rows) > 30:
            value["rows_truncated_for_response"] = len(rows) - 20
    pack = {
        "status": execution.get("status"),
        "evidence_label": execution.get("label"),
        "reason": execution.get("reason"),
        "detail": execution.get("detail"),
        "value": value,
        "provenance": execution.get("provenance", []),
    }
    # Upstream connector traces beneath a failed outer operation are diagnostic, not admissible
    # answer evidence. Hiding them prevents a responder from laundering a failed query into facts.
    if pack["status"] != "answer":
        pack["provenance"] = []
        if pack.get("reason") == "unbound_holes":
            pack["detail"] = {"ask": (
                "specify or collect the requested measure, place, time window, and survey effort")}
    return pack


def deterministic_render(question: str, compiled: dict) -> str:
    """Topic-neutral control renderer; intentionally plain but evidence-safe."""
    pack = response_pack(compiled)
    if pack["status"] != "answer":
        detail = pack.get("detail") or {}
        if pack.get("reason") == "ambiguous_request":
            choices = detail.get("candidate_capabilities") or []
            suffix = (" Options: " + "; ".join(str(choice) for choice in choices[:6]) + "."
                      if choices else "")
            return "That request could mean several different measurements. Which aspect do you want?" + suffix
        need = detail.get("hint") or detail.get("ask") or detail.get("error")
        if not need and detail.get("errors"):
            need = "; ".join(detail["errors"][:2])
        return ("I cannot answer this from the available evidence yet. "
                f"DATA REQUEST: {need or 'specify or collect the missing entity, place, measure, and survey effort.'}")
    value = pack.get("value") or {}
    label = pack.get("evidence_label") or value.get("label") or "observed"
    source = value.get("source") or "the executed connector"
    if value.get("kind") == "scalar":
        finding = str(value.get("value"))
        if value.get("unit"):
            finding += " " + str(value["unit"])
    elif value.get("grain") == "occurrence-proximity-relation":
        threshold = value.get("threshold_km")
        distance = f" within {threshold:g} km" if isinstance(threshold, (int, float)) else ""
        left_name = re.sub(r"\s+(?:occurrence\s+)?records?$", "",
                           str(value.get("left_entity") or "left"), flags=re.I)
        right_name = re.sub(r"\s+(?:occurrence\s+)?records?$", "",
                            str(value.get("right_entity") or "right"), flags=re.I)
        left_percent = value.get("matched_left_percent")
        right_percent = value.get("matched_right_percent")
        left_pct = (f" ({left_percent}%)" if isinstance(left_percent, (int, float)) else "")
        right_pct = (f" ({right_percent}%)" if isinstance(right_percent, (int, float)) else "")
        finding = (f"{value.get('matched_left_count', 0)} of "
                   f"{value.get('left_record_count', 0)} {left_name} "
                   f"records{left_pct} "
                   f"had at least one of "
                   f"{value.get('right_record_count', 0)} "
                   f"{right_name} records{distance}; "
                   f"{value.get('matched_right_count', 0)} of those right-side records{right_pct} had a "
                   "left-side neighbour at the same threshold")
        supports = [value.get("left_region"), value.get("right_region")]
        if any(isinstance(item, dict) and item.get("method") == "bbox-approx"
               for item in supports):
            finding += "; the search support is an approximate bbox, not an exact radius polygon"
    elif value.get("kind") == "field" and value.get("measure_field"):
        field = value["measure_field"]
        measured = [row.get(field) for row in value.get("rows") or []
                    if isinstance(row.get(field), (int, float))]
        if measured and value.get("grain") == "target-bbox-suitability-fraction":
            finding = (f"{measured[0]} of target analysis cells were classified suitable by "
                       f"the model; this fraction is not a calibrated occurrence probability")
        else:
            finding = (f"{field}={measured[0]} {value.get('unit') or ''}".rstrip()
                       if measured else f"{len(value.get('rows') or [])} model output records")
        gate = value.get("gate") if isinstance(value.get("gate"), dict) else {}
        if gate:
            finding += (f"; gate pass={gate.get('pass')} ({gate.get('strength')}: "
                        f"{gate.get('reason')})")
    elif value.get("kind") in {"records", "field"}:
        finding = f"{value.get('n_rows', len(value.get('rows') or []))} evidence records"
        sample = value.get("rows") or []
        names = []
        for row in sample:
            name = row.get("common_name") or row.get("scientific_name") or row.get("finding")
            if name and name not in names:
                row_label = row.get("label")
                names.append((f"[{row_label}] " if row_label else "") + str(name))
        if names:
            finding += ": " + ", ".join(names[:8])
    elif value.get("kind") == "series":
        finding = f"{len(value.get('rows') or [])} time points"
    elif value.get("kind") == "ranking":
        finding = " > ".join(str(row.get("label")) for row in value.get("rows") or [])
    else:
        finding = str(value.get("value") if value.get("value") is not None else value.get("kind"))
    notes = [p.get("note") for p in pack.get("provenance") or [] if p.get("note")]
    limitation = notes[-1] if notes else value.get("note")
    row_labels = {row.get("label") for row in (value.get("rows") or [])
                  if isinstance(row, dict) and row.get("label")}
    heading = "Mixed-evidence" if len(row_labels) > 1 else label.capitalize()
    text = f"{heading} result: {finding}. Source: {source}."
    if limitation:
        text += " " + str(limitation).rstrip(".") + "."
    return text


def _conversation_constraints(pack: dict) -> dict:
    """Extract compact semantic invariants from an audited conversation ledger."""
    value = pack.get("value") if isinstance(pack.get("value"), dict) else {}
    if value.get("kind") != "conversation_evidence":
        return {}
    constraints = {"locally_observed": [], "not_transfer_admissible": [],
                   "admitted_transfer_candidates": [], "labelled_summaries": [],
                   "data_requests": []}
    for row in value.get("rows") or []:
        if not isinstance(row, dict):
            continue
        summary = {"question": row.get("question"), "status": row.get("status"),
                   "label": row.get("label"), "summary": row.get("summary")}
        constraints["labelled_summaries"].append(summary)
        if row.get("status") != "answer":
            constraints["data_requests"].append(summary)
        facts = row.get("facts") if isinstance(row.get("facts"), dict) else {}
        for assessment in facts.get("assessments") or []:
            if not isinstance(assessment, dict) or not assessment.get("species"):
                continue
            species = assessment["species"]
            if assessment.get("locally_observed") is True:
                constraints["locally_observed"].append(species)
            if assessment.get("transfer_admissible") is False:
                constraints["not_transfer_admissible"].append(species)
        constraints["admitted_transfer_candidates"].extend(
            facts.get("admitted_transfer_candidates") or [])
    for key in ("locally_observed", "not_transfer_admissible",
                "admitted_transfer_candidates"):
        constraints[key] = list(dict.fromkeys(constraints[key]))
    return constraints


def _history_boundary_ok(pack: dict, answer: str) -> bool:
    """Reject explicit local-observation/transfer contradictions in ledger summaries."""
    constraints = _conversation_constraints(pack)
    if not constraints:
        return True
    sentences = re.split(r"(?<=[.!?])\s+", answer)
    for species in constraints["locally_observed"]:
        short_name = " ".join(str(species).split()[:2]).lower()
        for sentence in sentences:
            lowered = sentence.lower()
            if short_name not in lowered:
                continue
            presents_as_transfer = bool(re.search(
                r"pass(?:es|ed)?[^.!?]{0,70}\bfor transfer\b|"
                r"\b(?:admitted|admissible) transfer\b|\btransfer candidate\b", lowered))
            preserves_boundary = bool(re.search(
                r"\b(?:not|never|already|rather than|remains? observed|locally observed|"
                r"not regional|non-transfer)", lowered))
            presents_as_nonlocal = bool(re.search(
                r"\bregional\b|\bmodel(?:led|ed|s)?\b", lowered))
            if (presents_as_transfer or presents_as_nonlocal) and not preserves_boundary:
                return False
    return True


def _repair_history_boundary(pack: dict, answer: str) -> str:
    """Replace only sentences that contradict code-owned transfer disposition fields."""
    constraints = _conversation_constraints(pack)
    if not constraints or _history_boundary_ok(pack, answer):
        return answer
    repaired = []
    for sentence in re.split(r"(?<=[.!?])\s+", answer):
        offending = []
        lowered = sentence.lower()
        for species in constraints["locally_observed"]:
            short_name = " ".join(str(species).split()[:2])
            if (short_name.lower() in lowered and
                    re.search(r"pass(?:es|ed)?[^.!?]{0,70}\bfor transfer\b|"
                              r"\b(?:admitted|admissible) transfer\b|"
                              r"\btransfer candidate\b|\bregional\b|"
                              r"\bmodel(?:led|ed|s)?\b", lowered) and
                    not re.search(r"\b(?:not|never|already|rather than|remains? observed|"
                                  r"locally observed|not regional|non-transfer)", lowered)):
                offending.append(short_name)
        if not offending:
            repaired.append(sentence)
            continue
        repaired.extend(
            f"{name} is locally observed and remains an observation, not a transfer candidate."
            for name in offending)
        admitted = constraints["admitted_transfer_candidates"]
        if admitted:
            repaired.append("The transfer audit admitted only: " + ", ".join(admitted) + ".")
        else:
            repaired.append("The environmental-gate audit admitted no regional transfer candidate.")
    return " ".join(item.strip() for item in repaired if item.strip())


def _threshold_boundary_ok(pack: dict, answer: str) -> bool:
    """Ensure threshold language uses declared threshold fields, not observed values."""
    thresholds = []

    def walk(node):
        if isinstance(node, dict):
            for key, value in node.items():
                if key.endswith("_threshold") and isinstance(value, (int, float)):
                    thresholds.append((key[:-len("_threshold")], value))
                walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(pack)
    if not thresholds:
        return True
    for sentence in re.split(r"(?<=[.!?])\s+", answer):
        normalized = sentence.lower().replace("_", " ")
        if not re.search(r"\b(?:requir(?:e|es|ed|ing)|threshold|at least|minimum)\b", normalized):
            continue
        for field, threshold in thresholds:
            if field.lower().replace("_", " ") not in normalized:
                continue
            expected = str(threshold)
            if expected not in normalized:
                return False
    return True


def _absence_boundary_ok(answer: str) -> bool:
    """Permit cautions about absence while rejecting claims that a survey can establish it."""
    claim = re.compile(
        r"\b(?:confirm|prove|establish|rule out)\b[^.!?]{0,45}\babsence\b|"
        r"\b(?:confirm or rule out|rule out)\b[^.!?]{0,30}\bpresence\b", re.I)
    negated = re.compile(
        r"\b(?:cannot|can't|can’t|does not|doesn't|doesn’t|do not|don't|don’t|never)\b"
        r"[^.!?]{0,18}\b(?:confirm|prove|establish|rule out)\b", re.I)
    for sentence in re.split(r"(?<=[.!?])\s+", answer):
        if claim.search(sentence) and not negated.search(sentence):
            return False
    return True


def _count_grain_ok(pack: dict, answer: str) -> bool:
    """Reject explicit conversion of occurrence-record counts into named-taxon counts."""
    inventories = []

    def walk(node):
        if isinstance(node, dict):
            records = node.get("deduplicated_records", node.get("returned_record_count"))
            named = node.get("named_taxa_count")
            if named is None and isinstance(node.get("named_species"), list):
                named = len(node["named_species"])
            if isinstance(records, int) and isinstance(named, int) and records != named:
                inventories.append((records, named))
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(pack)
    for records, named in inventories:
        if re.search(rf"\b{records}\b[^\d.!?]{{0,35}}\bnamed\s+(?:species|taxa)\b", answer, re.I):
            return False
        if re.search(rf"\b{named}\b[^\d.!?]{{0,35}}\b(?:occurrence\s+)?records\b", answer, re.I):
            return False
    return True


def _interaction_boundary_ok(pack: dict, answer: str) -> bool:
    """Fail closed when an unknown local interaction is stated as ecologically impossible."""
    unsupported = False
    relation_proxy = False

    def walk(node):
        nonlocal unsupported, relation_proxy
        if isinstance(node, dict):
            if node.get("local_interaction_admissible") is False:
                unsupported = True
            if node.get("grain") == "occurrence-proximity-relation":
                relation_proxy = True
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(pack)
    if unsupported and re.search(
            r"\b(?:cannot|can't|can’t|could not|couldn't|couldn’t)\b[^.!?]{0,55}"
            r"\b(?:interact|feed|disperse|act as|occur)\b", answer, re.I):
        return False
    if relation_proxy:
        for sentence in re.split(r"(?<=[.!?])\s+", answer):
            if not re.search(
                    r"\b(?:interact\w*|feed\w*|dispers\w*|avoid\w*|prefer\w*|same[- ]time|simultaneous|"
                    r"together|associated?)\b", sentence, re.I):
                continue
            if not re.search(
                    r"\b(?:not|cannot|can't|can’t|does not|doesn't|doesn’t|unknown|"
                    r"unsupported|no temporal|not established)\b", sentence, re.I):
                return False
    return True


def _suitability_boundary_ok(pack: dict, answer: str) -> bool:
    """Keep a classified-cell fraction from becoming occurrence probability or prevalence."""
    has_suitability_fraction = False

    def walk(node):
        nonlocal has_suitability_fraction
        if isinstance(node, dict):
            if (node.get("grain") == "target-bbox-suitability-fraction" or
                    node.get("measure_field") == "suitability_fraction"):
                has_suitability_fraction = True
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(pack)
    if not has_suitability_fraction:
        return True
    for sentence in re.split(r"(?<=[.!?])\s+", answer):
        lowered = sentence.lower()
        if not re.search(r"\b(?:suitab\w*|fraction|model(?:led|ed)?|score)\b", lowered):
            continue
        # A caution may name these interpretations in order to reject them.
        rejects_inference = bool(re.search(
            r"\b(?:not|isn't|isn’t|cannot|can't|can’t|does not|doesn't|doesn’t|"
            r"should not|must not|no calibrated)\b", lowered))
        if re.search(
                r"\b(?:low|high|minimal|severe)\b[^.!?]{0,70}"
                r"\b(?:presence|occurrence|occupancy|abundance|prevalence|likelihood|probability|chance)\b|"
                r"\b(?:limited|likely|unlikely|widespread|rare|abundant)\b[^.!?]{0,55}"
                r"\b(?:presence|occurrence|occupancy|abundance|prevalence)\b|"
                r"\b(?:probability|likelihood|chance)\s+of\s+(?:presence|occurrence)\b",
                lowered) and not rejects_inference:
            return False
        if re.search(r"\b(?:proves?|confirms?|establishes?)\b[^.!?]{0,60}"
                     r"\b(?:presence|occurrence|occupancy|abundance)\b", lowered) and not rejects_inference:
            return False
    return True


def _approximate_support_boundary_ok(pack: dict, answer: str) -> bool:
    """An approximate bbox construction must remain visible on the answer surface."""
    approximate = False

    def walk(node):
        nonlocal approximate
        if isinstance(node, dict):
            if node.get("method") == "bbox-approx":
                approximate = True
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(pack)
    if not approximate:
        return True
    return (bool(re.search(r"\bapproximat\w*\b", answer, re.I)) and
            bool(re.search(r"\b(?:bbox|bounding box|search (?:area|extent|support))\b",
                           answer, re.I)) and
            not bool(re.search(r"\b(?:exact|surveyed|property)\s+(?:polygon|boundary|area)\b",
                               answer, re.I)))


def audit_response(question: str, compiled: dict, answer: str,
                   history: list[dict] | None = None) -> dict:
    pack = response_pack(compiled)
    packed = json.dumps(pack, ensure_ascii=False, default=str)
    allowed_text = question + " " + packed + " " + json.dumps(history or [], ensure_ascii=False)
    def fact_numbers(text):
        # List ordinals are formatting, not factual quantities. Removing them prevents a requested
        # three-item brief from failing because it is formatted as (1), (2), (3).
        text = re.sub(r"\(\d{1,2}\)(?=\s)", "", text)
        text = re.sub(r"(?m)^\s*\d{1,2}[.)]\s+", "", text)
        return set(re.findall(r"(?<![A-Za-z])\d+(?:\.\d+)?", text))

    stated_numbers = fact_numbers(answer)
    allowed_numbers = fact_numbers(allowed_text)
    label = pack.get("evidence_label") or ((pack.get("value") or {}).get("label"))
    checks = {
        "nonempty": bool(answer.strip()),
        "no_new_numbers": stated_numbers <= allowed_numbers,
        "no_internal_leak": not re.search(
            r"(?<!\.)\bjson\b|\btyped_evaluate\b|\bexpression tree\b|\bunbound(?:_holes)?\b|\"op\"",
            answer, re.I),
        "no_chat_envelope": not re.search(
            r'\{\s*"role"\s*:|"content"\s*:|CURRENT AUDITED RESULT', answer, re.I),
        "no_plan_narration": not re.search(
            r"(?:^|\n\s*\n)(?:The user (?:is asking|wants)|Let me |I (?:need|should) |"
            r"I(?:'ll| will) (?:answer|present|organize|summarize))",
            answer, re.I),
        "no_typed_holes": not re.search(r"\?(?:proxy|place|indicator|entity|time)\b", answer, re.I),
        "length": 4 <= len(answer.split()) <= (
            320 if compiled.get("dialogue_mode") == "synthesize_history" else 230),
        "proxy_label": label != "proxy" or bool(re.search(r"\bproxy\b", answer, re.I)),
        "modelled_label": label != "modelled" or bool(re.search(
            r"\b(?:modelled|modeled|estimate|transfer)\b", answer, re.I)),
        "data_gap": pack.get("status") == "answer" or bool(re.search(
            r"\b(?:unknown|cannot|can't|can’t|missing|need|data request|collect|measure)\b",
            answer, re.I)),
        "history_boundary": _history_boundary_ok(pack, answer),
        "absence_boundary": _absence_boundary_ok(answer),
        "threshold_boundary": _threshold_boundary_ok(pack, answer),
        "count_grain": _count_grain_ok(pack, answer),
        "interaction_boundary": _interaction_boundary_ok(pack, answer),
        "suitability_boundary": _suitability_boundary_ok(pack, answer),
        "approximate_support_boundary": _approximate_support_boundary_ok(pack, answer),
    }
    checks["passed"] = all(checks.values())
    checks["new_numbers"] = sorted(stated_numbers - allowed_numbers)
    return checks


def render_turn(question: str, compiled: dict, responder: str,
                history: list[dict], observer: StageObserver | None = None) -> dict:
    started = time.time()
    pack = response_pack(compiled)
    _observe(observer, "response_preview", model=responder, evidence_pack=pack)
    if responder == "deterministic":
        answer = deterministic_render(question, compiled)
        rendered = {"responder": responder, "answer": answer,
                    "audit": audit_response(question, compiled, answer, history),
                    "responder_attempts": 0, "fallback": False,
                    "render_latency_s": round(time.time() - started, 3)}
        _observe(observer, "response_complete", **rendered)
        return rendered

    compact_history = history[-6:]
    messages = [
        {"role": "system", "content": RESPONDER_SYSTEM},
        {"role": "user", "content": (
            "Conversation context:\n" + json.dumps(compact_history, ensure_ascii=False) +
            "\n\nCURRENT QUESTION:\n" + question +
            "\n\nCURRENT AUDITED RESULT:\n" +
            json.dumps(pack, ensure_ascii=False, default=str)
        )},
    ]
    attempts = 0
    raw = ""
    answer = ""
    audit = {}
    semantic_critic = None
    semantic_critic_raw = None
    attempt_range = (1,) if responder == "lora9b" else (1, 2)
    for attempts in attempt_range:
        try:
            raw = chat(responder, messages, temperature=0.0,
                       max_tokens=(320 if responder == "lora9b" else 800), use_cache=True)
        except RuntimeError as exc:
            raw = f"[llm-error] {exc}"
            audit = {"passed": False, "responder_available": False, "new_numbers": []}
            break
        answer = sanitize_user_answer(strip_reasoning(raw))
        audit = audit_response(question, compiled, answer, history)
        if audit["passed"]:
            break
        messages.extend([
            {"role": "assistant", "content": answer},
            {"role": "user", "content": (
                "That answer failed the mechanical evidence audit: " +
                ", ".join(k for k, ok in audit.items()
                          if k not in {"passed", "new_numbers"} and not ok) +
                (f"; unsupported numbers={audit['new_numbers']}" if audit["new_numbers"] else "") +
                ". Rewrite the answer using only the audited result. Output only the answer."
            )},
        ])
    value = pack.get("value") if isinstance(pack.get("value"), dict) else {}
    # Multi-turn summaries compound many evidence classes and are the highest-risk synthesis step.
    # Give them one independent semantic audit against the code-owned ledger. This role may rewrite
    # prose, but it cannot change execution, admit a connector, or add evidence.
    if (pack.get("status") == "answer" and value.get("kind") == "conversation_evidence"
            and answer):
        critic_chain = os.environ.get("DSS_TYPED_RESPONSE_CRITIC", "qwen9b").split(">")
        constraints = _conversation_constraints(pack)
        critic_prompt = (
            "Audit and rewrite a conservation field brief against its CODE-OWNED EVIDENCE LEDGER. "
            "Output ONLY the corrected brief, with no audit commentary. Preserve each ledger row's "
            "label, spatial grain, record_status, locally_observed and transfer_admissible values. "
            "A locally observed item is never regional-only or an admitted transfer. A failed gate "
            "never becomes a site expectation. A proxy is not modelled or observed ground truth. "
            "Do not attach property acreage to an analysis bbox or point buffer. Keep exactly the "
            "number of priorities requested, and match every collection to a documented decision "
            "gap. Use no fact, species or measurement absent from the ledger or user question. "
            "The NON-NEGOTIABLE CONSTRAINTS below are code-extracted: never contradict them.\n\n"
            "QUESTION:\n" + question + "\n\nEVIDENCE LEDGER:\n" +
            json.dumps(constraints, ensure_ascii=False, default=str) +
            "\n\nDRAFT:\n" + answer)
        for critic_model in critic_chain:
            semantic_critic = critic_model.strip()
            if not semantic_critic:
                continue
            try:
                semantic_critic_raw = chat(
                    semantic_critic, [{"role": "user", "content": critic_prompt}],
                    temperature=0.0,
                    max_tokens=(5000 if semantic_critic == "deepseekv4" else 1600),
                    use_cache=True, timeout=150, retries=2)
                candidate = _repair_history_boundary(
                    pack, sanitize_user_answer(strip_reasoning(semantic_critic_raw)))
                candidate_audit = audit_response(question, compiled, candidate, history)
                if candidate_audit.get("passed"):
                    answer, audit = candidate, candidate_audit
                    break
            except RuntimeError:
                continue
        if not audit.get("history_boundary", True):
            candidate = _repair_history_boundary(pack, answer)
            candidate_audit = audit_response(question, compiled, candidate, history)
            if candidate_audit.get("passed"):
                answer, audit = candidate, candidate_audit
    fallback = not audit.get("passed", False)
    if fallback:
        answer = deterministic_render(question, compiled)
        audit = audit_response(question, compiled, answer, history)
    rendered = {"responder": responder, "answer": answer, "raw_responder": raw,
                "audit": audit, "responder_attempts": attempts, "fallback": fallback,
                "semantic_critic": semantic_critic,
                "semantic_critic_raw": semantic_critic_raw,
                "render_latency_s": round(time.time() - started, 3)}
    _observe(observer, "response_complete", **rendered)
    return rendered
