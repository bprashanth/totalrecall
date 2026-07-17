#!/usr/bin/env python3
"""Erode drilldown driver. One arm per invocation:
  python3 run_bench.py --arm A-2B|A-9B|A-DS [--round v1] [--turns 14]
Reads persona/arc.md turn goals, phrases each follow-up in Meena's voice via deepseekv4
(OpenRouter, grinder role), sends it to hermes-live via docker exec with the arm's
provider, appends everything to transcripts/<round>/<arm>.md. Resumable: skips turns
already present in the transcript file."""
import argparse, json, os, re, subprocess, sys, time, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ARMS = {"A-2B": ("loravb", "loravb"), "A-9B": ("lora9b", "lora9b"),
        "A-2B-ctx": ("loravb", "loravb"), "A-9B-ctx": ("lora9b", "lora9b"),
        "A-9B3-ctx": ("lora9b003", "lora9b003"),
        "A-9B3-ctx-s3": ("lora9b003", "lora9b003"),
        "A-DS": ("deepseek/deepseek-v4-flash", "dsv4")}
DIGEST = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "persona", "digest.txt")).read()
OR_KEY = os.environ.get("OPENROUTER_API_KEY") or subprocess.run(
    ["docker", "exec", "hermes-live", "sh", "-c", "printenv OPENROUTER_API_KEY"],
    capture_output=True, text=True).stdout.strip()

ARC = []  # (goal line) parsed from persona/arc.md
for ln in open(os.path.join(HERE, "persona", "arc.md")):
    m = re.match(r"^(\d+)\. ([A-Z].*)", ln.strip())
    if m:
        ARC.append(m.group(2))

TURN1 = ("I want you to help me understand my own district for NGO work. First read "
         "/opt/data/livelihoods_erode/PLAYBOOK.md and follow it for this whole conversation. "
         "Use the edata tool there for real numbers. Now: tell me about Erode — I'm from "
         "there, but tell me like I'm mapping it for livelihoods work.")

def phrase(goal, prev_answer):
    content = ("You are Meena, 34, NGO program associate from Erode (Indian English, terse, "
               "warm). The assistant just said:\n---\n" + prev_answer[-600:] + "\n---\n"
               "Write ONLY your next chat message (1-2 sentences): first react to something "
               "concrete it said (agree/doubt/pick at it), then ask about: " + goal +
               "\nDo not add quotes or labels.")
    body = {"model": "deepseek/deepseek-v4-flash", "max_tokens": 900, "temperature": 0.7,
            "messages": [{"role": "user", "content": content}]}
    req = urllib.request.Request("https://openrouter.ai/api/v1/chat/completions",
                                 json.dumps(body).encode(),
                                 {"Content-Type": "application/json",
                                  "Authorization": "Bearer " + OR_KEY})
    for _ in range(3):
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.load(r)["choices"][0]["message"]["content"].strip()
        except Exception as e:
            time.sleep(5); err = e
    raise SystemExit(f"phraser failed: {err}")

def pack_text():
    import subprocess as sp
    return sp.run(["docker", "exec", "hermes-live", "sh", "-c",
                   "for f in /opt/data/livelihoods_erode/*.json; do echo \"=== $f\"; cat $f; done; echo '=== GAPS.md'; cat /opt/data/livelihoods_erode/GAPS.md"],
                  capture_output=True, text=True).stdout

CTX_PREAMBLE = ("I want you to help me understand my district for NGO work. Below is our ENTIRE "
    "verified data pack about Erode livelihoods. Rules for the whole conversation: real numbers "
    "ONLY from this pack, each with its source label in-line; anything not in the pack is either "
    "a labeled estimate (state your one-line basis) or unknown — and when it matters, tell me "
    "exactly what data to collect (a DATA REQUEST). Never invent a number. Talk like a "
    "knowledgeable local colleague, 1-3 short paragraphs.\n\n--- DATA PACK START\n%s\n--- DATA "
    "PACK END\n\nNow: tell me about Erode — I'm from there, but tell me like I'm mapping it "
    "for livelihoods work.")

def ask_hermes(text, session, model, provider, toolset="terminal,file,code_execution,clarify", home="/opt/data/bench_home"):
    cmd = ["docker", "exec", "hermes-live", "sh", "-c",
           (f"cd {home} && HOME={home} HERMES_HOME={home} timeout 1800 hermes -z ") + json.dumps(text) +
           f" -m {json.dumps(model)} --provider {provider} -t {toolset} --continue {session} 2>/dev/null"]
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=1860)
    return (p.stdout or "").strip() or "[NO OUTPUT — hermes error: " + (p.stderr or "")[-300:] + "]"

