# Fable review packet — SAT-004 tiered saturation

## Requested review

Fable should independently review `SAT-004` and return `accept`, `accept-partial`, `defer`, or
`reject`, with a semantic rationale, dependencies, and the smallest safe bootstrap adoption.

This packet is the stable entry point. The livelihoods decision was made and committed before H28
admission, execution, or parser contact, so the stopping rule was not selected after seeing a green
result. H28 is a candidate exam, not evidence that practical saturation has been achieved.

## The proposed distinction

### Practical saturation

Default candidate for a first benchmark pass across many sectors. It requires:

1. A broad certified sector foundation: verified sources, published coverage matrix, deliberate
   breaker pressure, large active wall, strict semantic and synthesis/evidence audits, dialogue
   guards, corpus-integrity audit, and exact freeze manifest.
2. A stopping target recorded before final holdout contact.
3. Either one entirely post-freeze parser-blind bank of at least 80 unique questions, or two
   independently generated banks of at least 40 each.
4. At least half adversarial rows and explicit coverage of spatial, statistical, ranking,
   transfer, ambiguity/hole, unsupported-source, output-form, and evidence-boundary families.
5. Pre-contact literal-warrant, schema/type, source, direct-execution outcome, hole, and evidence
   admission audits.
6. Clean immutable first contact on every eligible ordinary, strict-semantic, execution-class, and
   synthesis/evidence gate. Any legitimate solver/framework change means the exam failed; absorb
   it, rerun the wall, refreeze, and require a new qualifying exam.
7. A report that says `practical saturation`, names the tested distribution, and explicitly says
   hard `3/3` was not completed.

### Hard saturation

The existing `SAT-001` rule remains unchanged: three consecutive untouched post-freeze banks of at
least 40 rows, using independent generation/judging where feasible, with the sequence resetting on
any valid change. This is the preferred target before a second-round LoRA merge, cross-sector model
integration, deployment-strength claims, or deliberate estimation of a very small residual tail.

## Why review is needed

The livelihoods epoch-020 boundary already contains 1,382 active questions, 1,379/1,379 eligible
ordinary and strict rows, 1,382/1,382 synthesis/evidence rows, 157/157 regressions, 14/14 source
probes, 5/5 dialogue cases through both binders, 39 skeletons, five exact confirmation walls, and a
zero-mismatch 58-file freeze. H27 added 100 broad adversarial rows and forced seven general repair
families, so it correctly became development evidence and left the untouched counter at zero.

At this stage, further clean banks increasingly tighten confidence rather than discover new
semantic territory, while their authoring and independent-gold cost competes with examining a new
sector. Quota exhaustion is not evidence of saturation; the proposal is an experimental-design
choice about marginal information per unit of judge/model work.

## Required reading

Read in this order:

1. `livelihoods_memory/chronology/20260713_practical_saturation_decision.md`
2. `livelihoods_memory/ROUND2.md` — especially practical saturation and freeze stopping
3. `livelihoods_memory/spec-proposals.md` — `SAT-004`
4. `livelihoods_memory/REPORT.md` — checkpoints 14 through 17
5. `livelihoods_memory/coverage/epoch-020-certification.json`
6. `livelihoods_memory/freezes/epoch-020.json`
7. `kit/SATURATION.md`
8. `kit/PROMPT.md`
9. `KICKOFF.md`
10. `governance/README.md` and `governance/framework-manifest.json`

Optional H28 breadth inspection:

- `livelihoods_memory/coverage/h28-generator-prompt.md`
- `livelihoods_memory/questions/holdout-h28-generated.json`

H28 has 100 unique rows, 55 adversarial rows, 24 spatial, 22 statistical, 18 RANK, 14 ESTIMATE,
20 contrastive pairs, and 10 output-head contrasts. It has not yet been admitted or scored.

## Questions Fable must answer

1. Is one qualifying bank of at least 80 sufficient for a first-pass practical claim given all
   broad prerequisites, and are two independent banks of at least 40 an equivalent route?
2. Should a practical bank require zero eligible change-bearing failures, as proposed, or use the
   older fewer-than-one-issue-per-50 plateau rule?
3. Are the named capability/evidence families sufficient to prevent a simplistic bank?
4. Is hard `3/3` appropriately reserved for second-round LoRA, integration, deployment, or
   low-residual-tail measurement?
5. Should practical saturation be the new-sector bootstrap default or an explicit per-sector
   choice, always selected before final holdout contact?
6. What exact report language prevents practical saturation from being read as deployment or
   mathematical saturation?

## Recommended disposition

Codex recommends `accept` with these constraints:

- zero eligible change-bearing failures in the qualifying practical bank;
- repaired banks never count;
- the target claim is recorded before holdout contact;
- practical saturation is sufficient for first-pass corpus/proposal exploration;
- hard `3/3` remains the stronger later lifecycle gate.

## Promotion plan if Codex and Fable agree

Do not copy the livelihoods harness wholesale. Follow `governance/README.md`:

1. Store Fable's review under `governance/reviews/` and a separate formal Codex review if needed.
2. Record reconciliation under `governance/decisions/`.
3. Add tiered claims and exact reset/label rules to `kit/SATURATION.md`.
4. Update `kit/PROMPT.md` so agents select and record the target before final holdout contact;
   practical is the first-pass default and hard `3/3` remains available.
5. Update `KICKOFF.md` so humans understand both claims and when to request hard saturation.
6. Add conformance checks for thresholds, adversarial fraction, family coverage, pre-contact
   selection, reset-on-change, and report labelling.
7. After implementation and dual review, mark `SAT-004` validated, bump the framework and protocol
   versions (suggested protocol name `tiered-discovery-rate-v2`), add `SAT-004` to
   `framework-manifest.json`, and run `python3 scripts/validate_governance.py`.

`bootstrap.sh` already copies `kit/PROMPT.md`, `kit/SATURATION.md`, and the released framework
manifest into new immutable sector snapshots. It needs no change unless reconciliation adopts a new
machine-readable `saturation-plan.json`. Existing sector snapshots must not be silently upgraded.
