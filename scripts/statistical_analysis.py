#!/usr/bin/env python3
"""Matched multi-seed feature/model comparisons with corrected inference."""
from __future__ import annotations

import argparse
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import binomtest, t, ttest_rel

METRICS = ["accuracy", "precision", "recall", "f1", "roc_auc", "pr_auc_benign",
           "pr_auc_ddos", "balanced_accuracy", "mcc"]
BOUNDED_0_1_METRICS = frozenset({
    "accuracy", "precision", "recall", "f1", "roc_auc", "pr_auc_benign",
    "pr_auc_ddos", "balanced_accuracy",
})


def holm_adjust(pvalues: list[float]) -> list[float]:
    """Holm family-wise correction, retaining NaN for tests not performed."""
    result = np.full(len(pvalues), np.nan)
    valid = [(index, value) for index, value in enumerate(pvalues) if np.isfinite(value)]
    ordered = sorted(valid, key=lambda pair: pair[1])
    running = 0.0
    m = len(ordered)
    for rank, (index, value) in enumerate(ordered):
        running = max(running, (m - rank) * value)
        result[index] = min(1.0, running)
    return result.tolist()


def summarize(metrics: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (feature_set, model), group in metrics.groupby(["feature_set", "model"]):
        for metric in METRICS:
            values = pd.to_numeric(group[metric], errors="coerce").dropna().to_numpy(float)
            n = len(values)
            mean = np.mean(values) if n else np.nan
            sd = np.std(values, ddof=1) if n > 1 else np.nan
            half = t.ppf(0.975, n - 1) * sd / np.sqrt(n) if n > 1 else np.nan
            raw_low = mean - half
            raw_high = mean + half
            if metric in BOUNDED_0_1_METRICS and n > 1:
                display_low = max(0.0, raw_low)
                display_high = min(1.0, raw_high)
                constrained = display_low != raw_low or display_high != raw_high
            else:
                display_low, display_high, constrained = raw_low, raw_high, False
            rows.append({"feature_set": feature_set, "model": model, "metric": metric,
                         "n_seeds": n, "mean": mean, "sd": sd,
                         "ci95_method": "two-sided mean t interval, df=n-1",
                         "ci95_low_raw": raw_low, "ci95_high_raw": raw_high,
                         "ci95_low": display_low, "ci95_high": display_high,
                         "ci95_display_constrained_to_0_1": constrained,
                         "manuscript_value": (f"{mean:.4f} ± {sd:.4f} "
                                              f"(95% CI {display_low:.4f}–{display_high:.4f})"
                                              if n > 1 else "not estimable")})
    return pd.DataFrame(rows)


def paired_metric_tests(metrics: pd.DataFrame) -> pd.DataFrame:
    rows = []
    # Feature-set comparisons: paired on seed within each model.
    for model, model_data in metrics.groupby("model"):
        for left, right in combinations(sorted(model_data.feature_set.unique()), 2):
            for metric in METRICS:
                wide = model_data.pivot(index="seed", columns="feature_set", values=metric)
                pair = wide[[left, right]].apply(pd.to_numeric, errors="coerce").dropna()
                rows.append(_paired_row("feature_set", model, metric, left, right, pair))
    # Model comparisons: paired on seed within each feature set.
    for feature_set, feature_data in metrics.groupby("feature_set"):
        for left, right in combinations(sorted(feature_data.model.unique()), 2):
            for metric in METRICS:
                wide = feature_data.pivot(index="seed", columns="model", values=metric)
                pair = wide[[left, right]].apply(pd.to_numeric, errors="coerce").dropna()
                rows.append(_paired_row("model", feature_set, metric, left, right, pair))
    frame = pd.DataFrame(rows)
    frame["p_holm"] = holm_adjust(frame["paired_t_p"].tolist())
    frame["significant_after_holm_0.05"] = frame["p_holm"] < 0.05
    return frame


def _paired_row(comparison_type: str, stratum: object, metric: str,
                left: object, right: object, pair: pd.DataFrame) -> dict[str, object]:
    n = len(pair)
    differences = pair[left].to_numpy(float) - pair[right].to_numpy(float) if n else np.array([])
    mean = np.mean(differences) if n else np.nan
    sd = np.std(differences, ddof=1) if n > 1 else np.nan
    half = t.ppf(0.975, n - 1) * sd / np.sqrt(n) if n > 1 else np.nan
    pvalue = ttest_rel(pair[left], pair[right]).pvalue if n > 1 else np.nan
    return {"comparison_type": comparison_type, "stratum": stratum, "metric": metric,
            "left": left, "right": right, "matched_seeds": n,
            "mean_difference_left_minus_right": mean,
            "difference_ci95_low": mean - half, "difference_ci95_high": mean + half,
            "paired_t_p": pvalue,
            "status": "tested" if n > 1 else "not estimable: fewer than two matched seeds"}


def mcnemar_tests(predictions: pd.DataFrame) -> pd.DataFrame:
    required = {"feature_set", "seed", "sample_id", "model", "y_true", "y_pred"}
    missing = required - set(predictions.columns)
    if missing:
        raise ValueError(f"Prediction table lacks matched-test columns: {sorted(missing)}")
    rows = []
    for seed, seed_data in predictions.groupby("seed"):
        experiments = sorted(set(zip(seed_data.feature_set, seed_data.model)))
        indexed = {}
        for experiment in experiments:
            feature_set, model = experiment
            subset = seed_data[(seed_data.feature_set == feature_set) &
                               (seed_data.model == model)].set_index("sample_id")
            if subset.index.duplicated().any():
                raise ValueError(f"Duplicate prediction IDs for seed={seed}, experiment={experiment}")
            indexed[experiment] = subset
        for left, right in combinations(experiments, 2):
            left_data, right_data = indexed[left], indexed[right]
            matched = left_data.index.equals(right_data.index)
            if not matched:
                matched = set(left_data.index) == set(right_data.index)
                if matched:
                    right_data = right_data.reindex(left_data.index)
            if not matched or not np.array_equal(left_data.y_true.to_numpy(),
                                                  right_data.y_true.to_numpy()):
                rows.append({"seed": seed, "left_feature_set": left[0], "left_model": left[1],
                             "right_feature_set": right[0], "right_model": right[1],
                             "matched_observations": 0, "status": "not tested: unmatched samples",
                             "mcnemar_exact_p": np.nan})
                continue
            truth = left_data.y_true.to_numpy(int)
            left_error = left_data.y_pred.to_numpy(int) != truth
            right_error = right_data.y_pred.to_numpy(int) != truth
            left_only_error = int(np.sum(left_error & ~right_error))
            right_only_error = int(np.sum(~left_error & right_error))
            discordant = left_only_error + right_only_error
            pvalue = (binomtest(min(left_only_error, right_only_error), discordant, 0.5).pvalue
                      if discordant else 1.0)
            paired_error_difference = left_error.astype(float) - right_error.astype(float)
            mean = float(paired_error_difference.mean())
            sd = float(paired_error_difference.std(ddof=1)) if len(truth) > 1 else np.nan
            half = 1.96 * sd / np.sqrt(len(truth)) if len(truth) > 1 else np.nan
            rows.append({"seed": seed, "left_feature_set": left[0], "left_model": left[1],
                         "right_feature_set": right[0], "right_model": right[1],
                         "matched_observations": len(truth),
                         "left_error_right_correct": left_only_error,
                         "left_correct_right_error": right_only_error,
                         "discordant": discordant, "mcnemar_exact_p": pvalue,
                         "paired_error_difference_left_minus_right": mean,
                         "error_difference_ci95_low": mean - half,
                         "error_difference_ci95_high": mean + half, "status": "tested"})
    frame = pd.DataFrame(rows)
    frame["mcnemar_p_holm"] = holm_adjust(frame["mcnemar_exact_p"].tolist())
    frame["significant_after_holm_0.05"] = frame["mcnemar_p_holm"] < 0.05
    return frame


def markdown_table(frame: pd.DataFrame, columns: list[str]) -> str:
    view = frame[columns].copy()
    headers = "| " + " | ".join(columns) + " |"
    separator = "| " + " | ".join(["---"] * len(columns)) + " |"
    rows = ["| " + " | ".join(str(value) for value in row) + " |"
            for row in view.itertuples(index=False, name=None)]
    return "\n".join([headers, separator, *rows]) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--metrics", required=True, type=Path)
    parser.add_argument("--predictions", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    expected_outputs = [args.output_dir / name for name in (
        "metrics_mean_sd_95ci.csv", "paired_feature_and_model_comparisons.csv",
        "paired_mcnemar.csv", "manuscript_summary.md")]
    existing = [path for path in expected_outputs if path.exists()]
    if existing:
        raise FileExistsError(f"Refusing to overwrite existing statistical output: {existing[0]}")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    metrics = pd.read_csv(args.metrics)
    predictions = (pd.read_csv(args.predictions) if args.predictions.suffix.lower() == ".csv"
                   else pd.read_parquet(args.predictions))
    summary = summarize(metrics)
    paired = paired_metric_tests(metrics)
    mcnemar = mcnemar_tests(predictions)
    summary.to_csv(args.output_dir / "metrics_mean_sd_95ci.csv", index=False)
    paired.to_csv(args.output_dir / "paired_feature_and_model_comparisons.csv", index=False)
    mcnemar.to_csv(args.output_dir / "paired_mcnemar.csv", index=False)
    (args.output_dir / "manuscript_summary.md").write_text(
        "# Multi-seed model summary\n\n"
        "Values are means ± sample SD across the ten frozen, source-group-aware "
        "splits. The 95% intervals are ordinary two-sided t intervals around the "
        "seed mean (df = n-1). For metrics whose natural range is [0,1], only the "
        "displayed interval endpoints are constrained to [0,1]; raw t-interval "
        "endpoints remain in `ci95_low_raw` and `ci95_high_raw`. Seed measurements, "
        "means, SDs, paired differences, MCC, and hypothesis tests are unchanged.\n\n"
        + markdown_table(
            summary, ["feature_set", "model", "metric", "n_seeds", "manuscript_value"]),
        encoding="utf-8")
    print(f"Wrote multi-seed summaries, paired comparisons, and matched McNemar tests to "
          f"{args.output_dir}")


if __name__ == "__main__":
    main()
