#!/usr/bin/env python3
"""Build concise reviewer tables from immutable canonical run5 outputs."""
from __future__ import annotations

import argparse
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from scipy.stats import t
from sklearn.metrics import cohen_kappa_score, confusion_matrix

BOUNDED_0_1 = {
    "accuracy", "precision", "recall", "f1", "roc_auc", "pr_auc_benign",
    "pr_auc_ddos", "balanced_accuracy", "predicted_ddos_proportion",
}
HOLDOUT_METRICS = [
    "accuracy", "precision", "recall", "f1", "roc_auc", "pr_auc_ddos",
    "balanced_accuracy", "mcc",
]
MODEL_ORDER = ["xgboost", "rf", "mlp", "hybrid"]
FROZEN_SEEDS = {104729, 130363, 155921, 181081, 206369,
                231701, 257053, 282427, 307759, 333019}


def require_columns(frame: pd.DataFrame, columns: set[str], name: str) -> None:
    missing = columns - set(frame.columns)
    if missing:
        raise ValueError(f"{name} lacks required columns: {sorted(missing)}")


def markdown_table(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "_No rows._\n"

    def clean(value: object) -> str:
        return str(value).replace("|", "\\|").replace("\n", " ")

    header = "| " + " | ".join(clean(value) for value in frame.columns) + " |"
    separator = "| " + " | ".join("---" for _ in frame.columns) + " |"
    body = ["| " + " | ".join(clean(value) for value in row) + " |"
            for row in frame.itertuples(index=False, name=None)]
    return "\n".join([header, separator, *body]) + "\n"


def numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series.replace("not estimable", np.nan), errors="coerce")


def display_interval(values: pd.Series, metric: str, digits: int = 4) -> str:
    values = numeric(values).dropna().to_numpy(float)
    n = len(values)
    if n < 2:
        return "not estimable"
    mean = float(np.mean(values))
    sd = float(np.std(values, ddof=1))
    half = float(t.ppf(0.975, n - 1) * sd / np.sqrt(n))
    low, high = mean - half, mean + half
    if metric in BOUNDED_0_1:
        low, high = max(0.0, low), min(1.0, high)
    return (f"{mean:.{digits}f} ± {sd:.{digits}f} "
            f"(95% CI {low:.{digits}f}–{high:.{digits}f})")


def holdout_table(summary: pd.DataFrame) -> pd.DataFrame:
    require_columns(summary, {"feature_set", "model", "metric", "n_seeds",
                              "manuscript_value"}, "training statistics")
    if set(summary.n_seeds.astype(int)) != {10}:
        raise ValueError("Every hold-out summary must contain exactly 10 seeds")
    selected = summary[summary.metric.isin(HOLDOUT_METRICS)].copy()
    wide = selected.pivot(index=["feature_set", "model"], columns="metric",
                          values="manuscript_value").reset_index()
    wide["model"] = pd.Categorical(wide.model, MODEL_ORDER, ordered=True)
    wide = wide.sort_values(["feature_set", "model"])
    labels = {
        "feature_set": "Features", "model": "Classifier", "accuracy": "Accuracy",
        "precision": "Precision", "recall": "Recall", "f1": "F1",
        "roc_auc": "ROC-AUC", "pr_auc_ddos": "PR-AUC DDoS",
        "balanced_accuracy": "Balanced accuracy", "mcc": "MCC",
    }
    return wide.rename(columns=labels)[list(labels.values())]


