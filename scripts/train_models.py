#!/usr/bin/env python3
"""Train matched 4/6/8-feature experiments for the frozen ten seeds."""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from pipeline_common import (DEFAULT_SEEDS, FEATURES_8, feature_columns,
                             package_versions, safe_binary_metrics, write_json)


def keras_mlp(meta, seed: int):
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


def build_models(seed: int):
    from scikeras.wrappers import KerasClassifier
    from tensorflow import keras
    from xgboost import XGBClassifier

    return {
        "xgboost": Pipeline([("scale", StandardScaler()), ("model", XGBClassifier(
            n_estimators=200, learning_rate=0.07, max_depth=5, random_state=seed,
            eval_metric="logloss", n_jobs=-1))]),
        "rf": Pipeline([("scale", StandardScaler()), ("model", RandomForestClassifier(
            n_estimators=200, max_depth=10, random_state=seed, n_jobs=-1))]),
        "mlp": Pipeline([("scale", StandardScaler()), ("model", KerasClassifier(
            model=keras_mlp, model__seed=seed, epochs=50, batch_size=1024,
            validation_split=0.10, verbose=0,
            callbacks=[keras.callbacks.EarlyStopping(
                monitor="val_loss", patience=5, restore_best_weights=True)]))]),
    }


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_precomputed_split(data: pd.DataFrame, split_manifest: pd.DataFrame,
                           seed: int) -> dict[str, object]:
    """Load one already-validated source-group split; never create a record split."""
    required = {"seed", "split_id", "sample_id", "row_hash", "source_group",
                "partition", "Label"}
    missing = sorted(required - set(split_manifest.columns))
    if missing:
        raise ValueError(f"Split manifest is missing required columns: {missing}")
    ids = data["sample_id"].astype(str)
    if ids.duplicated().any():
        raise ValueError("sample_id must be unique before splitting")
    frame = split_manifest[split_manifest["seed"].astype(int) == int(seed)].copy()
    if frame.empty:
        raise ValueError(f"Precomputed split manifest has no partition for seed {seed}")
    frame["sample_id"] = frame["sample_id"].astype(str)
    if frame["sample_id"].duplicated().any() or set(frame["sample_id"]) != set(ids):
        raise ValueError(f"Seed {seed}: split sample IDs do not exactly match prepared data")
    if set(frame["partition"]) != {"train", "test"}:
        raise ValueError(f"Seed {seed}: split must contain only train and test partitions")
    split_ids = frame["split_id"].astype(str).unique()
    if len(split_ids) != 1:
        raise ValueError(f"Seed {seed}: expected exactly one split_id")
    manifest_by_id = frame.set_index("sample_id")
    aligned = manifest_by_id.loc[ids]
    if "row_hash" not in data or "source_group" not in data:
        raise ValueError("Prepared data must retain row_hash and source_group")
    if not np.array_equal(aligned["row_hash"].astype(str).to_numpy(),
                          data["row_hash"].astype(str).to_numpy()):
        raise ValueError(f"Seed {seed}: row hashes disagree between data and split manifest")
    if not np.array_equal(aligned["Label"].astype(int).to_numpy(),
                          data["Label"].astype(int).to_numpy()):
        raise ValueError(f"Seed {seed}: labels disagree between data and split manifest")
    train_mask = aligned["partition"].eq("train").to_numpy()
    test_mask = aligned["partition"].eq("test").to_numpy()
    train_pos, test_pos = np.flatnonzero(train_mask), np.flatnonzero(test_mask)
    train_groups = sorted(aligned.loc[train_mask, "source_group"].astype(str).unique())
    test_groups = sorted(aligned.loc[test_mask, "source_group"].astype(str).unique())
    if set(train_groups) & set(test_groups):
        raise AssertionError(f"Seed {seed}: source-group leakage in precomputed manifest")
    y = data["Label"].astype(int)
    if y.iloc[train_pos].nunique() != 2 or y.iloc[test_pos].nunique() != 2:
        raise ValueError(f"Seed {seed}: precomputed group partition is not class-preserving")
    return {
        "seed": seed, "split_id": split_ids[0], "train_pos": train_pos,
        "test_pos": test_pos, "train_ids": ids.iloc[train_pos].tolist(),
        "test_ids": ids.iloc[test_pos].tolist(), "group_column": "source_group",
        "train_groups": train_groups, "test_groups": test_groups,
    }


