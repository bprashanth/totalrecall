# Hermes-native multi-turn smoke — 2026-07-16

## Contract under test

The runtime axis changes the reasoning scaffold, not the conversation shell. Typed, original
untyped, and no-algebra paths all use Hermes; EBTL is an explicit context flag; model selection is
independent. This is smoke evidence, not saturation or a complete model ranking.

## Opening turn: `tell me about ebtl`

### Typed + DeepSeek-v4

- asked which of vegetation/land cover, wildlife, fire/degradation, or restoration change the user
  wanted;
- ran zero tools;
- completed in about 11 seconds;
- emitted a resumable `dss-eval` session.

### Original untyped + DeepSeek-v4

- delegated to the exact origin `chat.sh` and asked a useful multi-option clarification;
- loaded the conservation skill and playbook before answering (three recorded tool calls);
- completed in about 28 seconds;
- emitted an auxiliary title-generation 404 because the origin profile still names local model
  alias `qwen`, which the server does not advertise.

### No-algebra + DeepSeek-v4

- asked for a narrower direction with zero tools in about five seconds;
- incorrectly described the site as a private grassland and promised observed numbers despite
  having no live/project source access. This is a groundedness failure for the no-algebra baseline.

### Typed + base local 2B

- asked a clarification with zero tools, but its wording was less clean and did not consistently
  preserve the offered menu;
- required a short-turn compatibility override because Hermes rejects the endpoint's actual 8K
  context metadata;
- the endpoint lacks automatic tool choice, so the typed result is injected by a profile hook and
  no tools are exposed to the local model.

## Resumed choice: `1` (vegetation / land cover)

The EBTL context maps the choice to a typed site-centre WorldCover lookup. The added source adapter
uses the declared site centre from `SITE_EBTL.json`, labels it as a point proxy, and never treats it
as whole-AOI coverage. ESA WorldCover v200 returned `shrubland` at that point.

### Typed + DeepSeek-v4

The resumed response correctly stated:

- modelled class `shrubland`;
- site centre `(12.73394, 78.18344)`;
- ESA WorldCover v200 as the raster source;
- one declared site-centre point as support; and
- point proxy, not wall-to-wall AOI cover.

### Typed + base local 2B

The resumed response reached `shrubland` but mislabeled part of the modelled result as observed and
added an irrelevant meta sentence. This is a concrete LoRA target: exact evidence-label fidelity,
no invented scope expansion, and clean short-answer termination.

## Model preflight

`qwen2b-lora` now exits before Hermes starts:

```text
model 'qwen3.5-2b-lora' is not deployed; available local models: qwen3.5-2b.
No Hermes session was started.
```

## Verification

- 118 deterministic sector contract tests pass;
- Hermes wrapper shell contract passes;
- governance validation passes (46 proposals, 5 released);
- the algebra review packet and both review artifacts contain no sector/site references;
- origin remains clean at the locked commit.