def omnet_table(metrics: pd.DataFrame) -> pd.DataFrame:
    required = {"feature_set", "run", "scenario", "training_seed", "classifier",
                "evaluated_flows", "ground_truth_benign", "ground_truth_ddos",
                "predicted_ddos_proportion", "accuracy", "f1",
                "balanced_accuracy", "mcc"}
    require_columns(metrics, required, "OMNeT++ run/scenario metrics")
    for column in required - {"run", "scenario", "classifier"}:
        metrics[column] = numeric(metrics[column])
    per_run_rows = []
    metric_columns = ["accuracy", "f1", "balanced_accuracy", "mcc",
                      "predicted_ddos_proportion"]
    group_columns = ["feature_set", "classifier", "scenario", "run"]
    for keys, group in metrics.groupby(group_columns, sort=True):
        if group.training_seed.nunique() != 10:
            raise ValueError(f"OMNeT++ group {keys} does not contain 10 training seeds")
        count_columns = ["evaluated_flows", "ground_truth_benign", "ground_truth_ddos"]
        if any(group[column].nunique() != 1 for column in count_columns):
            raise ValueError(f"OMNeT++ truth/count columns vary by training seed for {keys}")
        row = dict(zip(group_columns, keys))
        row.update({column: float(group[column].iloc[0]) for column in count_columns})
        row.update({column: float(group[column].mean()) if group[column].notna().any()
                    else np.nan for column in metric_columns})
        per_run_rows.append(row)
    per_run = pd.DataFrame(per_run_rows)

    rows = []
    for (feature_set, classifier, scenario), group in per_run.groupby(
            ["feature_set", "classifier", "scenario"], sort=True):
        if group.run.nunique() != 10:
            raise ValueError(
                f"OMNeT++ {feature_set}/{classifier}/{scenario} lacks 10 simulation seeds")
        rows.append({
            "Features": int(feature_set), "Classifier": classifier,
            "Scenario": scenario, "Simulation seeds": 10, "Training seeds/model": 10,
            "Unique flows": int(group.evaluated_flows.sum()),
            "BENIGN": int(group.ground_truth_benign.sum()),
            "DDoS": int(group.ground_truth_ddos.sum()),
            "Predicted DDoS proportion": display_interval(
                group.predicted_ddos_proportion, "predicted_ddos_proportion"),
            "Accuracy": display_interval(group.accuracy, "accuracy"),
            "F1": display_interval(group.f1, "f1"),
            "Balanced accuracy": display_interval(group.balanced_accuracy,
                                                    "balanced_accuracy"),
            "MCC": display_interval(group.mcc, "mcc"),
        })
    result = pd.DataFrame(rows)
    result["Classifier"] = pd.Categorical(result["Classifier"], MODEL_ORDER, ordered=True)
    return result.sort_values(["Features", "Classifier", "Scenario"])


def paired_table(paired: pd.DataFrame, comparison_type: str,
                 metrics: set[str], feature8_only: bool = False) -> pd.DataFrame:
    required = {"comparison_type", "stratum", "metric", "left", "right",
                "matched_seeds", "mean_difference_left_minus_right",
                "difference_ci95_low", "difference_ci95_high", "p_holm",
                "significant_after_holm_0.05", "status"}
    require_columns(paired, required, "paired comparisons")
    view = paired[(paired.comparison_type == comparison_type) &
                  paired.metric.isin(metrics)].copy()
    if feature8_only:
        view = view[pd.to_numeric(view.stratum, errors="coerce").eq(8)]
    if set(pd.to_numeric(view.matched_seeds, errors="raise").astype(int)) != {10}:
        raise ValueError("Selected paired comparisons are not all based on 10 matched seeds")
    if set(view.status) != {"tested"}:
        raise ValueError("Selected paired comparisons include an untested row")

    def format_difference(row: pd.Series) -> str:
        return (f"{float(row.mean_difference_left_minus_right):.5f} "
                f"(95% CI {float(row.difference_ci95_low):.5f}–"
                f"{float(row.difference_ci95_high):.5f})")

    return pd.DataFrame({
        "Stratum": view.stratum, "Metric": view.metric, "Left": view.left,
        "Right": view.right, "Matched seeds": view.matched_seeds.astype(int),
        "Mean difference (left−right)": view.apply(format_difference, axis=1),
        "Holm-adjusted p": numeric(view.p_holm).map(lambda value: f"{value:.4g}"),
        "Significant after Holm": view["significant_after_holm_0.05"],
    }).reset_index(drop=True)


def consensus_confusion(predictions: pd.DataFrame) -> pd.DataFrame:
    required = {"sample_id", "feature_set", "training_seed", "classifier",
                "y_true", "y_pred", "score"}
    require_columns(predictions, required, "OMNeT++ flow predictions")
    data = predictions[predictions.feature_set.eq(8)].copy()
    rows = []
    for classifier, model_data in data.groupby("classifier", sort=True):
        consensus_rows = []
        for sample_id, group in model_data.groupby("sample_id", sort=False):
            if group.training_seed.nunique() != 10 or group.y_true.nunique() != 1:
                raise ValueError(f"Feature-8 consensus is not based on 10 aligned seeds: {sample_id}")
            votes = int(group.y_pred.sum())
            prediction = int(votes > 5 or (votes == 5 and group.score.mean() >= 0.5))
            consensus_rows.append((int(group.y_true.iloc[0]), prediction))
        truth = np.array([item[0] for item in consensus_rows], dtype=int)
        predicted = np.array([item[1] for item in consensus_rows], dtype=int)
        tn, fp, fn, tp = confusion_matrix(truth, predicted, labels=[0, 1]).ravel()
        rows.append({
            "Features": 8, "Classifier": classifier,
            "Training-seed aggregation":
                "majority consensus across 10 seeds; mean score breaks 5–5 ties",
            "Unique flows": len(truth), "BENIGN": int((truth == 0).sum()),
            "DDoS": int((truth == 1).sum()), "TN": int(tn), "FP": int(fp),
            "FN": int(fn), "TP": int(tp),
        })
    result = pd.DataFrame(rows)
    result["Classifier"] = pd.Categorical(result.Classifier, MODEL_ORDER, ordered=True)
    return result.sort_values("Classifier")


