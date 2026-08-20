# Frozen model artifacts: inventory and regeneration

The canonical trained-model payload is **not included** in this candidate
release. Redistribution is not approved by this release, and the
source directory also contains large row-level split/prediction artifacts that
are unsuitable for ordinary Git history.

The complete 245-file inventory is
`evidence/model_inventory/MODEL_ARTIFACT_INVENTORY.csv`. It records every
source filename, size, SHA-256, role, model family, feature set, training seed,
feature order, preprocessing dependency, expected environment, loading method,
and release status. The inventory comprises:

- 90 joblib pipelines required for inference: XGBoost, Random Forest, and MLP
  for 3 feature sets × 10 seeds;
- 30 hybrid metadata files that reference the three component pipelines;
- 90 per-model metadata files with exact hyperparameters and feature order;
- 30 split-ID CSV files required for exact verification but containing
  dataset-derived row identifiers;
- environment and aggregate metric files; and
- the large hold-out prediction and training-metadata payloads.

## Expected layout for an authorized local copy

```text
artifacts/models/max-benign-run5-inet454/
  environment_versions.json
  seed_metrics.csv
  test_predictions.parquet
  feature4/
    xgboost-seed104729.joblib
    rf-seed104729.joblib
    mlp-seed104729.joblib
    hybrid-seed104729.metadata.json
    ... all ten seeds ...
  feature6/
  feature8/
```

Do not commit payloads over GitHub's ordinary per-file limit to repository
history. Redistribution is outside this release's approved scope. If the
authors and institution later authorize separate distribution, use versioned
release assets or Zenodo files, record each bundle hash, and verify that
extracted files match the inventory.

## Regeneration

After locally preparing the user-supplied dataset, run the long ten-seed job
with a new output directory:

```bash
./.venv-final/Scripts/python.exe scripts/train_models.py \
  --data work/prepared/cicddos2019-max-benign-feature8.parquet \
  --split-manifest work/prepared/split_manifest.parquet \
  --preparation-validation work/prepared/preparation_validation.json \
  --output-dir artifacts/models/max-benign-reproduction-v1 \
  --feature-sets 4 6 8 \
  --seeds 104729 130363 155921 181081 206369 231701 257053 282427 307759 333019
```

This is long-running. It creates new artifacts and must not target the
canonical name.

## Loading

XGBoost and RF pipelines use `joblib.load(path)`. The saved preprocessing
`StandardScaler` is embedded in each pipeline. SciKeras MLP objects were
serialized from a script and refer to `__main__.keras_mlp`; use
`scripts/evaluate_omnet.py`, which registers the compatible factory before
loading, or register the exact same callable in an external loader.

Frozen model payloads are not redistributed in this release. The included
Figure 6 was generated and validated from the locally retained frozen
feature-8 XGBoost artifact trained with seed 104729 (SHA-256:
`c7bda804520817d02357cdb3c259a531652f3e99355fac4e3b52b0bae178f122`).
The clean-candidate generation utility loaded that exact artifact under the
pinned Python 3.10.5 stack and verified its identity, feature order, and seed.
Independent regeneration requires an authorized copy of that exact artifact;
the utility does not substitute another model. The remaining excluded payloads
were not release load-tested, and hashes or metadata do not imply that model
payloads are present.

Expected aggregate performance is documented in `CANONICAL_RESULTS.md`,
`evidence/training/seed_metrics.csv`, and
`evidence/statistics/metrics_mean_sd_95ci.csv`.
