"""LLM client — one place that knows how to reach every model in this box.

Three roles in the loop:
  - PARSER (under test): the small local model we want to eventually run on a laptop.
    Default = qwen3.5-2b on the local vLLM (172.17.0.1:8001).
  - JUDGE / GOLD author: a stronger remote model via OpenRouter (deepseek-v4-flash).
  - SUPERVISOR: the Claude process driving this harness (not called from here).

Everything is OpenAI-compatible chat/completions. Deterministic where the backend allows
(temperature 0). Responses are cached on (model, prompt) so re-runs are cheap and offline-ish.
"""
import hashlib
import http.client
import json
import os
import time
import urllib.request
import urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR = os.path.join(HERE, "cache", "llm")
os.makedirs(CACHE_DIR, exist_ok=True)

LOCAL_BASE = "http://172.17.0.1:8001/v1"
LORA_BASE = "http://172.17.0.1:8002/v1"
HAMMER_BASE = "http://172.17.0.1:8003/v1"
LORA9B_BASE = "http://172.17.0.1:8004/v1"
OPENROUTER_BASE = "https://openrouter.ai/api/v1"

# role -> (base_url, model_id, needs_openrouter_key)
# The curve holds the FAMILY constant (Qwen3.5) and sweeps params 2b->9b->27b->122b->397b, so the
# only variable is scale. All big points are API (no local GPU) -> they run in parallel. deepseek is
# the external-frontier cross-check; qwen3-coder-30b is the clean-provenance compile SPECIALIST.
MODELS = {
    "qwen2b":     (LOCAL_BASE, "qwen3.5-2b", False),          # local, the laptop target
    "qwen9b":     (OPENROUTER_BASE, "qwen/qwen3.5-9b", True),
    "qwen27b":    (OPENROUTER_BASE, "qwen/qwen3.5-27b", True),
    "qwen122b":   (OPENROUTER_BASE, "qwen/qwen3.5-122b-a10b", True),
    "qwen397b":   (OPENROUTER_BASE, "qwen/qwen3.5-397b-a17b", True),
    "coder30b":   (OPENROUTER_BASE, "qwen/qwen3-coder-30b-a3b-instruct", True),  # compile specialist
    "deepseekv4": (OPENROUTER_BASE, "deepseek/deepseek-v4-flash", True),
    "glm":        (OPENROUTER_BASE, "z-ai/glm-5.2", True),
    "loravb":     (LORA_BASE, "loravb", False),               # 2B + adapter-001, :8002
    "qwen2bbase": (LORA_BASE, "qwen3.5-2b-base", False),      # same server, no adapter
    "hammer7b":   (HAMMER_BASE, "hammer7b", False),           # fc-specialist, local :8003
    "lora9b":     (LORA9B_BASE, "lora9b", False),             # 9B + adapter-9b-001, :8004 HF shim
}


def _openrouter_key():
    p = os.path.expanduser("~/.config/idlisseus/openrouter.json")
    with open(p) as f:
        return json.load(f)["api_key"]


def _cache_path(model, messages, temperature, max_tokens):
    h = hashlib.sha256(
        json.dumps([model, messages, temperature, max_tokens], sort_keys=True).encode()
    ).hexdigest()[:24]
    return os.path.join(CACHE_DIR, f"{model.replace('/', '_')}_{h}.json")


def chat(role, messages, temperature=0.0, max_tokens=1200, use_cache=True, timeout=180,
         retries=3):
    """Return assistant text for a chat call. `role` keys into MODELS."""
    if role not in MODELS:
        raise ValueError(f"unknown role {role!r}; have {list(MODELS)}")
    base, model, needs_key = MODELS[role]
    cp = _cache_path(model, messages, temperature, max_tokens)
    if use_cache and os.path.exists(cp):
        with open(cp) as f:
            cached = json.load(f).get("text")
        if cached:  # a null/empty cached text is poison from an earlier bug — refetch
            return cached
        os.remove(cp)

    headers = {"Content-Type": "application/json"}
    if needs_key:
        headers["Authorization"] = f"Bearer {_openrouter_key()}"
    body = json.dumps({
        "model": model, "messages": messages,
        "temperature": temperature, "max_tokens": max_tokens,
    }).encode()

    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(base + "/chat/completions", data=body, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                d = json.loads(r.read())
            msg = d["choices"][0]["message"]
            text = msg.get("content")
            if not text:
                # reasoning models can burn max_tokens on reasoning and return content:null —
                # never cache/return None; retry (the loop) so the caller always gets a str.
                raise KeyError(f"empty content (finish={d['choices'][0].get('finish_reason')})")
            with open(cp, "w") as f:
                json.dump({"text": text, "model": model, "raw_usage": d.get("usage")}, f)
            return text
        except (urllib.error.URLError, urllib.error.HTTPError, KeyError, TimeoutError,
                http.client.HTTPException, ConnectionError, OSError,
                json.JSONDecodeError) as e:  # IncompleteRead etc — overnight loop must retry, not die
            last = e
            detail = ""
            if isinstance(e, urllib.error.HTTPError):
                try:
                    detail = e.read().decode()[:300]
                except Exception:
                    pass
            print(f"[llm] {role} attempt {attempt+1}/{retries} failed: {e} {detail}")
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"llm chat failed for {role}: {last}")


def ping(role):
    try:
        t = chat(role, [{"role": "user", "content": "Reply with the single word PONG."}],
                 max_tokens=8, use_cache=False, retries=1, timeout=30)
        return "PONG" in t.upper(), t.strip()[:60]
    except Exception as e:
        return False, str(e)[:120]


if __name__ == "__main__":
    import sys
    role = sys.argv[1] if len(sys.argv) > 1 else "qwen2b"
    ok, msg = ping(role)
    print(f"{role}: {'OK' if ok else 'FAIL'} -> {msg}")