def agreement_table(predictions: pd.DataFrame) -> pd.DataFrame:
    required = {"sample_id", "feature_set", "training_seed", "classifier", "y_pred"}
    require_columns(predictions, required, "OMNeT++ flow predictions")
    rows = []
    for (feature_set, seed), group in predictions.groupby(["feature_set", "training_seed"]):
        indexed = {name: part.set_index("sample_id").sort_index()
                   for name, part in group.groupby("classifier")}
        if set(indexed) != set(MODEL_ORDER):
            raise ValueError(f"Missing classifier for agreement feature={feature_set}, seed={seed}")
        for left, right in combinations(MODEL_ORDER, 2):
            if not indexed[left].index.equals(indexed[right].index):
                raise ValueError("OMNeT++ agreement attempted on unmatched flows")
            a = indexed[left].y_pred.to_numpy(int)
            b = indexed[right].y_pred.to_numpy(int)
            rows.append({"feature_set": feature_set, "seed": seed, "left": left,
                         "right": right, "agreement": np.mean(a == b),
                         "kappa": cohen_kappa_score(a, b)})
    seedwise = pd.DataFrame(rows)
    output = []
    for (feature_set, left, right), group in seedwise.groupby(
            ["feature_set", "left", "right"], sort=True):
        if group.seed.nunique() != 10:
            raise ValueError("Agreement summary does not contain 10 training seeds")
        output.append({
            "Features": int(feature_set), "Classifier A": left, "Classifier B": right,
            "Training seeds": 10,
            "Agreement": display_interval(group.agreement, "accuracy"),
            "Cohen's kappa": display_interval(group.kappa, "mcc"),
            "Agreement with ensemble": "yes" if "hybrid" in {left, right} else "no",
        })
    return pd.DataFrame(output)


def mcnemar_summary(frame: pd.DataFrame) -> pd.DataFrame:
    required = {"seed", "left_feature_set", "left_model", "right_feature_set",
                "right_model", "matched_observations", "discordant", "status",
                "mcnemar_p_holm", "significant_after_holm_0.05"}
    require_columns(frame, required, "McNemar results")
    view = frame[(frame.left_feature_set.eq(8)) & (frame.right_feature_set.eq(8))].copy()
    if set(view.status) != {"tested"}:
        raise ValueError("Feature-8 McNemar summary contains unmatched/untested comparisons")
    rows = []
    for (left, right), group in view.groupby(["left_model", "right_model"], sort=True):
        if group.seed.nunique() != 10 or len(group) != 10:
            raise ValueError("Feature-8 McNemar pair does not contain 10 seedwise tests")
        significant = group["significant_after_holm_0.05"].astype(str).str.lower().eq("true")
        rows.append({
            "Features": 8, "Classifier A": left, "Classifier B": right,
            "Matched seedwise tests": 10,
            "Matched observations/test (min–max)":
                f"{int(group.matched_observations.min())}–{int(group.matched_observations.max())}",
            "Total discordant predictions": int(group.discordant.sum()),
            "Holm-significant tests": int(significant.sum()),
            "Median Holm-adjusted p": f"{numeric(group.mcnemar_p_holm).median():.4g}",
        })
    return pd.DataFrame(rows)


