# Publication figure provenance

## Figures 1–4 — author-created manuscript artwork

Figures 1–4 are the exact media objects embedded in the final manuscript. They
are original author-created diagrams or screenshots and carry no third-party
attribution. The per-figure `CAPTION.txt` and provenance JSON files preserve the
exact manuscript caption and identify the originating DOCX media part and
SHA-256. Figure 4 is an optional Flask demonstration screenshot; it was not
used to generate canonical run5 results. Visual inspection found no credentials,
private paths, or confidential user data in these four figures.

- Figure 1: `figure1/figure1_pipeline.jpeg`
- Figure 2: `figure2/figure2_feature_selection.png`
- Figure 3: `figure3/figure3_omnet_topology.jpeg`
- Figure 4: `figure4/figure4_flask_interface.jpeg`

Both figures were generated on 2026-08-20 with the isolated Python 3.10.5
validation runtime and the package's pinned scientific versions. Neither
simulation, preparation, extraction, training, prediction, nor statistical
analysis was rerun. First-pass PNGs with overlapping headings were retained
outside the release as audit evidence; only layout was changed before the
validated renders below were regenerated.

## Figure 5 — matched ten-seed ROC summary

Input: frozen canonical
`models/max-benign-run5-inet454/test_predictions.parquet`, SHA-256
`142d07b117619de2e00740d7e36264e8b70233cce959f69a9495f7a23fe17da3`.
Feature set 8, all four model families, and all ten frozen seeds were used; no
seed was selected or omitted. A ROC curve was calculated within each matched
seed/model cell, TPR was linearly interpolated onto a 1,001-point common FPR
grid, and the displayed curve is the seed mean. Shading is ±1 sample SD of TPR
and is constrained to [0,1] for display only. The legend reports mean ROC-AUC
± sample SD; the CSV also reports the two-sided mean-based t interval with
displayed endpoints bounded to [0,1]. Run4 is excluded.

- PNG: `figure5/figure5_roc_summary.png`
- vector: `figure5/figure5_roc_summary.svg`
- aggregate data: `figure5/figure5_roc_curves.csv` and
  `figure5/figure5_roc_summary.csv`
- metadata: `figure5/figure5_metadata.json`

## Figure 6 — selected classifier TreeSHAP summary

Figure 6. SHAP summary for the frozen canonical feature-8 XGBoost model
trained with seed 104729. Seed 104729 was selected as the first seed in the
predefined numerically ordered frozen seed list, independently of model
performance.

- model family: XGBoost
- feature set: 8
- training seed: 104729
- selection rule: first seed in the predefined numerically ordered frozen seed
  list; not selected by accuracy, ROC-AUC, OMNeT++ agreement, SHAP appearance,
  or any favorable-result criterion
- artifact: `models/max-benign-run5-inet454/feature8/xgboost-seed104729.joblib`
- artifact SHA-256:
  `c7bda804520817d02357cdb3c259a531652f3e99355fac4e3b52b0bae178f122`
- features, in frozen order: Total Fwd Packets; Total Backward Packets; Flow
  Bytes/s; Flow Packets/s; Flow Duration; Total Length of Fwd Packets; Total
  Length of Bwd Packets; Fwd Packet Length Mean
- explainer: XGBoost 2.1.1 native exact TreeSHAP through
  `Booster.predict(pred_contribs=True)` on the saved pipeline's
  StandardScaler output
- represented class: DDoS (positive class 1), in binary raw-margin/log-odds
  units
- background: no external background sample; native tree-path-dependent
  expectation encoded by the fitted booster
- evaluation sample: 10,000 rows from the frozen seed-104729 hold-out IDs,
  selected without replacement by ascending SHA-256 of
  `104729:sample_id`
- software: Python 3.10.5; numpy 1.26.4; pandas 2.2.3; pyarrow 17.0.0;
  joblib 1.4.2; scikit-learn 1.5.2; XGBoost 2.1.1
- PNG: `figure6/figure6_shap_summary.png`
- vector: `figure6/figure6_shap_summary.svg`
- aggregate data: `figure6/figure6_shap_summary.csv`
- machine-readable provenance: `figure6/figure6_provenance.json`

Figure 6 explains the selected classifier's predictions only. It does not
establish simulator realism or fidelity.
## Figure 7 — Full-feature CICDDoS2019 TreeSHAP importance

**Manuscript figure:** Figure 7

**Figure file:**  
`figures/figure7/full_feature_shap_top20.png`

**Generation script:**  
`scripts/full_feature_analysis.py`

**Supporting outputs:**  
- `evidence/full_feature_importance/full_feature_shap_ranking.csv`
- `evidence/full_feature_importance/cross_environment_feature_ranks.csv`
- `evidence/full_feature_importance/full_feature_metrics.json`

**Description:**  
XGBoost feature-importance analysis performed on the complete eligible
CICDDoS2019 predictor space. The original source files contained 88 columns.
After excluding the class label and non-predictive identifier/metadata
fields, 79 eligible predictors were evaluated. Mean absolute TreeSHAP
contributions were used to rank predictor importance.
