# Visual-ready AOI index prototype

This directory is the dependency-light feasibility implementation for the companion Idlisseus
design,
[`VISUAL_FIRST_AOI_DATA_DESIGN.md`](../../../idlisseus/docs/VISUAL_FIRST_AOI_DATA_DESIGN.md).
It proves the logical tables and visual-view contracts against a maintained site pack. The
deployment-pinned bridge integration is documented in
[`../SITE_PACK_DEPLOYMENT.md`](../SITE_PACK_DEPLOYMENT.md).

Build:

```bash
python3 dss/visual_index/build.py \
  --site-pack dss/sites/valparai \
  --output /tmp/valparai-visual-index
```

Outputs:

- `site_index.sqlite` — canonical facts and materialised aggregates;
- `visual_bundle.json` — data for the tested visual contracts;
- `preview.png` — one static feasibility preview; and
- `build_report.json` — counts, elapsed build time and integrity result.

Run the regression tests:

```bash
python3 -m unittest dss.visual_index.tests.test_build -v
```

The code intentionally uses the Python standard library and Pillow already present on this host.
It is a proof of the logical contract, not a recommendation to use SQLite as the production
warehouse.
