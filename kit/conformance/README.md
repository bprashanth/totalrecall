# Conditional algebra conformance assets

`buffer_questions_v2.4.json` is the neutral ALG-015 corpus required by the accepted-conditional
decision. It deliberately includes:

- single-support selection;
- the search-radius versus pairwise-threshold discrimination class;
- explicitly identical and intentionally different operand supports;
- nested-buffer canonicalization;
- a typed radius hole;
- BUFFER as an ESTIMATE target;
- dateline failure; and
- a REGION-only backward-compatibility row.

Run it with:

```bash
python3 kit/harness/run_buffer_conformance.py --model qwen2b \
  --out governance/evidence/ALG-015-buffer-qwen2b.json \
  --corpus-out kit/conformance/buffer_parse_v2.4.jsonl
```

The runner validates and fixture-executes every gold before asking the parser model. Gold execution
is the contract gate; parser agreement is separate evidence about model compilability. The artifact
does not release v2.4 or authorize training on holdout material.

Add `--require-parser-perfect` for the eventual model-promotion wall. That flag currently fails for
both available comparison models; this is expected until a v2.4-trained bundle exists.

`buffer_parse_v2.4.jsonl` is generated only from the execution-verified golds and is the candidate
training input for a future v2.4 model bundle. It is development corpus, never a holdout.

## Coordinated v2.4 bundle

`filter_questions_v2.4.json` adds ten neutral ALG-002 cases covering declared string/numeric
fields, conjunctive predicates, canonical chain merge, typed value holes, unknown fields,
predicate type mismatch, empty-result truth, and BUFFER/RELATE composition. Reference fixtures
carry the same `fields` contract as live connector results.

Run both accepted-conditional parser-visible surfaces together:

```bash
python3 kit/harness/run_v24_conformance.py --model qwen2b \
  --out governance/evidence/v24-qwen2b.json \
  --corpus-out kit/conformance/v24_parse_v2.4.jsonl
```

The combined corpus has 20 execution-verified development rows and includes the required
radius-vs-threshold discrimination class. `--require-parser-perfect` is the eventual trained-model
promotion gate. It is expected to fail on models trained only through v2.3.
