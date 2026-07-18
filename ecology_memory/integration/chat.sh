#!/usr/bin/env bash
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
ORIGIN_CHAT="${IDLISSEUS_CHAT:-/home/beeps/src/github.com/bprashanth/idlisseus/agents/hermes/chat.sh}"
CONTAINER="${HERMES_CONTAINER:-hermes-live}"
PROFILE="${DSS_HERMES_PROFILE:-dss-eval}"

usage() {
  cat <<'HELP'
chat.sh — one Hermes shell, independent algebra/model/context axes

USAGE
  chat.sh [--runtime typed|untyped|no-algebra] [--context general|ebtl]
          [--model MODEL] [--selector ROLE] [--compiler ROLE] [--responder ROLE]
          [--trace-json] [--dry-run] [QUESTION]

RUNTIMES (all normal chat paths use Hermes and preserve multi-turn sessions)
  untyped      Original connector/playbook reasoning. With EBTL and a supported original model,
               delegates exactly to the origin Hermes chat.sh. Alias: legacy.
  typed        Hermes dialogue and clarification wrapped around the deterministic typed bridge.
  no-algebra   Same Hermes shell/discipline, but no playbook, connectors, or typed bridge.

CONTEXT
  general      No implied site. Default for typed and no-algebra.
  ebtl         Bind “here” to the original EBTL site AOI. Default for untyped.

MODELS
  qwen2b, qwen2b-lora, lora9b, deepseekv4, glm5.2, qwen9b, qwen27b, qwen122b,
  qwen397b, coder30b; no-algebra also accepts a raw OpenRouter provider/slug.

OPTIONS
  --trace-json  Run one typed question directly and emit its audit trace. This is a diagnostic,
                not the conversational shell. Alias: --json.
  --selector    Semantic capability selector; default qwen9b>deepseekv4.
  --compiler    Algebra compiler after selection; default is --model.
  --responder   Audited response model; default qwen9b, or deterministic.
  --dry-run     Print the resolved command without deployment or execution.
  -h, --help    Show this help.

With no flags, behavior is exactly the origin EBTL Hermes chat.sh.
Use HERMES_RESUME, CONTINUE, HERMES_SOURCE, HERMES_MAXTURNS, and AUTO_APPROVE as with the origin.
HELP
}

RUNTIME="${CHAT_RUNTIME:-}"
CONTEXT="${CHAT_CONTEXT:-}"
MODEL="${CHAT_MODEL:-}"
TRACE_JSON=0
DRY_RUN=0
SAW_OPTION=0
QUESTION=()
SELECTOR="${DSS_TYPED_SELECTOR:-qwen9b>deepseekv4}"
COMPILER="${DSS_TYPED_COMPILER:-}"
RESPONDER="${DSS_TYPED_RESPONDER:-qwen9b}"

while [ "$#" -gt 0 ]; do
  case "$1" in
    --runtime)
      [ "$#" -ge 2 ] || { echo "chat.sh: --runtime needs a value" >&2; exit 2; }
      RUNTIME="$2"; SAW_OPTION=1; shift 2 ;;
    --context)
      [ "$#" -ge 2 ] || { echo "chat.sh: --context needs a value" >&2; exit 2; }
      CONTEXT="$2"; SAW_OPTION=1; shift 2 ;;
    --model|-m)
      [ "$#" -ge 2 ] || { echo "chat.sh: --model needs a value" >&2; exit 2; }
      MODEL="$2"; SAW_OPTION=1; shift 2 ;;
    --selector)
      [ "$#" -ge 2 ] || { echo "chat.sh: --selector needs a value" >&2; exit 2; }
      SELECTOR="$2"; SAW_OPTION=1; shift 2 ;;
    --compiler)
      [ "$#" -ge 2 ] || { echo "chat.sh: --compiler needs a value" >&2; exit 2; }
      COMPILER="$2"; SAW_OPTION=1; shift 2 ;;
    --responder)
      [ "$#" -ge 2 ] || { echo "chat.sh: --responder needs a value" >&2; exit 2; }
      RESPONDER="$2"; SAW_OPTION=1; shift 2 ;;
    --trace-json|--json) TRACE_JSON=1; SAW_OPTION=1; shift ;;
    --dry-run) DRY_RUN=1; SAW_OPTION=1; shift ;;
    --help|-h) usage; exit 0 ;;
    --) shift; QUESTION+=("$@"); break ;;
    -*) echo "chat.sh: unknown option '$1'" >&2; exit 2 ;;
    *) QUESTION+=("$1"); shift ;;
  esac