def write_supplementary_index(path: Path, sources: dict[str, Path]) -> None:
    rows = []
    for description, source in sources.items():
        row_count = (sum(1 for _ in source.open(encoding="utf-8")) - 1
                     if source.suffix.lower() == ".csv"
                     else pq.ParquetFile(source).metadata.num_rows)
        rows.append({"Supplementary evidence": description,
                     "Canonical relative path": source.as_posix(), "Rows": row_count})
    text = (
        "# Supplementary seed-level evidence index\n\n"
        "All entries are canonical run5 outputs. Detailed seed-level rows remain in their "
        "machine-readable source files and were not copied into the concise main tables.\n\n"
        + markdown_table(pd.DataFrame(rows))
        + "\nThe hold-out prediction table uses identical sample IDs within each training "
          "seed across feature sets and model families. OMNeT++ rows use per-flow ground "
          "truth and never infer labels from scenario names.\n")
    path.write_text(text, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--training-statistics", required=True, type=Path)
    parser.add_argument("--training-metrics", required=True, type=Path)
    parser.add_argument("--training-predictions", required=True, type=Path)
    parser.add_argument("--omnet-run-metrics", required=True, type=Path)
    parser.add_argument("--omnet-predictions", required=True, type=Path)
    parser.add_argument("--paired-comparisons", required=True, type=Path)
    parser.add_argument("--mcnemar", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--supplementary-output", required=True, type=Path)
    args = parser.parse_args()
    for output in (args.output, args.supplementary_output):
        if output.exists():
            raise FileExistsError(f"Refusing to overwrite existing table: {output}")
        output.parent.mkdir(parents=True, exist_ok=True)

    training_summary = pd.read_csv(args.training_statistics)
    training_metrics = pd.read_csv(args.training_metrics)
    omnet_metrics = pd.read_csv(args.omnet_run_metrics)
    omnet_predictions = pd.read_csv(args.omnet_predictions)
    paired = pd.read_csv(args.paired_comparisons)
    mcnemar = pd.read_csv(args.mcnemar)

    if len(training_metrics) != 120 or training_metrics.duplicated(
            ["feature_set", "seed", "model"]).any():
        raise ValueError("Training metrics are incomplete or contain duplicate experiment keys")
    if set(training_metrics.seed) != FROZEN_SEEDS:
        raise ValueError("Training metrics do not use the frozen ten-seed set")

    main_holdout = holdout_table(training_summary)
    main_omnet = omnet_table(omnet_metrics)
    sensitivity = paired_table(paired, "feature_set", {"accuracy", "f1"})
    comparisons = paired_table(paired, "model", {"accuracy", "f1"}, feature8_only=True)
    confusion = consensus_confusion(omnet_predictions)
    agreement = agreement_table(omnet_predictions)
    mcnemar_view = mcnemar_summary(mcnemar)

    text = (
        "# Canonical run5 manuscript-ready tables\n\n"
        "These concise tables use only the verified OMNeT++ 6.0.3 / INET 4.5.4 "
        "run5 campaign and the frozen ten-seed CICDDoS2019 experiment. They do not "
        "select a favorable training seed. For [0,1]-bounded metrics, displayed "
        "mean-based t-interval endpoints are constrained to [0,1]; raw endpoints are "
        "retained in the timestamped statistical CSV. Means, SDs, seed measurements, "
        "MCC, paired differences, predictions, and tests are unchanged.\n\n"
        "## Main hold-out comparison\n\n"
        "Aggregation: mean ± sample SD and two-sided 95% t CI across n=10 independent "
        "source-group-aware splits for every feature-set/classifier row.\n\n"
        + markdown_table(main_holdout)
        + "\n## OMNeT++ cross-environment results by scenario\n\n"
        "Aggregation: n=10 canonical simulation seeds per scenario. Within each "
        "simulation seed, each metric is first averaged across all n=10 trained-seed "
        "models; the displayed mean, SD, and 95% t CI are then calculated across the "
        "10 simulation seeds. `Unique flows` counts each canonical flow once and is not "
        "multiplied by training seeds. Undefined single-class metrics remain `not "
        "estimable`.\n\n"
        + markdown_table(main_omnet)
        + "\n## Feature sensitivity\n\n"
        "Each row compares the same n=10 seed splits. Differences are left minus right; "
        "difference intervals are unbounded and therefore are not clipped. Holm p values "
        "come from the complete 270-comparison family.\n\n"
        + markdown_table(sensitivity)
        + "\n## Principal feature-8 classifier comparisons\n\n"
        "Each row uses n=10 matched seed splits. Holm p values come from the complete "
        "270-comparison family.\n\n"
        + markdown_table(comparisons)
        + "\n## Feature-8 OMNeT++ consensus confusion matrices\n\n"
        "Aggregation: all 10,312 unique canonical run5 flows. For each classifier, the "
        "prediction is the majority across all n=10 training-seed models; a 5–5 tie is "
        "resolved by the mean score. No training seed is selected.\n\n"
        + markdown_table(confusion)
        + "\n## OMNeT++ classifier agreement\n\n"
        "Aggregation: agreement and Cohen's kappa are calculated on the same 10,312 "
        "canonical flows for each training seed, then summarized across n=10 training "
        "seeds.\n\n"
        + markdown_table(agreement)
        + "\n## Matched McNemar summary for feature 8\n\n"
        "Each classifier pair has 10 exact, seedwise McNemar tests on identical hold-out "
        "sample IDs. Holm adjustment was applied over the complete 660-test family. "
        "Unmatched observations are never tested.\n\n"
        + markdown_table(mcnemar_view)
        + "\nDetailed seed-level outputs are indexed in the timestamped supplementary file.\n")
    if "run4" in text.lower():
        raise ValueError("Noncanonical run4 text must not enter manuscript tables")
    args.output.write_text(text, encoding="utf-8")

    write_supplementary_index(args.supplementary_output, {
        "Hold-out seed metrics": args.training_metrics,
        "Matched hold-out predictions": args.training_predictions,
        "OMNeT++ run/scenario metrics": args.omnet_run_metrics,
        "OMNeT++ per-flow predictions": args.omnet_predictions,
        "Paired feature/model comparisons": args.paired_comparisons,
        "Matched Holm-corrected McNemar tests": args.mcnemar,
    })
    print(f"Wrote {args.output} and {args.supplementary_output}")


if __name__ == "__main__":
    main()
