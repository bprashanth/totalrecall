#!/usr/bin/env python3
"""verify_numbers — the S3 numeric-honesty rail for prose answers.

verify(answer, question, history_numbers) -> {"verdicts": [...], "violations": [...]}
Verdict per extracted number: verbatim | derived(a op b, recorded) | contextual |
tagged-estimate | YEAR | request-exempt | UNVERIFIED. Any UNVERIFIED = repair trigger.
Boundary (documented, not hidden): cannot catch right-number-wrong-claim, wrong-place
attribution, or numberless narrative fabrication — those remain judge territory.
"""
import itertools, json, os, re, sys

HB = os.path.dirname(os.path.abspath(__file__))
_num = re.compile(r"\d[\d,]*\.?\d*")
EST = re.compile(r"\(estimate|estimate[d\s—-]*basis|roughly \(est", re.I)
REQ = re.compile(r"data request|collect|survey|sample|if you can get", re.I)
YEAR = re.compile(r"^(19|20)\d\d$")

def _norm(tok):
    return tok.replace(",", "").rstrip(".")

def pack_numbers():
    nums, by_file = set(), {}
    for f in sorted(os.listdir(os.path.join(HB, "data"))):
        if f.endswith((".json", ".md")):
            toks = {_norm(m.group(0)) for m in _num.finditer(open(os.path.join(HB, "data", f)).read())}
            nums |= toks
            vals = set()
            for n in toks:
                try:
                    vals.add(float(n))
                except ValueError:
                    pass
            by_file[f] = vals
    return nums, by_file

PACK_STR, PACK_BY_FILE = pack_numbers()
_DERIV = None

def _derivations():
    global _DERIV
    if _DERIV is None:
        _DERIV = []
        # bases: material same-dataset numbers only (cross-file arithmetic is meaningless)
        for fn, fv in PACK_BY_FILE.items():
            vs = [v for v in fv if v >= 100 and not YEAR.fullmatch(f"{v:g}")]
            for a, b in itertools.permutations(vs, 2):
                if a < b:  # share-of-whole percentage
                    _DERIV.append((a / b * 100, f"{a:g}/{b:g}*100 [{fn}]"))
                if a > b and a / b < 10:  # difference between comparable magnitudes
                    _DERIV.append((a - b, f"{a:g}-{b:g} [{fn}]"))
    return _DERIV

def _round_to_claim(val, claim_tok):
    if "." in claim_tok:
        return round(val, len(claim_tok.split(".")[1]))
    # integer claim from a non-integer derivation must be exact, not rounded
    return val if abs(val - round(val)) < 1e-9 else None

def _derived(x, claim_tok=""):
    for val, expl in _derivations():
        if _round_to_claim(val, claim_tok or f"{x:g}") == x:
            return expl
    return None

def verify(answer, question="", history_numbers=()):
    ctx = {_norm(m.group(0)) for m in _num.finditer(question)} | set(history_numbers)
    verdicts, violations = [], []
    for sent in re.split(r"(?<=[.!?])\s+", answer):
        est = bool(EST.search(sent))
        req = bool(REQ.search(sent))
        for m in _num.finditer(sent):
            tok = _norm(m.group(0))
            if YEAR.fullmatch(tok):
                verdicts.append((tok, "year")); continue
            if tok in PACK_STR:
                verdicts.append((tok, "verbatim")); continue
            if tok in ctx:
                verdicts.append((tok, "contextual")); continue
            if est:
                verdicts.append((tok, "tagged-estimate")); continue
            if req:
                verdicts.append((tok, "request-exempt")); continue
            try:
                d = _derived(float(tok), tok)
            except ValueError:
                d = None
            if d:
                verdicts.append((tok, f"derived({d})")); continue
            verdicts.append((tok, "UNVERIFIED"))
            violations.append({"number": tok, "sentence": sent.strip()[:200]})
    return {"verdicts": verdicts, "violations": violations}

if __name__ == "__main__":
    # self-test on known cases from the bench transcripts
    cases = [
        ("verbatim", "MGNREGA employed 80,321 households of 185,051 registered (DRDA FY25-26).", 0),
        ("derived-pct", "That is about 43% scheme utilization (DRDA FY25-26).", 0),
        ("derived-share", "Cultivators are 14.9% of workers (Census 2011).", 0),
        ("fabricated", "The MGNREGS table shows 1,247 households received work.", 1),
        ("estimate-ok", "Maybe 30-40 households grow turmeric primarily (estimate — basis: share of cultivators near the APMC).", 0),
        ("request-ok", "DATA REQUEST: survey 200-300 dyeing workers across two clusters.", 0),
        ("mixed", "Wages are Rs 336/day (DRDA) but dyeing units pay Rs 512 daily.", 1),
    ]
    ok = True
    for name, text, want in cases:
        r = verify(text)
        good = len(r["violations"]) == want
        ok &= good
        print(("PASS" if good else "FAIL"), name, "->",
              [v for v in r["verdicts"]], r["violations"] if r["violations"] else "")
    print("ALL", "PASS" if ok else "FAIL")
