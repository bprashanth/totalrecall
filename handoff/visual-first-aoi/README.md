# Visual-first AOI question-class handoff

This handoff distils the reusable question and failure classes that informed the Idlisseus
visual-first AOI data design. It is deliberately sector-neutral and contains no model-specific
execution plan.

The machine-readable bank is [`question_classes.json`](question_classes.json). Each conversation
states the data planes that must exist before its first visual can be considered valid. It is
intended for:

- checking whether a proposed site-pack schema covers realistic multi-turn work;
- testing a visual query service independently of answer prose;
- ensuring presence, effort, trends, models and data requests remain separate;
- testing source outages and adjacent-message contamination; and
- preventing a large semantic corpus from being mistaken for analysis-ready data.

The corresponding future design and first feasibility site pack live in the Idlisseus repository:

```text
docs/VISUAL_FIRST_AOI_DATA_DESIGN.md
dss/sites/valparai/
dss/visual_index/
```

This handoff is an input ledger. The Idlisseus design is the normative document.

