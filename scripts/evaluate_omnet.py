#!/usr/bin/env python3
"""Apply matching 4/6/8-feature models to per-flow-labelled OMNeT++ tables."""
from __future__ import annotations

import argparse
import json
import re
from itertools import combinations
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from scipy.stats import t
from sklearn.metrics import cohen_kappa_score

from pipeline_common import (FEATURES_8, INT_TO_LABEL, LABEL_TO_INT,
                             feature_columns, safe_binary_metrics, stable_id)

MODEL_PATTERN = re.compile(r"^(xgboost|rf|mlp)-seed(\d+)\.joblib$")


def keras_mlp(meta, seed: int):
    """Resolve the SciKeras factory persisted as ``__main__.keras_mlp``.

    The trainer is invoked as a script, so joblib records its model factory in
    the ``__main__`` module.  Keeping the identical factory here allows the
    evaluator to load those immutable artifacts without retraining them.
    """
    import tensorflow as tf
    from tensorflow import keras

    tf.keras.utils.set_random_seed(seed)
    model = keras.Sequential([
        keras.layers.Input(shape=(meta["n_features_in_"],)),
        keras.layers.Dense(32, activation="relu"),
        keras.layers.Dense(16, activation="relu"),
        keras.layers.Dense(1, activation="sigmoid"),
    ])
    model.compile(optimizer=keras.optimizers.Adam(learning_rate=0.001),
                  loss="binary_crossentropy", metrics=["accuracy"])
    return model


def load_feature_tables(paths: list[Path]) -> pd.DataFrame:
    parts = []
    for path in paths:
        frame = pd.read_csv(path)
        required = FEATURES_8 + ["ground_truth_label", "traffic_source", "run", "scenario"]
        missing = [column for column in required if column not in frame.columns]
        if missing:
            raise ValueError(f"Refusing unlabeled/legacy OMNeT++ CSV {path}: "
                             f"missing required columns {missing}. Re-extract from PCAP; "
                             "scenario names will not be converted into labels.")
        invalid = sorted(set(frame["ground_truth_label"].dropna()) - set(LABEL_TO_INT))
        if invalid or frame["ground_truth_label"].isna().any():
            raise ValueError(f"{path}: invalid ground_truth_label values {invalid}")
        frame = frame.copy()
        frame["source_csv"] = path.name
        if "flow_id" not in frame.columns:
            frame["flow_id"] = [stable_id(path.name, index) for index in range(len(frame))]
        parts.append(frame)
    data = pd.concat(parts, ignore_index=True)
    if data["flow_id"].duplicated().any():
        data["sample_id"] = [stable_id(row.source_csv, row.flow_id)
                             for row in data[["source_csv", "flow_id"]].itertuples()]
    else:
        data["sample_id"] = data["flow_id"].astype(str)
    data["y_true"] = data["ground_truth_label"].map(LABEL_TO_INT).astype(int)
    return data


