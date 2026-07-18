# EBTL showcase head-to-head — frozen repaired epoch

## Outcome

The typed Hermes/Qwen 2B arm passed the pre-declared showcase stop against the untouched origin
Hermes/DeepSeek-v4 arm on 12 multi-turn cases. It scored 110/120 versus 69/120, a 59.4% relative
quality improvement, with zero typed critical errors. Median complete-case latency was 22.548 s
versus 227.714 s; total latency was 299.668 s versus 3048.675 s.

This is a repaired showcase bank, not an untouched post-freeze holdout and not practical or hard
saturation under `SATURATION.md`.

## Method

Every arm used the real Hermes shell and a resumed session. The candidate was
`integration/chat.sh --runtime typed --context ebtl --model qwen2b`; the baseline was the untouched
origin `agents/hermes/chat.sh --model deepseekv4`. The exact origin connector copy is pinned by
`integration/manifests/origin-lock.json`; the origin repository was not changed.

Each case received 0–2 on factual/source correctness, provenance/grain honesty, connector/search
adequacy, multi-turn relevance, and concise/actionable response. Critical errors were separately
gated: false absence, fabricated taxa or measurements, unsupported causal/feeding links,
bbox/property conflation, and transfer presented as local. Cursor
`gpt-5.3-codex-low-fast` performed a read-only advisory review; Codex audited its decisions and
mechanically summed the scores. The complete hashes, scores, latencies, and critical-error labels
are in `20260717-showcase-epoch.json`.

## What made the difference

- The typed arm finds imported page-addressed local surveys before falling back to regional
  occurrence or model memory. This recovered 14 snakes, four venomous snake species, 67 birds,
  two indirect elephant passage events, and nursery snapshots that the origin chat missed.
- Fire, occurrence, discovery, greenness, and land-cover calls use the exact copied origin
  production implementations through thin typed adapters. Visible `🔌` events show the executed
  connector path. Hermes still reports zero *model-authored* tool calls because local vLLM tool
  parsing is unavailable; no session rows were falsified to change that footer.
- Regional transfer is gated and labelled. Arachnid category discovery starts with the higher
  taxon, obtains dynamic candidates from returned GBIF data, and runs explicit climate/feature
  gates. It does not promote failed candidates to site expectations.
- Paper embeddings are used for discovery, but a semantic lead is never treated as a local
  measurement. The Dryad Lantana bird-frugivory join is regional evidence; the local bird survey
  and public plant bbox points retain their distinct spatial grains.
- Sparse data produces a bounded estimate or a field-data request, not a confident absence,
  causal link, or habitat requirement.

## Remaining limits

The result is site-showcase superiority, not global connector equivalence. Terrain, water,
commercial imagery, broader paper extraction, and several production connectors still need
matched cases. The LoRA model name is not deployed at the shared endpoint, so no base-versus-LoRA
column can run. The current evidence supports using a larger model as an offline question author,
advisory judge, or verifier; placing it before deterministic connector execution did not add facts
and previously increased latency and unsupported synthesis.
