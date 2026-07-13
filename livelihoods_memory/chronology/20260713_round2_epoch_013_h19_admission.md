# Round 2 epoch 013 — H19 admission boundary

## Independent generation

H19 was authored after the epoch-013 freeze by Cursor Agent using `gemini-3.1-pro`, a
Google-family generator not used for H18. The author could inspect the frozen v2.1 algebra,
schema, connector vocabulary, source census, coverage snapshot, Round 2 protocol, and freeze
manifest. It could not inspect parser/scorer code, prior questions, runs, traces, compiled corpus,
or repair history. It produced 64 candidates (`h19-001` through `h19-064`) without parser contact.

The main judge audited all candidates and their executable denotations. An independent blind
judge audited rows 33–64 against the schema, connector contract, and coverage gaps. Admission
favored sparse distance, nested relation, mixed-source comparison, rank-of-comparisons,
rank-of-relational-counts, ambiguity, and explicit-source-gap forms over repeated simple controls.

## Pre-run adjudication

Twenty-four candidates were excluded before first parser contact:

- `h19-021`, `h19-022`, `h19-023`, `h19-024`, `h19-033`, `h19-045`, and `h19-053` use
  `ESTIMATE` on Series even though frozen v2.1 requires Records.
- `h19-025` and `h19-026` ask ANNOTATE to invent statistical fields absent from the selected OSM
  records; `h19-048` similarly encodes computed distance as a free-form annotation.
- `h19-030`, `h19-043`, and `h19-055` choose a ratio for bare “compare” wording without enough
  evidence to distinguish ratio from difference.
- `h19-042` silently interprets “urban population” as a percentage share and chooses an absolute
  percentage-point change for ambiguous “grow”.
- `h19-057` and `h19-062` request historical change from current-snapshot OSM records. The
  symbolic executor currently returns an answer instead of failing closed, so these remain
  framework breakers under proposal `SRC-001`; flexible expectation metadata was explicitly
  rejected as a way to hide the evidence defect.
- `h19-059` uses an unstable fictional-place assumption, `h19-060` subtracts incompatible units,
  and `h19-063` is both incomplete and ill-typed (`ESTIMATE` cannot yield the requested count).
- `h19-001`, `h19-003`, `h19-004`, `h19-039`, and `h19-051` were low-novelty or semantically weak
  controls removed after the invalid candidates.

Pre-contact repairs were gold-only and disclosed: mechanically redundant mean wrappers around
Series SELECTs were removed; `h19-034` was represented as the existing binary distance RELATE;
`h19-047` retained only the two missing places because absent time means the available series, not
an invented time hole; and explicitly named unsupported entities were marked as source gaps
without semantic holes. Nine valid OSM/ILOSTAT questions use `answer_or_data_request` because
bounded or sparse live coverage can legitimately vary without changing their denotation. No
parser, prompt, scorer, repair, connector, executor, or synthesis code changed.

## Frozen bank

The admitted bank is `questions/holdout-019.json`: 40 rows comprising 12 relation, 12 state,
10 change, 2 trend, 2 value, and 2 ambiguity cases. Its expectation mix is 22 answer,
9 answer-or-data-request, and 9 data-request rows. SHA-256:
`fc4df34c1335d350ac3eb25b529b7377443da16bf90a4abf72883bfd89076d38`.

This checksum is the immutable pre-contact boundary. Any bank/gold edit or any parser, prompt,
scorer, connector, executor, repair, or synthesis change invalidates H19 and epoch 013. If H19 has
no valid post-contact discovery, it is only untouched saturation pass 1 of the required 3.