def s3_pass(ans, q, history_nums):
    sys.path.insert(0, HERE)
    from verify_numbers import verify, _num, _norm
    v = verify(ans, q, history_nums)
    if not v["violations"]:
        return ans, "s3:clean"
    viol = "; ".join(f"'{x['number']}' in \"{x['sentence']}\"" for x in v["violations"][:6])
    fix = phrase_raw(
        "Rewrite the answer below changing NOTHING except the flagged unverifiable numbers — "
        "for each one either replace it with the correct number from the DATA PACK context, "
        "tag it as (estimate — basis: ...), or delete its sentence. Flagged: " + viol +
        "\n\nANSWER:\n" + ans)
    v2 = verify(fix, q, history_nums)
    if not v2["violations"]:
        return fix, f"s3:repaired({len(v['violations'])})"
    # fail closed: strip still-violating sentences
    bad = {x["sentence"][:60] for x in v2["violations"]}
    kept = [sn for sn in re.split(r"(?<=[.!?])\s+", fix) if sn.strip()[:60] not in bad]
    return " ".join(kept) + "\n\n(Some unverifiable figures were removed by the honesty check.)", \
           f"s3:stripped({len(v2['violations'])})"

def phrase_raw(content):
    body = {"model": "deepseek/deepseek-v4-flash", "max_tokens": 1500, "temperature": 0.2,
            "messages": [{"role": "user", "content": content}]}
    req = urllib.request.Request("https://openrouter.ai/api/v1/chat/completions",
                                 json.dumps(body).encode(),
                                 {"Content-Type": "application/json",
                                  "Authorization": "Bearer " + OR_KEY})
    for _ in range(3):
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                c = json.load(r)["choices"][0]["message"]["content"]
                if c:
                    return c.strip()
        except Exception:
            time.sleep(5)
    return content  # repair unavailable -> keep original (will be stripped)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", required=True, choices=list(ARMS))
    ap.add_argument("--round", default="v1")
    ap.add_argument("--turns", type=int, default=14)
    a = ap.parse_args()
    model, provider = ARMS[a.arm]
    is_ctx = "-ctx" in a.arm
    is_s3 = a.arm.endswith("-s3")
    outdir = os.path.join(HERE, "transcripts", a.round)
    os.makedirs(outdir, exist_ok=True)
    path = os.path.join(outdir, a.arm + ".md")
    done = 0
    if os.path.exists(path):
        done = len(re.findall(r"^## Turn ", open(path).read(), re.M))
    session = f"erode_{a.round}_{a.arm.replace('-', '').lower()}"
    prev = ""
    if done:
        prev = open(path).read().split("### Hermes\n")[-1]
    with open(path, "a") as f:
        if not done:
            f.write(f"# Erode drilldown — {a.arm} — round {a.round}\n"
                    f"session={session} model={model} provider={provider} "
                    f"started={time.strftime('%F %T')}\n\n")
        for i in range(done, min(a.turns, len(ARC))):
            q = (CTX_PREAMBLE % pack_text() if is_ctx else TURN1) if i == 0 else phrase(ARC[i], prev)
            if is_ctx and i > 0:
                q = q + "\n\n[" + DIGEST + "]"
            t0 = time.time()
            ans = ask_hermes(q, session, model, provider,
                             toolset="clarify" if is_ctx else "terminal,file,code_execution,clarify",
                             home="/opt/data/bench_home_ctx" if is_ctx else "/opt/data/bench_home")
            s3_note = ""
            if is_s3:
                hist = set()
                ans, s3_note = s3_pass(ans, q, hist)
                s3_note = f" _[{s3_note}]_"
            f.write(f"## Turn {i+1} — {ARC[i][:60]}\n### Meena\n{q}\n\n"
                    f"### Hermes\n{ans}\n\n_(latency {time.time()-t0:.0f}s)_" +
                    (s3_note if is_s3 else "") + "\n\n")
            f.flush()
            prev = ans
            print(f"[{a.arm}] turn {i+1}/{a.turns} done ({time.time()-t0:.0f}s)", flush=True)
    print(f"[{a.arm}] transcript -> {path}", flush=True)

if __name__ == "__main__":
    main()
