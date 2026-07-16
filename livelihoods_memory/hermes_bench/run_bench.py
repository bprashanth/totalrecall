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
        "A-DS": ("deepseek/deepseek-chat-v4", "dsv4")}
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
    body = {"model": "deepseek/deepseek-chat-v4", "max_tokens": 120, "temperature": 0.7,
            "messages": [{"role": "user", "content":
                "You are Meena, 34, NGO program associate from Erode (Indian English, terse, "
                "warm). The assistant just said:\n---\n" + prev_answer[-600:] + "\n---\n"
                "Write ONLY your next chat message (1-2 sentences): first react to something "
                "concrete it said (agree/doubt/pick at it), then ask about: " + goal +
                "\nDo not add quotes or labels.")}]}
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

def ask_hermes(text, session, model, provider):
    cmd = ["docker", "exec", "hermes-live", "sh", "-c",
           "cd /opt/data && timeout 900 hermes -z " + json.dumps(text) +
           f" -m {json.dumps(model)} --provider {provider} --continue {session} 2>/dev/null"]
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=960)
    return (p.stdout or "").strip() or "[NO OUTPUT — hermes error: " + (p.stderr or "")[-300:] + "]"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", required=True, choices=list(ARMS))
    ap.add_argument("--round", default="v1")
    ap.add_argument("--turns", type=int, default=14)
    a = ap.parse_args()
    model, provider = ARMS[a.arm]
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
            q = TURN1 if i == 0 else phrase(ARC[i], prev)
            t0 = time.time()
            ans = ask_hermes(q, session, model, provider)
            f.write(f"## Turn {i+1} — {ARC[i][:60]}\n### Meena\n{q}\n\n"
                    f"### Hermes\n{ans}\n\n_(latency {time.time()-t0:.0f}s)_\n\n")
            f.flush()
            prev = ans
            print(f"[{a.arm}] turn {i+1}/{a.turns} done ({time.time()-t0:.0f}s)", flush=True)
    print(f"[{a.arm}] transcript -> {path}", flush=True)

if __name__ == "__main__":
    main()
