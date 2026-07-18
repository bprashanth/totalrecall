#!/usr/bin/env bash
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
CHAT="$(cd "$HERE/.." && pwd)/chat.sh"

"$CHAT" --help | grep -q 'one Hermes shell, independent algebra/model/context axes'

# Compatibility and exact-original delegation.
"$CHAT" --dry-run test | grep -q 'idlisseus/agents/hermes/chat.sh test'
"$CHAT" --runtime legacy --context ebtl --model deepseekv4 --dry-run test \
  | grep -q 'idlisseus/agents/hermes/chat.sh.*--model deepseekv4 test'
"$CHAT" --runtime untyped --model deepseekv4 --dry-run test \
  | grep -q 'idlisseus/agents/hermes/chat.sh.*--model deepseekv4 test'

# Every new comparison path resolves to Hermes, never the old generic Python REPL.
typed_ds="$($CHAT --runtime typed --model deepseekv4 --dry-run test)"
grep -q 'docker exec' <<<"$typed_ds"
grep -q 'HERMES_HOME=/opt/data/profiles/dss-eval' <<<"$typed_ds"
grep -q 'hermes chat' <<<"$typed_ds"
grep -q 'DSS_EVAL_RUNTIME=typed' <<<"$typed_ds"
grep -q 'workspaces/typed/general' <<<"$typed_ds"
! grep -q 'runtime/chat.py' <<<"$typed_ds"

typed_site="$($CHAT --runtime typed --context ebtl --model qwen2b --dry-run test)"
grep -q 'qwen3.5-2b.*provider custom' <<<"$typed_site"
grep -q 'DSS_TYPED_CONTEXT=ebtl' <<<"$typed_site"
grep -q 'workspaces/typed/ebtl' <<<"$typed_site"

typed_lora9b="$($CHAT --runtime typed --context ebtl --model lora9b --dry-run test)"
grep -q -- '-m lora9b --provider lora9b' <<<"$typed_lora9b"
grep -q 'DSS_TYPED_MODEL=lora9b' <<<"$typed_lora9b"

noalg="$($CHAT --runtime no-algebra --context ebtl --model deepseekv4 --dry-run test)"
grep -q 'DSS_EVAL_RUNTIME=no-algebra' <<<"$noalg"
grep -q 'workspaces/no-algebra/ebtl' <<<"$noalg"
! grep -q -- '-t hermes-cli' <<<"$noalg"

# The original untyped stack needs tools when it cannot delegate (local 2B case).
untyped_local="$($CHAT --runtime untyped --context general --model qwen2b --dry-run test)"
grep -q 'workspaces/untyped/general' <<<"$untyped_local"
grep -q -- '-t hermes-cli' <<<"$untyped_local"

# Multi-turn/session controls survive wrapper resolution.
resumed="$(AUTO_APPROVE=1 HERMES_RESUME=session-123 HERMES_SOURCE=matrix-a HERMES_MAXTURNS=4 \
  "$CHAT" --runtime typed --model deepseekv4 --dry-run followup)"
grep -q -- '--resume session-123' <<<"$resumed"
grep -q 'DSS_TYPED_RESUME_SESSION=session-123' <<<"$resumed"
grep -q -- '--source matrix-a' <<<"$resumed"
grep -q -- '--max-turns 4' <<<"$resumed"
grep -q -- '--yolo' <<<"$resumed"

# JSON is an explicit typed diagnostic, not the conversational path.
trace="$($CHAT --runtime typed --context ebtl --model qwen2b --trace-json --dry-run test)"
grep -q 'runtime/chat.py.*--context ebtl.*--json test' <<<"$trace"

if "$CHAT" --runtime no-algebra --trace-json --dry-run test >/dev/null 2>&1; then
  echo "no-algebra trace should fail closed" >&2
  exit 1
fi
if "$CHAT" --runtime typed --model vendor/raw --dry-run test >/dev/null 2>&1; then
  echo "typed raw model without parser role should fail closed" >&2
  exit 1
fi
if "$CHAT" --runtime unknown --dry-run test >/dev/null 2>&1; then
  echo "unknown runtime should fail closed" >&2
  exit 1
fi
if "$CHAT" --context unknown --dry-run test >/dev/null 2>&1; then
  echo "unknown context should fail closed" >&2
  exit 1
fi

echo "Hermes chat CLI contract: OK"