def read_data(path: Path) -> pd.DataFrame:
    return pd.read_csv(path) if path.suffix.lower() == ".csv" else pd.read_parquet(path)


def jsonable_params(model) -> dict[str, object]:
    result = {}
    for key, value in model.get_params(deep=True).items():
        if isinstance(value, (str, int, float, bool, type(None))):
            result[key] = value
        elif isinstance(value, (list, tuple)) and all(
                isinstance(item, (str, int, float, bool, type(None))) for item in value):
            result[key] = list(value)
        else:
            result[key] = repr(value)
    return result


def ensure_environment(output_dir: Path) -> dict[str, str]:
    if platform.python_version() != "3.10.5":
        raise RuntimeError(f"Training requires Python 3.10.5; active interpreter is "
                           f"{platform.python_version()}")
    versions = package_versions()
    existing = output_dir / "environment_versions.json"
    if existing.exists() and json.loads(existing.read_text(encoding="utf-8")) != versions:
        raise RuntimeError(f"Refusing to mix artifacts from a different environment in {output_dir}")
    write_json(existing, versions)
    return versions


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--split-manifest", required=True, type=Path)
    parser.add_argument("--preparation-validation", required=True, type=Path)
    parser.add_argument("--feature-sets", nargs="+", type=int, choices=[4, 6, 8],
                        default=[4, 6, 8])
    parser.add_argument("--seeds", nargs="+", type=int, default=DEFAULT_SEEDS)
    args = parser.parse_args()
    feature_sets = list(dict.fromkeys(args.feature_sets))
    if args.output_dir.exists():
        occupied = [path for path in args.output_dir.rglob("*")
                    if path.is_file() and path.name.lower() != "readme.md"]
        if occupied:
            raise FileExistsError(f"Refusing to overwrite existing model artifacts in "
                                  f"{args.output_dir}; first existing file: {occupied[0]}")
    data = read_data(args.data)
    missing = [column for column in FEATURES_8 + ["Label", "sample_id"]
               if column not in data.columns]
    if missing:
        raise ValueError(f"Prepared dataset is missing required columns: {missing}")
    if data[FEATURES_8].replace([np.inf, -np.inf], np.nan).isna().any().any():
        raise ValueError("Training data contains missing or non-finite feature values")
    validation = json.loads(args.preparation_validation.read_text(encoding="utf-8"))
    if validation.get("status") != "valid":
        raise ValueError("Training requires a valid independent preparation report")
    data_hash = sha256_file(args.data)
    if data_hash != validation.get("prepared_dataset_sha256"):
        raise ValueError("Prepared dataset SHA-256 does not match independent validation")
    split_hash = sha256_file(args.split_manifest)
    if split_hash != validation.get("split_manifest_sha256"):
        raise ValueError("Split manifest SHA-256 does not match independent validation")
    split_manifest = read_data(args.split_manifest)
    precomputed_splits = {
        seed: load_precomputed_split(data, split_manifest, seed) for seed in args.seeds
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    versions = ensure_environment(args.output_dir)
    all_rows, all_predictions, split_records = [], [], []
    for seed in args.seeds:
        split = precomputed_splits[seed]
        train_pos, test_pos = split["train_pos"], split["test_pos"]
        y_train = data.iloc[train_pos]["Label"].astype(int)
        y_test = data.iloc[test_pos]["Label"].astype(int)
        split_record = {key: value for key, value in split.items()
                        if key not in {"train_pos", "test_pos"}}
        split_record.update({
            "train_class_counts": {str(k): int(v) for k, v in y_train.value_counts().items()},
            "test_class_counts": {str(k): int(v) for k, v in y_test.value_counts().items()},
        })
        split_records.append(split_record)
        canonical_test_ids = data.iloc[test_pos]["sample_id"].astype(str).to_numpy()
        for feature_set in feature_sets:
            features = feature_columns(feature_set)
            feature_dir = args.output_dir / f"feature{feature_set}"
            feature_dir.mkdir(parents=True, exist_ok=True)
            x_train, x_test = data.iloc[train_pos][features], data.iloc[test_pos][features]
            if not np.array_equal(canonical_test_ids,
                                  data.iloc[test_pos]["sample_id"].astype(str).to_numpy()):
                raise AssertionError("Feature-set split identifiers diverged")
            partition = np.full(len(data), "train", dtype=object)
            partition[test_pos] = "test"
            split_frame = pd.DataFrame({
                "seed": seed,
                "sample_id": data["sample_id"].astype(str),
                "partition": partition,
            })
            split_frame.to_csv(feature_dir / f"split_ids_seed{seed}.csv", index=False)
            seed_predictions = {}
            for name, model in build_models(seed).items():
                model.fit(x_train, y_train)
                pred = np.asarray(model.predict(x_test), dtype=int).reshape(-1)
                score = np.asarray(model.predict_proba(x_test)[:, 1], dtype=float)
                seed_predictions[name] = (pred, score)
                metrics = safe_binary_metrics(y_test, pred, score)
                all_rows.append({"feature_set": feature_set, "seed": seed,
                                 "model": name, **metrics})
                all_predictions.append(pd.DataFrame({
                    "feature_set": feature_set, "seed": seed,
                    "sample_id": canonical_test_ids, "y_true": y_test.to_numpy(),
                    "model": name, "y_pred": pred, "score": score,
                }))
                artifact = feature_dir / f"{name}-seed{seed}.joblib"
                joblib.dump(model, artifact)
                write_json(feature_dir / f"{name}-seed{seed}.metadata.json", {
                    "artifact": artifact.name, "feature_set": feature_set,
                    "feature_order": features, "preprocessing": "StandardScaler in saved Pipeline",
                    "seed": seed, "split_ids_file": f"split_ids_seed{seed}.csv",
                    "model_parameters": jsonable_params(model), "package_versions": versions,
                })
            hard_sum = sum(seed_predictions[name][0] for name in ("xgboost", "rf", "mlp"))
            hybrid_pred = (hard_sum >= 2).astype(int)
            hybrid_score = sum(seed_predictions[name][1] for name in ("xgboost", "rf", "mlp")) / 3
            all_rows.append({"feature_set": feature_set, "seed": seed, "model": "hybrid",
                             **safe_binary_metrics(y_test, hybrid_pred, hybrid_score)})
            all_predictions.append(pd.DataFrame({
                "feature_set": feature_set, "seed": seed,
                "sample_id": canonical_test_ids, "y_true": y_test.to_numpy(),
                "model": "hybrid", "y_pred": hybrid_pred, "score": hybrid_score,
            }))
            write_json(feature_dir / f"hybrid-seed{seed}.metadata.json", {
                "feature_set": feature_set, "feature_order": features, "seed": seed,
                "rule": "hard majority vote of xgboost/rf/mlp; mean DDoS probability for ranking",
                "component_artifacts": [f"{name}-seed{seed}.joblib"
                                        for name in ("xgboost", "rf", "mlp")],
                "split_ids_file": f"split_ids_seed{seed}.csv", "package_versions": versions,
            })
    results = pd.DataFrame(all_rows)
    results.to_csv(args.output_dir / "seed_metrics.csv", index=False)
    numeric_metrics = ["accuracy", "precision", "recall", "f1", "roc_auc",
                       "pr_auc_benign", "pr_auc_ddos", "balanced_accuracy", "mcc"]
    numeric_results = results.copy()
    numeric_results[numeric_metrics] = numeric_results[numeric_metrics].apply(
        pd.to_numeric, errors="coerce")
    summary = numeric_results.groupby(["feature_set", "model"])[numeric_metrics].agg(
        ["mean", "std"])
    summary.to_csv(args.output_dir / "metrics_mean_std.csv")
    pd.concat(all_predictions, ignore_index=True).to_parquet(
        args.output_dir / "test_predictions.parquet", index=False)
    write_json(args.output_dir / "training_metadata.json", {
        "data": str(args.data), "feature_sets": {str(k): feature_columns(k) for k in feature_sets},
        "seeds": args.seeds, "test_fraction": 0.20,
        "split_mode": "precomputed_source_group_only_no_record_fallback",
        "split_manifest": str(args.split_manifest), "split_manifest_sha256": split_hash,
        "prepared_dataset_sha256": data_hash,
        "preparation_validation": str(args.preparation_validation),
        "split_records": split_records,
        "matched_split_invariant": "For each seed, identical sample_id partitions are used for 4/6/8.",
        "package_versions": versions,
    })


if __name__ == "__main__":
    main()