done

print_command() {
  printf '%q' "$1"; shift
  for arg in "$@"; do printf ' %q' "$arg"; done
  printf '\n'
}

# The no-option compatibility path remains byte-for-byte owned by the origin wrapper.
if [ "$SAW_OPTION" -eq 0 ] && [ -z "$RUNTIME$CONTEXT$MODEL" ]; then
  CMD=("$ORIGIN_CHAT" "${QUESTION[@]}")
  [ "$DRY_RUN" -eq 0 ] || { print_command "${CMD[@]}"; exit 0; }
  exec "${CMD[@]}"
fi

[ "$RUNTIME" != "legacy" ] || RUNTIME="untyped"
RUNTIME="${RUNTIME:-untyped}"
case "$RUNTIME" in
  typed|untyped|no-algebra) ;;
  *) echo "chat.sh: unknown runtime '$RUNTIME' (use typed, untyped, or no-algebra)" >&2; exit 2 ;;
esac
if [ -z "$CONTEXT" ]; then
  [ "$RUNTIME" = "untyped" ] && CONTEXT="ebtl" || CONTEXT="general"
fi
case "$CONTEXT" in general|ebtl) ;; *) echo "chat.sh: unknown context '$CONTEXT'" >&2; exit 2 ;; esac
MODEL="${MODEL:-$([ "$RUNTIME" = "untyped" ] && echo qwen122b || echo qwen2b)}"

# Preserve the exact original stack whenever that comparison is representable there.
if [ "$RUNTIME" = "untyped" ] && [ "$CONTEXT" = "ebtl" ] && [ "$TRACE_JSON" -eq 0 ]; then
  case "$MODEL" in
    qwen2b|2b|qwen2b-lora|2b-lora|loravb) ;;
    *)
      CMD=("$ORIGIN_CHAT")
      [ "$MODEL" = "qwen122b" ] || CMD+=(--model "$MODEL")
      CMD+=("${QUESTION[@]}")
      [ "$DRY_RUN" -eq 0 ] || { print_command "${CMD[@]}"; exit 0; }
      exec "${CMD[@]}"
      ;;
  esac
fi

