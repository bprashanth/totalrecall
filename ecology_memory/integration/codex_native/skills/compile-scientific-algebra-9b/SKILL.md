---
name: compile-scientific-algebra-9b
description: Compile one explicit, evidence-bound ecology question into the frozen scientific Algebra with the local 9B model, validate its resource symbols, bind it to admitted connectors and assets, and execute it. Use for a scientific state, relationship, trend, comparison, ranking, or transfer calculation after the entity and scope are established. Do not use for site orientation, literature discovery, or choosing skills.
---

# Compile scientific Algebra with 9B

Use this compiler only for the scientific part of an investigation. Codex owns the outer dialogue,
clarification, evidence discovery, and skill selection. The controller supplies the frozen grammar,
admitted scientific symbols, and connector capabilities to 9B.

## Workflow

1. Establish the entity, region, comparison, or measurement from the user's words and admitted
   evidence.
2. Pass one short `scientific_question`. Do not pass skill names, paths, connector arguments,
   coordinates, datasets, or hand-written Algebra.
   Use the wrapper's `--pairs` form when the question contains an apostrophe.
3. Let 9B emit the frozen Algebra tree. The controller validates all symbols, binds the leaves,
   applies gates, and executes the tree.
4. If the result requests data or contains a hole, ask the returned clarification. Do not repair
   the tree yourself.
5. Invoke again only after evidence or the user's clarification changes the scientific question.

Invoke:

```bash
python3 /tmp/codex-native/sessions/<session>/input/skill_call.py \
  compile-scientific-algebra-9b \
  --pairs scientific_question="Estimate Daboia russelii suitability inside EBTL from admitted donor-region records"
```

The returned envelope includes the exact scientific question, the human-readable compiled
expression, the raw Algebra for audit, and the bound execution result.
