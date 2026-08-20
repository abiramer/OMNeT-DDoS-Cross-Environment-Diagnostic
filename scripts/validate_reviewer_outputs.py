#!/usr/bin/env python3
"""Validate timestamped reviewer reports against immutable canonical run5 evidence."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
from scipy.stats import t

from statistical_analysis import BOUNDED_0_1_METRICS, METRICS, holm_adjust

FROZEN_SEEDS = {104729, 130363, 155921, 181081, 206369,
                231701, 257053, 282427, 307759, 333019}


class Checks:
    def __init__(self) -> None:
        self.rows: list[dict[str, object]] = []

    def add(self, name: str, passed: bool, detail: str) -> None:
        self.rows.append({"check": name, "status": "pass" if passed else "fail",
                          "detail": detail})

    def require(self, name: str, passed: bool, detail: str) -> None:
        self.add(name, bool(passed), detail)

    @property
    def failures(self) -> list[dict[str, object]]:
        return [row for row in self.rows if row["status"] == "fail"]


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate_summary(checks: Checks, summary: pd.DataFrame,
                     seed_metrics: pd.DataFrame) -> None:
    checks.require("summary_rows", len(summary) == 108, f"observed={len(summary)} expected=108")
    duplicate = int(summary.duplicated(["feature_set", "model", "metric"]).sum())
    checks.require("summary_unique_keys", duplicate == 0, f"duplicates={duplicate}")
    checks.require("summary_seed_counts", set(summary.n_seeds.astype(int)) == {10},
                   f"values={sorted(summary.n_seeds.astype(int).unique())}")
    checks.require("summary_metric_set", set(summary.metric) == set(METRICS),
                   f"metrics={sorted(summary.metric.unique())}")
    numeric_columns = ["mean", "sd", "ci95_low_raw", "ci95_high_raw",
                       "ci95_low", "ci95_high"]
    finite = np.isfinite(summary[numeric_columns].apply(pd.to_numeric).to_numpy()).all()
    checks.require("summary_finite_estimable_values", finite,
                   f"columns={numeric_columns}")
    bounded = summary[summary.metric.isin(BOUNDED_0_1_METRICS)]
    endpoints_ok = ((bounded.ci95_low.astype(float) >= 0) &
                    (bounded.ci95_high.astype(float) <= 1)).all()
    checks.require("bounded_display_ci_within_0_1", endpoints_ok,
                   f"bounded_rows={len(bounded)}")

    mismatches = 0
    for row in summary.itertuples(index=False):
        values = seed_metrics[(seed_metrics.feature_set == row.feature_set) &
                              (seed_metrics.model == row.model)][row.metric].to_numpy(float)
        mean = float(np.mean(values))
        sd = float(np.std(values, ddof=1))
        half = float(t.ppf(0.975, len(values) - 1) * sd / np.sqrt(len(values)))
        expected = [mean, sd, mean - half, mean + half]
        observed = [row.mean, row.sd, row.ci95_low_raw, row.ci95_high_raw]
        mismatches += int(not np.allclose(expected, observed, rtol=0, atol=1e-12))
    checks.require("means_sd_raw_t_ci_unchanged", mismatches == 0,
                   f"mismatched_rows={mismatches}")


def validate_holm(checks: Checks, frame: pd.DataFrame, raw: str, adjusted: str,
                  name: str) -> None:
    expected = np.array(holm_adjust(pd.to_numeric(frame[raw], errors="coerce").tolist()))
    observed = pd.to_numeric(frame[adjusted], errors="coerce").to_numpy(float)
    max_difference = float(np.nanmax(np.abs(expected - observed)))
    # CSV decimal round-tripping introduces differences around 1e-14; this
    # tolerance is far below the reported precision and does not alter a test.
    same = np.allclose(expected, observed, equal_nan=True, rtol=0, atol=1e-12)
    checks.require(name, same, f"rows={len(frame)} max_abs_difference={max_difference:.3g}")


def parse_displayed_bounded_cis(path: Path) -> tuple[int, list[str]]:
    bounded_by_section = {
        "Main hold-out comparison": {"Accuracy", "Precision", "Recall", "F1",
                                      "ROC-AUC", "PR-AUC DDoS", "Balanced accuracy"},
        "OMNeT++ cross-environment results by scenario": {
            "Predicted DDoS proportion", "Accuracy", "F1", "Balanced accuracy"},
        "OMNeT++ classifier agreement": {"Agreement"},
    }
    section = ""
    header: list[str] | None = None
    checked = 0
    failures: list[str] = []
    pattern = re.compile(r"95% CI\s+(-?[0-9.]+)–(-?[0-9.]+)")
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            section = line[3:]
            header = None
            continue
        if not line.startswith("|") or section not in bounded_by_section:
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if header is None:
            header = cells
            continue
        if all(set(cell) <= {"-", ":"} for cell in cells):
            continue
        for column in bounded_by_section[section]:
            value = cells[header.index(column)]
            if value == "not estimable":
                continue
            match = pattern.search(value)
            if not match:
                failures.append(f"{section}/{column}: missing CI in {value}")
                continue
            low, high = map(float, match.groups())
            checked += 1
            if low < 0 or high > 1:
                failures.append(f"{section}/{column}: {low}–{high}")
    return checked, failures


def markdown_section_row_counts(path: Path) -> dict[str, int]:
    counts: dict[str, int] = {}
    section = ""
    table_lines = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            if section and table_lines:
                counts[section] = max(0, table_lines - 2)  # header and separator
            section = line[3:]
            table_lines = 0
        elif line.startswith("|"):
            table_lines += 1
    if section and table_lines:
        counts[section] = max(0, table_lines - 2)
    return counts


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--summary", required=True, type=Path)
    parser.add_argument("--paired", required=True, type=Path)
    parser.add_argument("--mcnemar", required=True, type=Path)
    parser.add_argument("--seed-metrics", required=True, type=Path)
    parser.add_argument("--holdout-predictions", required=True, type=Path)
    parser.add_argument("--omnet-metrics", required=True, type=Path)
    parser.add_argument("--omnet-predictions", required=True, type=Path)
    parser.add_argument("--models", required=True, type=Path)
    parser.add_argument("--final-table", required=True, type=Path)
    parser.add_argument("--python-version", required=True, type=Path)
    parser.add_argument("--pip-freeze", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    outputs = [args.output_dir / "reviewer_validation_checks.csv",
               args.output_dir / "reviewer_validation.json"]
    if args.output_dir.exists() or any(path.exists() for path in outputs):
        raise FileExistsError(f"Refusing to overwrite reviewer validation: {args.output_dir}")
    args.output_dir.mkdir(parents=True)
    checks = Checks()

    for label, path in (("python_version_snapshot", args.python_version),
                        ("pip_freeze_snapshot", args.pip_freeze)):
        checks.require(label, path.is_file() and path.stat().st_size > 0,
                       f"path={path} bytes={path.stat().st_size if path.exists() else 0}")
    version = args.python_version.read_text(encoding="utf-8-sig").strip()
    checks.require("python_exact_3_10_5", version == "Python 3.10.5", f"observed={version}")

    summary = pd.read_csv(args.summary)
    seed_metrics = pd.read_csv(args.seed_metrics)
    validate_summary(checks, summary, seed_metrics)
    checks.require("training_metric_rows", len(seed_metrics) == 120,
                   f"observed={len(seed_metrics)} expected=120")
    seed_duplicates = int(seed_metrics.duplicated(["feature_set", "seed", "model"]).sum())
    checks.require("training_metric_unique_keys", seed_duplicates == 0,
                   f"duplicates={seed_duplicates}")
    checks.require("frozen_training_seeds", set(seed_metrics.seed) == FROZEN_SEEDS,
                   f"seeds={sorted(seed_metrics.seed.unique())}")

    paired = pd.read_csv(args.paired)
    paired_keys = ["comparison_type", "stratum", "metric", "left", "right"]
    checks.require("paired_rows", len(paired) == 270, f"observed={len(paired)} expected=270")
    checks.require("paired_unique_keys", not paired.duplicated(paired_keys).any(),
                   f"duplicates={int(paired.duplicated(paired_keys).sum())}")
    checks.require("paired_matched_ten_seeds",
                   set(paired.matched_seeds.astype(int)) == {10} and set(paired.status) == {"tested"},
                   f"seed_counts={sorted(paired.matched_seeds.unique())} status={sorted(paired.status.unique())}")
    validate_holm(checks, paired, "paired_t_p", "p_holm", "paired_holm_recomputed")

    mcnemar = pd.read_csv(args.mcnemar)
    mcnemar_keys = ["seed", "left_feature_set", "left_model",
                    "right_feature_set", "right_model"]
    checks.require("mcnemar_rows", len(mcnemar) == 660,
                   f"observed={len(mcnemar)} expected=660")
    checks.require("mcnemar_unique_keys", not mcnemar.duplicated(mcnemar_keys).any(),
                   f"duplicates={int(mcnemar.duplicated(mcnemar_keys).sum())}")
    matched = (set(mcnemar.status) == {"tested"} and
               (mcnemar.matched_observations.astype(int) > 0).all())
    checks.require("mcnemar_all_predictions_matched", matched,
                   f"statuses={sorted(mcnemar.status.unique())}")
    validate_holm(checks, mcnemar, "mcnemar_exact_p", "mcnemar_p_holm",
                  "mcnemar_holm_recomputed")

    split_failures = []
    for seed in sorted(FROZEN_SEEDS):
        hashes = [file_sha256(args.models / f"feature{size}" /
                              f"split_ids_seed{seed}.csv") for size in (4, 6, 8)]
        if len(set(hashes)) != 1:
            split_failures.append(str(seed))
    checks.require("feature_4_6_8_split_files_identical", not split_failures,
                   f"mismatched_seeds={split_failures}")

    connection = duckdb.connect()
    holdout = args.holdout_predictions.as_posix().replace("'", "''")
    holdout_rows = connection.execute(
        f"SELECT count(*) FROM read_parquet('{holdout}')").fetchone()[0]
    holdout_bad_keys = connection.execute(f"""
        SELECT count(*) FROM (
          SELECT feature_set, seed, sample_id, model
          FROM read_parquet('{holdout}') GROUP BY ALL HAVING count(*) <> 1)
    """).fetchone()[0]
    holdout_bad_alignment = connection.execute(f"""
        SELECT count(*) FROM (
          SELECT seed, sample_id, count(*) AS n,
                 count(DISTINCT feature_set) AS nf, count(DISTINCT model) AS nm,
                 count(DISTINCT y_true) AS ny
          FROM read_parquet('{holdout}') GROUP BY seed, sample_id
          HAVING n <> 12 OR nf <> 3 OR nm <> 4 OR ny <> 1)
    """).fetchone()[0]
    checks.require("holdout_prediction_rows", holdout_rows == 5_225_664,
                   f"observed={holdout_rows} expected=5225664")
    checks.require("holdout_prediction_unique_keys", holdout_bad_keys == 0,
                   f"bad_keys={holdout_bad_keys}")
    checks.require("holdout_predictions_matched_across_features_models",
                   holdout_bad_alignment == 0, f"bad_seed_sample_groups={holdout_bad_alignment}")

    omnet_path = args.omnet_predictions.as_posix().replace("'", "''")
    omnet_rows = connection.execute(
        f"SELECT count(*) FROM read_csv_auto('{omnet_path}', header=true)").fetchone()[0]
    omnet_bad_keys = connection.execute(f"""
        SELECT count(*) FROM (
          SELECT sample_id, feature_set, training_seed, classifier
          FROM read_csv_auto('{omnet_path}', header=true) GROUP BY ALL HAVING count(*) <> 1)
    """).fetchone()[0]
    omnet_bad_alignment = connection.execute(f"""
        SELECT count(*) FROM (
          SELECT sample_id, count(*) AS n, count(DISTINCT y_true) AS ny
          FROM read_csv_auto('{omnet_path}', header=true) GROUP BY sample_id
          HAVING n <> 120 OR ny <> 1)
    """).fetchone()[0]
    omnet_unique = connection.execute(
        f"SELECT count(DISTINCT sample_id) FROM read_csv_auto('{omnet_path}', header=true)").fetchone()[0]
    connection.close()
    checks.require("omnet_prediction_rows", omnet_rows == 1_237_440,
                   f"observed={omnet_rows} expected=1237440")
    checks.require("omnet_prediction_unique_keys", omnet_bad_keys == 0,
                   f"bad_keys={omnet_bad_keys}")
    checks.require("omnet_prediction_alignment", omnet_bad_alignment == 0,
                   f"bad_sample_groups={omnet_bad_alignment}")
    checks.require("omnet_unique_labelled_flows", omnet_unique == 10_312,
                   f"observed={omnet_unique} expected=10312")

    omnet_metrics = pd.read_csv(args.omnet_metrics, keep_default_na=False)
    omnet_metric_keys = ["feature_set", "run", "scenario", "training_seed", "classifier"]
    checks.require("omnet_metric_rows", len(omnet_metrics) == 4800,
                   f"observed={len(omnet_metrics)} expected=4800")
    checks.require("omnet_metric_unique_keys", not omnet_metrics.duplicated(omnet_metric_keys).any(),
                   f"duplicates={int(omnet_metrics.duplicated(omnet_metric_keys).sum())}")
    metric_columns = ["accuracy", "precision", "recall", "f1", "balanced_accuracy",
                      "mcc", "roc_auc", "pr_auc_benign", "pr_auc_ddos"]
    invalid_numeric = 0
    undefined = 0
    for column in metric_columns:
        for value in omnet_metrics[column]:
            if value == "not estimable":
                undefined += 1
            else:
                try:
                    invalid_numeric += int(not math.isfinite(float(value)))
                except ValueError:
                    invalid_numeric += 1
    checks.require("omnet_estimable_metrics_finite", invalid_numeric == 0,
                   f"invalid_values={invalid_numeric}")
    checks.require("omnet_undefined_explicit", undefined > 0,
                   f"not_estimable_cells={undefined}")

    table_text = args.final_table.read_text(encoding="utf-8")
    checked_cis, ci_failures = parse_displayed_bounded_cis(args.final_table)
    checks.require("final_table_bounded_cis", not ci_failures,
                   f"checked={checked_cis} failures={ci_failures[:5]}")
    checks.require("final_table_excludes_run4", "run4" not in table_text.lower(),
                   "case-insensitive run4 search")
    checks.require("final_table_explicit_not_estimable", "not estimable" in table_text,
                   "undefined metrics retained")
    expected_sections = {
        "Main hold-out comparison": 12,
        "OMNeT++ cross-environment results by scenario": 48,
        "Feature sensitivity": 24,
        "Principal feature-8 classifier comparisons": 12,
        "Feature-8 OMNeT++ consensus confusion matrices": 4,
        "OMNeT++ classifier agreement": 18,
        "Matched McNemar summary for feature 8": 6,
    }
    observed_sections = markdown_section_row_counts(args.final_table)
    checks.require("concise_table_expected_rows", observed_sections == expected_sections,
                   f"observed={observed_sections} expected={expected_sections}")

    frame = pd.DataFrame(checks.rows)
    frame.to_csv(outputs[0], index=False)
    report = {
        "status": "valid" if not checks.failures else "invalid",
        "checks_passed": int((frame.status == "pass").sum()),
        "checks_failed": len(checks.failures),
        "failures": checks.failures,
        "input_hashes": {str(path): file_sha256(path) for path in (
            args.summary, args.paired, args.mcnemar, args.final_table,
            args.python_version, args.pip_freeze)},
    }
    outputs[1].write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    if checks.failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
