# TR-VIS-0001 — field-declared matrix dimensions

The producer emits tidy matrix rows such as:

```json
{
  "category": "Group A",
  "x": "08",
  "y": 3000,
  "value": 0.42,
  "series": 12,
  "unit": "scaled activity"
}
```

The layer tells the consumer how to interpret those names:

```json
{
  "style_hint": {
    "facet_field": "category",
    "x_field": "x",
    "y_field": "y",
    "value_field": "value",
    "coverage_field": "series"
  }
}
```

The renderer should use the declared fields instead of requiring the producer to rename a
scientific or programme dimension to `row` and `col`. This keeps the wire grammar generic and
allows a matrix to represent time × frequency, age × service, village × indicator, or any other
two-dimensional result without a renderer fork.
