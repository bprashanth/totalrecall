# TR-VIS-0003 — Show how an open phrase was read

Some phrases are stored names. Some are categories declared by a source. Others are ordinary
collective words whose members require interpretation. These must not look identical.

The producer now returns a model-selected subject in the ordinary result binding:

```json
{
  "requested": "public works",
  "kind": "selected_group",
  "label": "public works",
  "member_labels": ["Footpath repair", "Check dam construction"],
  "resolution_method": "model_selected",
  "selector": {
    "model": "configured-dialogue-model",
    "prompt_version": "site-subject-selection/2"
  },
  "binding_id": "binding-…"
}
```

Every member id was selected from the bounded catalogue and verified by the producer. That makes
the mapping runnable; it does not turn the interpretation into a source-defined category.

## Requested presentation

Beside the visual, show one short disclosure:

> Read “public works” as Footpath repair and Check dam construction · assistant interpretation

The words and members come from the binding. `selector` and `binding_id` belong in the expanded
audit view. The distinction must have a text or icon label, not colour alone.

The result also carries a normal `choice` action labelled “Change what … includes”. Its supplied
`capability_id` and `arguments` deliberately reopen the bounded catalogue, even when a cached
binding exists. The consumer should invoke that action through the conversation route; it should
not build its own entity resolver or edit the result in place.

Exact stored names and groups declared by a source do not carry `model_selected`, so they need no
interpretation warning. Old results remain unchanged.
