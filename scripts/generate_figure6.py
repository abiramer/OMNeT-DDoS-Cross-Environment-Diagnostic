#!/usr/bin/env python3
"""Generate Figure 6 for an author-prespecified frozen XGBoost artifact."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import xgboost as xgb


FEATURES = [
    "Total Fwd Packets", "Total Backward Packets", "Flow Bytes/s",
    "Flow Packets/s", "Flow Duration", "Total Length of Fwd Packets",
    "Total Length of Bwd Packets", "Fwd Packet Length Mean",
]
CAPTION = (
    "Figure 6. SHAP summary for the frozen canonical feature-8 XGBoost model "
    "trained with seed 104729. Seed 104729 was selected as the first seed in "
    "the predefined numerically ordered frozen seed list, independently of "
    "model performance."
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def rank_id(sample_id: str, sampling_seed: int) -> str:
    return hashlib.sha256(f"{sampling_seed}:{sample_id}".encode()).hexdigest()


def render_svg(rows: pd.DataFrame, output: Path) -> None:
    rows = rows.sort_values("mean_abs_treeshap")
    width, height, left, right, top, bottom = 1120, 570, 330, 70, 72, 65
    plot_w = width - left - right
    maximum = float(rows.mean_abs_treeshap.max()) or 1.0
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        f'<text x="{width/2}" y="30" text-anchor="middle" font-family="Arial" '
        f'font-size="20">Feature-8 XGBoost TreeSHAP summary — seed 104729</text>',
        f'<text x="{width/2}" y="52" text-anchor="middle" font-family="Arial" '
        f'font-size="12">Mean absolute contribution to the DDoS-class raw margin; '
        f'deterministic 10,000-row hold-out sample</text>',
    ]
    usable_h = height - top - bottom
    for index, row in enumerate(rows.itertuples(index=False)):
        y = top + (index + 0.5) * usable_h / len(rows)
        bar_w = float(row.mean_abs_treeshap) / maximum * plot_w
        parts.extend([
            f'<text x="{left-12}" y="{y+5:.1f}" text-anchor="end" '
            f'font-family="Arial" font-size="13">{row.feature}</text>',
            f'<rect x="{left}" y="{y-17:.1f}" width="{bar_w:.1f}" height="34" '
            f'fill="#1f77b4"/>',
            f'<text x="{left+bar_w+8:.1f}" y="{y+5:.1f}" font-family="Arial" '
            f'font-size="12">{row.mean_abs_treeshap:.6g}</text>',
        ])
    parts.extend([
        f'<text x="{width/2}" y="{height-18}" text-anchor="middle" '
        f'font-family="Arial" font-size="13">Mean |TreeSHAP contribution| '
        f'(XGBoost raw-margin units)</text>',
        '</svg>',
    ])
    output.write_text("\n".join(parts) + "\n", encoding="utf-8")


def render_png(rows: pd.DataFrame, output: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    rows = rows.sort_values("mean_abs_treeshap")
    fig, axis = plt.subplots(figsize=(10.4, 6.2), dpi=200)
    axis.barh(rows.feature, rows.mean_abs_treeshap, color="#1f77b4")
    axis.set_xlabel("Mean |TreeSHAP contribution| (XGBoost raw-margin units)")
    fig.suptitle("Feature-8 XGBoost TreeSHAP summary — seed 104729",
                 fontsize=16, y=0.98)
    axis.set_title("DDoS-class raw margin; deterministic 10,000-row hold-out sample",
                   fontsize=9, pad=12)
    axis.grid(axis="x", alpha=0.2)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig(output, dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True, type=Path)
    parser.add_argument("--models", required=True, type=Path)
    parser.add_argument("--seed-list", required=True, type=Path)
    parser.add_argument("--model-inventory", required=True, type=Path)
    parser.add_argument("--training-metadata", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--seed", type=int, default=104729)
    parser.add_argument("--sample-size", type=int, default=10000)
    parser.add_argument("--sampling-seed", type=int, default=104729)
    args = parser.parse_args()
    for path in [args.data, args.seed_list, args.model_inventory,
                 args.training_metadata]:
        if not path.is_file():
            raise FileNotFoundError(path)
    if args.output_dir.exists():
        raise FileExistsError(f"Refusing to overwrite Figure 6 output: {args.output_dir}")
    if args.seed != 104729:
        raise ValueError("Publication Figure 6 is frozen to author-approved seed 104729")
    seeds = [int(line) for line in args.seed_list.read_text().splitlines()
             if line.strip() and not line.lstrip().startswith("#")]
    if seeds != sorted(seeds) or not seeds or seeds[0] != args.seed:
        raise ValueError("Seed 104729 must be first in the numerically ordered frozen seed list")
    if xgb.__version__ != "2.1.1":
        raise RuntimeError(f"Expected xgboost 2.1.1; found {xgb.__version__}")

    artifact_rel = f"feature8/xgboost-seed{args.seed}.joblib"
    artifact = args.models / Path(artifact_rel)
    artifact_meta = artifact.with_suffix(".metadata.json")
    split_file = args.models / "feature8" / f"split_ids_seed{args.seed}.csv"
    for path in [artifact, artifact_meta, split_file]:
        if not path.is_file():
            raise FileNotFoundError(path)
    artifact_hash = sha256(artifact)
    with args.model_inventory.open(newline="", encoding="utf-8-sig") as stream:
        inventory = list(csv.DictReader(stream))
    matches = [row for row in inventory if row.get("relative_path") == artifact_rel]
    if len(matches) != 1 or matches[0].get("sha256") != artifact_hash:
        raise ValueError("Artifact SHA-256 does not match the unique model-inventory entry")
    metadata = json.loads(artifact_meta.read_text(encoding="utf-8"))
    if metadata.get("feature_set") != 8 or metadata.get("seed") != args.seed:
        raise ValueError("Artifact metadata feature set or seed is not canonical")
    if metadata.get("feature_order") != FEATURES:
        raise ValueError("Artifact metadata feature order is not the frozen feature-8 order")
    training = json.loads(args.training_metadata.read_text(encoding="utf-8"))
    if "max-benign-run5-inet454" not in training.get("data", ""):
        raise ValueError("Training metadata does not identify canonical run5-INET4.5.4")
    if args.seed not in training.get("seeds", []):
        raise ValueError("Selected seed is absent from canonical training metadata")
    if training.get("prepared_dataset_sha256") != sha256(args.data):
        raise ValueError("Prepared dataset hash disagrees with canonical training metadata")

    data = pd.read_parquet(args.data, columns=["sample_id", *FEATURES])
    data["sample_id"] = data.sample_id.astype(str)
    if data.sample_id.duplicated().any():
        raise ValueError("Prepared sample_id values must be unique")
    split = pd.read_csv(split_file, usecols=["seed", "sample_id", "partition"])
    split = split[(split.seed.astype(int) == args.seed) &
                  (split.partition == "test")].copy()
    split["sample_id"] = split.sample_id.astype(str)
    if split.sample_id.duplicated().any():
        raise ValueError("Frozen test split contains duplicate sample IDs")
    selected = data[data.sample_id.isin(set(split.sample_id))].copy()
    if len(selected) != len(split):
        raise ValueError("Prepared data and frozen test split disagree")
    selected["_rank"] = selected.sample_id.map(
        lambda value: rank_id(value, args.sampling_seed))
    selected = selected.sort_values("_rank", kind="mergesort").head(
        min(args.sample_size, len(selected)))

    pipeline = joblib.load(artifact)
    if list(pipeline.feature_names_in_) != FEATURES:
        raise ValueError("Loaded pipeline feature order disagrees with metadata")
    if pipeline.named_steps["model"].get_params()["random_state"] != args.seed:
        raise ValueError("Loaded model random_state disagrees with selected seed")
    transformed = pipeline.named_steps["scale"].transform(selected[FEATURES])
    booster = pipeline.named_steps["model"].get_booster()
    contributions = booster.predict(
        xgb.DMatrix(transformed, feature_names=FEATURES), pred_contribs=True)
    if contributions.shape != (len(selected), len(FEATURES) + 1):
        raise ValueError(f"Unexpected TreeSHAP shape: {contributions.shape}")
    summary = pd.DataFrame({
        "feature": FEATURES,
        "mean_abs_treeshap": np.abs(contributions[:, :-1]).mean(axis=0),
    })
    args.output_dir.mkdir(parents=True)
    summary.to_csv(args.output_dir / "figure6_shap_summary.csv", index=False)
    render_svg(summary, args.output_dir / "figure6_shap_summary.svg")
    render_png(summary, args.output_dir / "figure6_shap_summary.png")
    provenance = {
        "caption": CAPTION,
        "model_family": "XGBoost", "feature_set": 8, "training_seed": args.seed,
        "selection_rule": "first seed in the predefined numerically ordered frozen seed list; independent of performance",
        "artifact_relative_path": f"models/max-benign-run5-inet454/{artifact_rel}",
        "artifact_filename": artifact.name, "artifact_sha256": artifact_hash,
        "artifact_metadata_sha256": sha256(artifact_meta),
        "prepared_data_filename": args.data.name,
        "prepared_data_sha256": sha256(args.data), "features": FEATURES,
        "explainer": "XGBoost 2.1.1 native exact TreeSHAP via Booster.predict(pred_contribs=True)",
        "represented_class": "DDoS (positive class 1); contributions are in binary raw-margin/log-odds units",
        "background_sampling": "No external background sample; native tree-path-dependent TreeSHAP expectation encoded by the fitted booster",
        "evaluation_sampling": "Frozen seed-104729 hold-out IDs only; deterministic SHA-256 rank of sampling_seed:sample_id; without replacement",
        "sample_size": len(selected), "sampling_seed": args.sampling_seed,
        "software_versions": metadata.get("package_versions", {}),
        "loading_procedure": "joblib.load; verify Pipeline feature_names_in_, StandardScaler, XGBClassifier random_state, then use get_booster()",
        "interpretation": "Explains the selected classifier's predictions; no simulator-realism or fidelity claim.",
        "run4_excluded": True,
    }
    (args.output_dir / "figure6_provenance.json").write_text(
        json.dumps(provenance, indent=2) + "\n", encoding="utf-8")
    (args.output_dir / "CAPTION.txt").write_text(CAPTION + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
