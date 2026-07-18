# Hermes-native comparison integration

This directory is a reversible integration candidate. It does not modify the origin repository or
restart the shared Hermes container/model server.

All normal comparison modes use the Hermes conversation shell:

```text
./integration/chat.sh --runtime untyped    --context ebtl    --model deepseekv4
./integration/chat.sh --runtime typed      --context ebtl    --model deepseekv4
./integration/chat.sh --runtime no-algebra --context ebtl    --model deepseekv4

./integration/chat.sh --runtime typed --model qwen2b
./integration/chat.sh --runtime typed --model qwen2b-lora
```

The axes are independent:

- `untyped`: original connector/playbook reasoning. `untyped + ebtl + deepseekv4` delegates exactly
  to the origin `agents/hermes/chat.sh`.
- `typed`: Hermes handles conversation and clarification; a profile hook dispatches one registered
  `typed_evaluate` tool before each scoped turn. The 2B does not choose arbitrary terminal calls;
  the governed executor emits the actual connector events it ran.
- `no-algebra`: the same neutral Hermes profile and dialogue discipline, with no playbook,
  connectors, or typed bridge.
- `general`: no place is implied. This is the default for typed and no-algebra banks.
- `ebtl`: binds “here” to the exact site AOI from the imported `SITE_EBTL.json`. This is explicit so
  broad holdouts are not silently site-seeded.

With no flags, `chat.sh` delegates to the origin entrypoint unchanged. `HERMES_RESUME`, `CONTINUE`,
`HERMES_SOURCE`, `HERMES_MAXTURNS`, and `AUTO_APPROVE` are forwarded.

## Isolated profile

`scripts/deploy_hermes.sh` creates/refreshes a `dss-eval` profile and versioned workspaces under
`/opt/data/work/dss_typed`. It copies only the minimal typed runtime, uses a neutral SOUL, has no
bundled skills, and keeps sessions separate from the origin default profile. It copies the existing
provider and discipline-plugin configuration but does not change the default profile or restart the
container.

The local endpoint currently advertises `qwen3.5-2b` with an actual 8K server limit, while Hermes
normally refuses models below 64K. The isolated profile uses a 64K compatibility declaration and a
2,048-token output cap so short-turn dialogue can be diagnosed. This is not evidence of long-context
compatibility and must not be used for long-context claims. The endpoint also lacks server-side
automatic tool calling. Typed mode therefore invokes its registered evaluation tool
programmatically and shows connector events, while Hermes's footer still counts zero
*model-authored* tool calls. No-algebra exposes none. Untyped local runs remain blocked by that
server capability unless a tool parser is deployed.

`qwen2b-lora` fails during preflight because `qwen3.5-2b-lora` is not currently listed by
`/v1/models`; no Hermes session or retry loop starts.

## Diagnostics and safety

`--trace-json` deliberately bypasses the conversation shell for a one-question typed audit trace,
but executes inside the same deployed container so connector dependencies and corpus mounts agree:

```text
./integration/chat.sh --runtime typed --context ebtl --model qwen2b \
  --trace-json "What is the mean NDVI here in 2024?"
```

Run the contracts with:

```text
./integration/tests/test_chat_cli.sh
python3 -m unittest ecology_memory.tests.test_ecology_contract
```

Run a matched, real-session multi-turn comparison with:

```text
python3 ecology_memory/integration/eval/run_multiturn.py \
  --case site_snake_inventory \
  --arm typed:qwen2b \
  --arm typed:deepseekv4

python3 ecology_memory/integration/eval/run_multiturn.py \
  --case site_snake_inventory \
  --arm untyped:deepseekv4
```

The runner resumes one actual Hermes session per arm, uses identical turns, and stores the full
terminal transcript, session ID, exit code, and per-turn latency under `eval/runs/`. The first
matched report is `eval/runs/20260716-snake-head-to-head.md`.

The five-topic locked-connector wall and the precise meaning of footer/tool parity are documented
in `eval/runs/20260716-origin-equivalence-wall.md`.

The typed site context also imports the primary `Faunal Survey 2024` snake tables as structured,
page-addressed evidence. A broad snake request resolves to that complete local inventory before any
regional transfer is considered. Requests for additional *likely* species are deliberately not
rewritten as inventory requests: the current runtime attempts the transfer contract and fails
closed if occurrence-grain donor evidence is unavailable.

`manifests/origin-lock.json` inventories the admitted origin-facing files by commit and SHA-256.
Export to an origin-side `dss_typed/` remains a later explicit operation after framework
reconciliation and the audited comparison matrix.