def predict_score(model, frame: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    pred = np.asarray(model.predict(frame), dtype=int).reshape(-1)
    if not hasattr(model, "predict_proba"):
        raise ValueError("Every saved classifier must expose predict_proba for AUC evaluation")
    score = np.asarray(model.predict_proba(frame)[:, 1], dtype=float)
    return pred, score


def metric_rows(predictions: pd.DataFrame) -> pd.DataFrame:
    rows = []
    keys = ["feature_set", "run", "scenario", "training_seed", "classifier"]
    for values, group in predictions.groupby(keys, sort=True):
        y, pred, score = group.y_true, group.y_pred, group.score
        metrics = safe_binary_metrics(y, pred, score)
        predicted_benign = int((pred == 0).sum())
        predicted_ddos = int((pred == 1).sum())
        rows.append({**dict(zip(keys, values)), "evaluated_flows": len(group),
                     "ground_truth_benign": int((y == 0).sum()),
                     "ground_truth_ddos": int((y == 1).sum()),
                     "predicted_benign": predicted_benign,
                     "predicted_ddos": predicted_ddos,
                     "predicted_benign_proportion": predicted_benign / len(group),
                     "predicted_ddos_proportion": predicted_ddos / len(group),
                     **metrics})
    return pd.DataFrame(rows)


def agreement_rows(predictions: pd.DataFrame) -> pd.DataFrame:
    rows = []
    keys = ["feature_set", "run", "scenario", "training_seed"]
    for values, group in predictions.groupby(keys, sort=True):
        wide = group.pivot(index="sample_id", columns="classifier", values="y_pred")
        for left, right in combinations(sorted(wide.columns), 2):
            pair = wide[[left, right]].dropna()
            if pair.empty:
                continue
            agreement = float((pair[left] == pair[right]).mean())
            kappa = cohen_kappa_score(pair[left], pair[right])
            rows.append({**dict(zip(keys, values)), "classifier_left": left,
                         "classifier_right": right, "matched_flows": len(pair),
                         "agreement_percentage": 100 * agreement,
                         "cohen_kappa": (float(kappa) if np.isfinite(kappa)
                                         else "not estimable"),
                         "agreement_with_ensemble": (100 * agreement
                                                     if "hybrid" in {left, right}
                                                     else "not applicable")})
    return pd.DataFrame(rows)


def seed_summary(metrics: pd.DataFrame) -> pd.DataFrame:
    metric_names = ["accuracy", "precision", "recall", "f1", "balanced_accuracy",
                    "mcc", "roc_auc", "pr_auc_benign", "pr_auc_ddos"]
    rows = []
    group_keys = ["feature_set", "scenario", "training_seed", "classifier"]
    for values, group in metrics.groupby(group_keys, sort=True):
        for metric in metric_names:
            numeric = pd.to_numeric(group[metric], errors="coerce").dropna().to_numpy(float)
            n = len(numeric)
            mean = float(np.mean(numeric)) if n else "not estimable"
            sd = float(np.std(numeric, ddof=1)) if n > 1 else "not estimable"
            half = (float(t.ppf(0.975, n - 1) * sd / np.sqrt(n))
                    if n > 1 else None)
            rows.append({**dict(zip(group_keys, values)), "metric": metric,
                         "n_simulation_seeds": n, "mean": mean, "sd": sd,
                         "ci95_low": (mean - half if half is not None else "not estimable"),
                         "ci95_high": (mean + half if half is not None else "not estimable")})
    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--features", nargs="+", required=True, type=Path)
    parser.add_argument("--models", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--feature-sets", nargs="+", type=int, choices=[4, 6, 8],
                        default=[4, 6, 8])
    args = parser.parse_args()
    expected_outputs = [args.output_dir / name for name in (
        "flow_predictions.csv", "run_scenario_metrics.csv", "classifier_agreement.csv",
        "metrics_across_simulation_seeds.csv")]
    existing = [path for path in expected_outputs if path.exists()]
    if existing:
        raise FileExistsError(f"Refusing to overwrite existing evaluation output: {existing[0]}")
    data = load_feature_tables(args.features)
    predictions = []
    for feature_set in dict.fromkeys(args.feature_sets):
        features = feature_columns(feature_set)
        numeric = data[features].apply(pd.to_numeric, errors="coerce")
        if numeric.replace([np.inf, -np.inf], np.nan).isna().any().any():
            raise ValueError(f"Feature set {feature_set} contains undefined/non-finite values; "
                             "zero-duration flows cannot be assigned misleading rates")
        model_dir = args.models / f"feature{feature_set}"
        paths = [path for path in sorted(model_dir.glob("*.joblib"))
                 if MODEL_PATTERN.match(path.name)]
        if not paths:
            raise ValueError(f"No model artifacts found in {model_dir}")
        by_seed: dict[int, dict[str, tuple[np.ndarray, np.ndarray]]] = {}
        for path in paths:
            match = MODEL_PATTERN.match(path.name)
            assert match is not None
            classifier, training_seed_text = match.groups()
            training_seed = int(training_seed_text)
            metadata_path = path.with_suffix(".metadata.json")
            if metadata_path.exists():
                metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
                if metadata.get("feature_order") != features:
                    raise ValueError(f"Feature order mismatch for {path}")
            pred, score = predict_score(joblib.load(path), numeric)
            by_seed.setdefault(training_seed, {})[classifier] = (pred, score)
        for training_seed, components in by_seed.items():
            required = {"xgboost", "rf", "mlp"}
            if set(components) != required:
                raise ValueError(f"Feature set {feature_set}, seed {training_seed}: "
                                 f"expected components {sorted(required)}, got {sorted(components)}")
            component_view = dict(components)
            hard = sum(components[name][0] for name in required)
            component_view["hybrid"] = ((hard >= 2).astype(int),
                                        sum(components[name][1] for name in required) / 3)
            for classifier, (pred, score) in component_view.items():
                current = data[["sample_id", "flow_id", "run", "scenario",
                                "ground_truth_label", "traffic_source", "y_true"]].copy()
                current["feature_set"] = feature_set
                current["training_seed"] = training_seed
                current["classifier"] = classifier
                current["y_pred"] = pred
                current["predicted_label"] = [INT_TO_LABEL[int(value)] for value in pred]
                current["score_ddos"] = score
                current.rename(columns={"score_ddos": "score"}, inplace=True)
                predictions.append(current)
    result = pd.concat(predictions, ignore_index=True)
    metrics = metric_rows(result)
    agreements = agreement_rows(result)
    summaries = seed_summary(metrics)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    result.to_csv(args.output_dir / "flow_predictions.csv", index=False)
    metrics.to_csv(args.output_dir / "run_scenario_metrics.csv", index=False)
    agreements.to_csv(args.output_dir / "classifier_agreement.csv", index=False)
    summaries.to_csv(args.output_dir / "metrics_across_simulation_seeds.csv", index=False)
    print(f"Evaluated {data.shape[0]} labelled flows across feature sets "
          f"{sorted(set(args.feature_sets))}; outputs={args.output_dir}")


if __name__ == "__main__":
    main()