BRIDGE_MODEL=""
LOCAL_MODEL=0
MFLAGS=()
case "$MODEL" in
  qwen2b|2b)
    LOCAL_MODEL=1; BRIDGE_MODEL=qwen2b; MFLAGS=(-m qwen3.5-2b --provider custom) ;;
  qwen2b-lora|2b-lora|loravb)
    LOCAL_MODEL=1; BRIDGE_MODEL=loravb; MFLAGS=(-m qwen3.5-2b-lora --provider custom) ;;
  lora9b|9b-lora|merged-9b-002)
    LOCAL_MODEL=1; BRIDGE_MODEL=lora9b; MFLAGS=(-m lora9b --provider lora9b) ;;
  deepseekv4|deepseek-v4|deepseek|dsv4)
    BRIDGE_MODEL=deepseekv4; MFLAGS=(-m deepseek/deepseek-v4-flash --provider openrouter) ;;
  glm5.2|glm-5.2|glm)
    BRIDGE_MODEL=glm; MFLAGS=(-m z-ai/glm-5.2 --provider openrouter) ;;
  qwen9b) BRIDGE_MODEL=qwen9b; MFLAGS=(-m qwen/qwen3.5-9b --provider openrouter) ;;
  qwen27b) BRIDGE_MODEL=qwen27b; MFLAGS=(-m qwen/qwen3.5-27b --provider openrouter) ;;
  qwen122b) BRIDGE_MODEL=qwen122b; MFLAGS=(-m qwen/qwen3.5-122b-a10b --provider openrouter) ;;
  qwen397b) BRIDGE_MODEL=qwen397b; MFLAGS=(-m qwen/qwen3.5-397b-a17b --provider openrouter) ;;
  coder30b) BRIDGE_MODEL=coder30b; MFLAGS=(-m qwen/qwen3-coder-30b-a3b-instruct --provider openrouter) ;;
  */*)
    [ "$RUNTIME" != "typed" ] || {
      echo "chat.sh: typed bridge has no parser role for raw model '$MODEL'" >&2; exit 2; }
    MFLAGS=(-m "$MODEL" --provider openrouter) ;;
  *) echo "chat.sh: unknown model '$MODEL'" >&2; exit 2 ;;
esac
COMPILER="${COMPILER:-$BRIDGE_MODEL}"

if [ "$TRACE_JSON" -eq 1 ]; then
  [ "$RUNTIME" = "typed" ] || { echo "chat.sh: --trace-json requires --runtime typed" >&2; exit 2; }
  [ "${#QUESTION[@]}" -gt 0 ] || { echo "chat.sh: --trace-json requires a question" >&2; exit 2; }
  TRACE_ROOT="/opt/data/work/dss_typed/ecology_memory"
  CMD=(docker exec -e "DSS_TYPED_MODEL=$BRIDGE_MODEL" -e "DSS_TYPED_CONTEXT=$CONTEXT"
       -e "DSS_TYPED_SELECTOR=$SELECTOR" -e "DSS_TYPED_COMPILER=$COMPILER"
       -e "DSS_TYPED_RESPONDER=$RESPONDER"
       -w "$TRACE_ROOT/integration/runtime" "$CONTAINER" python "$TRACE_ROOT/integration/runtime/chat.py"
       --model "$BRIDGE_MODEL" --context "$CONTEXT" --selector "$SELECTOR"
       --compiler "$COMPILER" --responder "$RESPONDER" --json "${QUESTION[@]}")
  [ "$DRY_RUN" -eq 0 ] || { print_command "${CMD[@]}"; exit 0; }
  [ "$LOCAL_MODEL" -eq 0 ] || python3 "$HERE/scripts/model_preflight.py" --model "$MODEL" --quiet
  "$HERE/scripts/deploy_hermes.sh" --quiet
  exec "${CMD[@]}"
fi

WORKSPACE="/opt/data/work/dss_typed/hermes/workspaces/$RUNTIME/$CONTEXT"
CMD=(docker exec)
[ "${#QUESTION[@]}" -gt 0 ] || CMD+=(-it)
[ -n "${HERMES_RESUME:-}" ] && CMD+=(-e "DSS_TYPED_RESUME_SESSION=$HERMES_RESUME")
CMD+=(-e "HERMES_HOME=/opt/data/profiles/$PROFILE"
      -e "DSS_TYPED_MODEL=$BRIDGE_MODEL" -e "DSS_TYPED_CONTEXT=$CONTEXT"
      -e "DSS_TYPED_SELECTOR=$SELECTOR" -e "DSS_TYPED_COMPILER=$COMPILER"
      -e "DSS_TYPED_RESPONDER=$RESPONDER"
      -e "DSS_EVAL_RUNTIME=$RUNTIME" -w "$WORKSPACE"
      "$CONTAINER" hermes chat "${MFLAGS[@]}")
[ "$RUNTIME" != "untyped" ] || CMD+=(-t hermes-cli)
[ "${AUTO_APPROVE:-0}" = "1" ] && CMD+=(--yolo)
[ "${CONTINUE:-0}" = "1" ] && CMD+=(-c)
[ -n "${HERMES_SOURCE:-}" ] && CMD+=(--source "$HERMES_SOURCE")
[ -n "${HERMES_RESUME:-}" ] && CMD+=(--resume "$HERMES_RESUME")
[ -n "${HERMES_MAXTURNS:-}" ] && CMD+=(--max-turns "$HERMES_MAXTURNS")
[ "${#QUESTION[@]}" -eq 0 ] || CMD+=(-q "${QUESTION[*]}")

[ "$DRY_RUN" -eq 0 ] || { print_command "${CMD[@]}"; exit 0; }
[ "$LOCAL_MODEL" -eq 0 ] || python3 "$HERE/scripts/model_preflight.py" --model "$MODEL" --quiet
"$HERE/scripts/deploy_hermes.sh" --quiet
exec "${CMD[@]}"
