#!/bin/bash
# INDIAN-DIALECT baselines: 5 models on the frozen Indic eval (first-contact runs).
# Run dirs follow the curve-* naming so curve.py picks them up automatically.
# Sequential on purpose (single GPU slot for local models; :8001 untouched throughout).
set -u
cd "$(dirname "$0")"
BANK=questions/indic-eval-001.json
LOG=../runs/indic-baselines.log
{
  echo "=== indic baselines $(date -Is) ==="
  for spec in "qwen2b:A2:" "loravb:A3:--minimal" "lora9b:A3:--minimal" "qwen9b:A2:" "deepseekv4:A2:"; do
    model="${spec%%:*}"; rest="${spec#*:}"; arm="${rest%%:*}"; flags="${rest#*:}"
    out="../runs/curve-${arm}-${model}-indic"
    echo "--- $model ($arm) $flags -> $out"
    python3 llm.py "$model"
    python3 run_bench.py --model "$model" --questions "$BANK" --out "$out" $flags
  done
  echo "=== done $(date -Is) ==="
} >> "$LOG" 2>&1
tail -n 40 "$LOG"
