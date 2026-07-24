# 2024 cell-aligned Earth-observation feature cube

This directory is a reproducible derived input, not a field-observation source and not a fitted
distribution model.

`cell_features_2024.csv` contains long-form values aligned to the 302 cells in the Valparai visual
index. `manifest.json` declares every input asset, feature, unit, evidence class, aggregation,
support gap, limitation and the CSV digest. The file was generated with:

```bash
python3 dss/visual_index/acquire_earth_observation_cube.py \
  --index /tmp/valparai-visual-index/site_index.sqlite \
  --output-dir dss/sites/valparai/derived/earth_observation_2024 \
  --year 2024 \
  --scale-m 100 \
  --tile-scale 4
```

The script uses the caller's normal Earth Engine authentication. It never copies credentials into
the output.

The 64 AlphaEarth axes must be used together and normalised after cell aggregation when cosine
similarity is required. Dynamic World values are class scores rather than measured cover.
ERA5-Land and CHIRPS are substantially coarser than the serving cells. Missing cloudy-season
Sentinel-2 values remain missing; they are not filled or silently converted to zero.
