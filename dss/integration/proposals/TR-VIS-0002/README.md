# TR-VIS-0002 — Render the statements a result requires

## Why

The dialogue prompt is saturated. Across four rounds of the ecology benchmark, every rule added to
it cost one that was already working: the join rule went to 100% and the confidence statement fell
to 50%; shortening sentences to 14 words cost the alternative and the join rule; restoring those
cost the sentence length. The dimensions took turns failing. The three fixes in that period that
never regressed were the three that changed the data the model was given rather than the
instructions it was told to follow.

So the requirement moves to where it cannot be displaced: onto the result.

## Shape

Each result may carry, beside `limitations`:

```json
"required_statements": [
  {
    "id": "join-rule",
    "statement": "A shared square means each of Elephant and Bucerotidae was written down inside the same 1.1 km square. It is not an interaction, an association or contact between them.",
    "why": "A reader who is not told the join rule will read co-occurrence as contact."
  }
]
```

`statement` is the producing capability's own sentence, promoted from a limitation it already
declared — nothing is authored for this field. `why` is for a tooltip or a debug view, not
necessarily for display.

After each turn the bridge also emits (named into the existing `insight_*` family, so it lands in the event allowlist the consumer already filters on; unknown types are dropped today, so this is inert until it is rendered):

```json
{
  "type": "insight_answer_check",
  "required_statements": ["join-rule", "same-year"],
  "missing_statements": [{"id": "same-year", "statement": "...", "why": "..."}],
  "issues": [{"code": "sentence-too-long", "detail": [31]}],
  "substitutions": ["target cells"],
  "sentences_split": 1,
  "mean_sentence_words": 19.3
}
```

## What the producer already does

Wording that belongs to the plumbing is substituted before the answer leaves the bridge, and
over-long sentences are split at joins already present in the text. Neither pass invents content:
a missing required statement is reported, never written, because writing it would be authorship.

## What is being asked of the renderer

Show the statements. A short block beside the visual, in the producer's words, visibly not the
assistant's prose. Optionally use `answer_check.missing_statements` to mark the ones the prose did
not make — that is the honest version of a caveat chip, because it is the producer saying what the
answer owes the reader.

A result without `required_statements` renders exactly as it does today.
