# Supplementary seed-level evidence index

All entries are canonical run5 outputs. Detailed seed-level rows remain in their machine-readable source files and were not copied into the concise main tables.

| Supplementary evidence | Canonical relative path | Rows |
| --- | --- | --- |
| Hold-out seed metrics | models/max-benign-run5-inet454/seed_metrics.csv | 120 |
| Matched hold-out predictions | models/max-benign-run5-inet454/test_predictions.parquet | 5225664 |
| OMNeT++ run/scenario metrics | reports/omnet/max-benign-run5-inet454/run_scenario_metrics.csv | 4800 |
| OMNeT++ per-flow predictions | reports/omnet/max-benign-run5-inet454/flow_predictions.csv | 1237440 |
| Paired feature/model comparisons | reports/statistics/max-benign-run5-inet454-ci-bounded-20260819T150411/paired_feature_and_model_comparisons.csv | 270 |
| Matched Holm-corrected McNemar tests | reports/statistics/max-benign-run5-inet454-ci-bounded-20260819T150411/paired_mcnemar.csv | 660 |

The hold-out prediction table uses identical sample IDs within each training seed across feature sets and model families. OMNeT++ rows use per-flow ground truth and never infer labels from scenario names.
