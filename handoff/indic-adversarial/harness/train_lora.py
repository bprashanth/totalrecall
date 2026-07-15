"""train_lora — LoRA the 2B on (question -> IR) pairs with a MINIMAL prompt.

The experiment: can fine-tuning close the measured composition gap (hard-eval shape 0.10)
without the 15-few-shot prompt? Training runs inside a throwaway container from the vLLM image
(torch+cuda verified there); this script is self-contained (no HF Trainer/datasets — manual
loop, loss masked to assistant tokens).

Data mix: hard-train-001 (the gap, 160) + easy corpus parse.jsonl (retention, ~173) —
identical MINIMAL_SYSTEM for every row; eval later uses the same minimal prompt.

Usage (inside container; see launch block at bottom of file for the docker command):
  python3 train_lora.py --data /work/sft.jsonl --out /work/adapter-001 --epochs 3
Build the sft file first (on host):
  python3 train_lora.py --build-data ../lora/sft.jsonl
"""
import argparse
import json
import os
import random

MINIMAL_SYSTEM = ("Translate the user's question about a place into the JSON query tree (ops: "
                  "SELECT, ANNOTATE, RELATE, AGGREGATE, COMPARE, RANK, ESTIMATE, REGION; holes "
                  "start with '?'). Output only JSON.")


def build_data(out_path):
    rows = []
    hb = json.load(open("questions/hard-train-001.json"))
    for q in hb["questions"]:
        rows.append({"q": q["q"], "ir": q["gold_ir"], "src": "hard-" + q["cclass"]})
    for line in open("../corpus/parse.jsonl"):
        d = json.loads(line)
        m = d["messages"]
        rows.append({"q": m[1]["content"], "ir": json.loads(m[2]["content"]), "src": "easy"})
    random.Random(3).shuffle(rows)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    from collections import Counter
    print(f"{len(rows)} sft rows -> {out_path}",
          dict(Counter(r['src'] for r in rows)))


def train(data, out, epochs, lr, r_lora, mid="Qwen/Qwen3.5-2B"):
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from peft import LoraConfig, get_peft_model
    tok = AutoTokenizer.from_pretrained(mid)
    model = AutoModelForCausalLM.from_pretrained(mid, torch_dtype=torch.bfloat16,
                                                 device_map="cuda")
    cfg = LoraConfig(r=r_lora, lora_alpha=2 * r_lora, lora_dropout=0.05,
                     target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
                     task_type="CAUSAL_LM")
    model = get_peft_model(model, cfg)
    model.print_trainable_parameters()

    rows = [json.loads(l) for l in open(data)]
    def encode(r):
        msgs = [{"role": "system", "content": MINIMAL_SYSTEM},
                {"role": "user", "content": r["q"]}]
        prompt = tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
        target = json.dumps(r["ir"]) + tok.eos_token
        pi = tok(prompt, add_special_tokens=False).input_ids
        ti = tok(target, add_special_tokens=False).input_ids
        ids = (pi + ti)[:1024]
        labels = ([-100] * len(pi) + ti)[:1024]
        return ids, labels
    enc = [encode(r) for r in rows]

    opt = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=lr)
    model.train()
    step = 0
    accum = 8
    for ep in range(epochs):
        random.Random(ep).shuffle(enc)
        for ids, labels in enc:
            x = torch.tensor([ids]).cuda()
            y = torch.tensor([labels]).cuda()
            loss = model(input_ids=x, labels=y).loss / accum
            loss.backward()
            step += 1
            if step % accum == 0:
                opt.step()
                opt.zero_grad()
            if step % 20 == 0:  # denser loss trace: the 9B run needs a printable loss curve
                print(f"ep{ep} step{step} loss={loss.item()*accum:.3f}", flush=True)
    model.save_pretrained(out)
    tok.save_pretrained(out)
    print(f"adapter saved -> {out}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--build-data")
    ap.add_argument("--data")
    ap.add_argument("--out")
    ap.add_argument("--epochs", type=int, default=3)
    ap.add_argument("--lr", type=float, default=1e-4)
    ap.add_argument("--r", type=int, default=16)
    ap.add_argument("--model-id", default="Qwen/Qwen3.5-2B")  # 9B ROI point: Qwen/Qwen3.5-9B
    a = ap.parse_args()
    if a.build_data:
        build_data(a.build_data)
    else:
        train(a.data, a.out, a.epochs, a.lr, a.r, a.model_id)

# Launch (host):
#   IMG=$(docker inspect qwen-sidekick-vllm --format '{{.Config.Image}}')
#   docker run --rm --gpus all -v ~/.cache/huggingface:/root/.cache/huggingface \
#     -v $PWD/..:/bench -w /bench/harness --entrypoint bash "$IMG" \
#     -c "pip install -q peft && python3 train_lora.py --data /bench/lora/sft.jsonl --out /bench/lora/adapter-001 --epochs 3"
# Serve for eval (does NOT touch :8001):
#   vllm serve Qwen/Qwen3.5-2B --port 8002 --host 172.17.0.1 --enable-lora \
#     --lora-modules loravb=/bench/lora/adapter-001
