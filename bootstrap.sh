#!/usr/bin/env bash
# bootstrap.sh <sector>  ->  creates <sector>_memory/ with the frozen benchmark scaffold.
# e.g.  ./bootstrap.sh livelihoods   ->  livelihoods_memory/
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
SECTOR="${1:?usage: ./bootstrap.sh <sector>   (e.g. livelihoods, transport)}"
DEST="$HERE/${SECTOR}_memory"
[ -e "$DEST" ] && { echo "refusing: $DEST already exists"; exit 1; }
SPEC_VERSION="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["algebra_version"])' \
  "$HERE/governance/framework-manifest.json")"

mkdir -p "$DEST"/{harness,algebra,questions,runs,corpus,chronology}
cp "$HERE"/kit/harness/*.py "$DEST/harness/"
cp "$HERE"/kit/algebra/*.md "$DEST/algebra/"
cp "$HERE"/kit/PROMPT.md "$DEST/PROMPT.md"
cp "$HERE"/kit/AGENTS.md "$DEST/AGENTS.md"
cp "$HERE"/kit/SATURATION.md "$DEST/SATURATION.md"
cp "$HERE"/governance/framework-manifest.json "$DEST/framework-lock.json"
cat > "$DEST/sector.json" <<EOF
{ "sector": "$SECTOR", "created": "$(date -Iseconds)", "spec_version": "$SPEC_VERSION",
  "parser_under_test": "qwen2b", "reference_run": "heartwood/docs/architecture/memory/benchmarks" }
EOF
cat > "$DEST/spec-proposals.md" <<'EOF'
# Spec proposals from this sector (append-only; do NOT edit the spec directly)
Each entry: date · the question that forced it · why the current spec cannot express/handle it ·
the proposed change · evidence (trace path). The cross-sector supervisor reconciles these.
EOF
cat > "$DEST/FINDINGS.md" <<EOF
# FINDINGS — $SECTOR sector
Running log, newest at bottom. Tag each finding [HARNESS]/[CONNECTOR]/[PARSER]/[SPEC-PROPOSAL]/[SCORING].
Every equivalence decision you make as judge gets recorded here with its reasoning.
EOF
echo "bootstrapped $DEST"
echo "next: open $DEST/PROMPT.md and follow it top to bottom."
