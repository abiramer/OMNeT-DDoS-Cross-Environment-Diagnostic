#!/usr/bin/env python3
"""Generate a matched ten-seed ROC summary from frozen hold-out predictions.

Classification: compatible reporting utility. This script was added for the
public package and was not used to create the already-frozen run5 predictions.
It refuses an existing output directory and never changes its input file.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import t
from sklearn.metrics import auc, roc_curve

DEFAULT_SEEDS = [104729, 130363, 155921, 181081, 206369,
                 231701, 257053, 282427, 307759, 333019]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _svg(curves: list[dict[str, object]], output: Path, feature_set: int) -> None:
    width, height, margin = 920, 680, 76
    plot_w, plot_h = width - 2 * margin, height - 2 * margin
    colors = {"xgboost": "#1f77b4", "rf": "#2ca02c", "mlp": "#d62728",
              "hybrid": "#9467bd"}
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        f'<text x="{width/2}" y="34" text-anchor="middle" font-family="Arial" '
        f'font-size="21">Feature-{feature_set} matched ten-seed ROC summary</text>',
        f'<line x1="{margin}" y1="{height-margin}" x2="{width-margin}" '
        f'y2="{height-margin}" stroke="black"/>',
        f'<line x1="{margin}" y1="{height-margin}" x2="{margin}" y2="{margin}" '
        f'stroke="black"/>',
        f'<line x1="{margin}" y1="{height-margin}" x2="{width-margin}" y2="{margin}" '
        f'stroke="#999" stroke-dasharray="6 5"/>',
    ]
    for tick in np.linspace(0, 1, 6):
        x = margin + tick * plot_w
        y = height - margin - tick * plot_h
        parts.extend([
            f'<text x="{x:.1f}" y="{height-margin+24}" text-anchor="middle" '
            f'font-family="Arial" font-size="12">{tick:.1f}</text>',
            f'<text x="{margin-14}" y="{y+4:.1f}" text-anchor="end" '
            f'font-family="Arial" font-size="12">{tick:.1f}</text>',
        ])
    for index, curve in enumerate(curves):
        upper = np.minimum(1.0, curve["mean_tpr"] + curve["sd_tpr"])
        lower = np.maximum(0.0, curve["mean_tpr"] - curve["sd_tpr"])
        band = list(zip(curve["fpr"], upper)) + list(
            zip(curve["fpr"][::-1], lower[::-1]))
        band_points = " ".join(
            f"{margin + x * plot_w:.2f},{height - margin - y * plot_h:.2f}"
            for x, y in band
        )
        points = " ".join(
            f"{margin + x * plot_w:.2f},{height - margin - y * plot_h:.2f}"
            for x, y in zip(curve["fpr"], curve["mean_tpr"])
        )
        model = str(curve["model"])
        color = colors.get(model, "#333333")
        parts.append(f'<polygon points="{band_points}" fill="{color}" '
                     f'fill-opacity="0.12" stroke="none"/>')
        parts.append(f'<polyline points="{points}" fill="none" stroke="{color}" '
                     f'stroke-width="2.5"/>')
        legend_y = margin + 22 * index
        parts.append(f'<line x1="{width-300}" y1="{legend_y}" x2="{width-270}" '
                     f'y2="{legend_y}" stroke="{color}" stroke-width="3"/>')
        parts.append(f'<text x="{width-262}" y="{legend_y+4}" font-family="Arial" '
                     f'font-size="13">{model}: AUC {curve["auc_mean"]:.4f} '
                     f'± {curve["auc_sd"]:.4f}</text>')
    parts.extend([
        f'<text x="{width/2}" y="{height-16}" text-anchor="middle" '
        f'font-family="Arial" font-size="15">False-positive rate</text>',
        f'<text x="18" y="{height/2}" text-anchor="middle" font-family="Arial" '
        f'font-size="15" transform="rotate(-90 18 {height/2})">True-positive rate</text>',
        f'<text x="{width/2}" y="58" text-anchor="middle" font-family="Arial" '
        f'font-size="12">Mean ROC across 10 matched seeds; bands: ±1 sample SD of TPR</text>',
        '</svg>',
    ])
    output.write_text("\n".join(parts) + "\n", encoding="utf-8")


def _png(curves: list[dict[str, object]], output: Path, feature_set: int) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    colors = {"xgboost": "#1f77b4", "rf": "#2ca02c", "mlp": "#d62728",
              "hybrid": "#9467bd"}
    fig, axis = plt.subplots(figsize=(9.2, 6.8), dpi=200)
    axis.plot([0, 1], [0, 1], linestyle="--", color="#777777", linewidth=1)
    for curve in curves:
        model = str(curve["model"])
        fpr = np.asarray(curve["fpr"])
        mean_tpr = np.asarray(curve["mean_tpr"])
        sd_tpr = np.asarray(curve["sd_tpr"])
        color = colors.get(model, "#333333")
        axis.fill_between(fpr, np.maximum(0.0, mean_tpr - sd_tpr),
                          np.minimum(1.0, mean_tpr + sd_tpr), color=color,
                          alpha=0.12, linewidth=0)
        axis.plot(fpr, mean_tpr, color=color, linewidth=2,
                  label=f'{model}: AUC {curve["auc_mean"]:.4f} ± '
                        f'{curve["auc_sd"]:.4f}')
    axis.set(xlim=(0, 1), ylim=(0, 1), xlabel="False-positive rate",
             ylabel="True-positive rate")
    fig.suptitle(f"Feature-{feature_set} matched ten-seed ROC summary",
                 fontsize=16, y=0.98)
    axis.set_title("Mean ROC across 10 matched seeds; bands: ±1 sample SD of TPR",
                   fontsize=9, pad=12)
    axis.grid(alpha=0.2)
    axis.legend(loc="lower right", frameon=True, fontsize=8)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig(output, dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--predictions", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--feature-set", required=True, type=int, choices=[4, 6, 8])
    parser.add_argument("--models", nargs="+", required=True,
                        choices=["xgboost", "rf", "mlp", "hybrid"])
    parser.add_argument("--seeds", nargs="+", type=int, default=DEFAULT_SEEDS)
    parser.add_argument("--grid-points", type=int, default=1001)
    args = parser.parse_args()
    if not args.predictions.is_file():
        raise FileNotFoundError(f"Predictions file does not exist: {args.predictions}")
    if args.output_dir.exists():
        raise FileExistsError(f"Refusing to overwrite Figure 5 output: {args.output_dir}")
    if args.grid_points < 101:
        raise ValueError("--grid-points must be at least 101")

    frame = pd.read_parquet(args.predictions)
    required = {"feature_set", "seed", "model", "sample_id", "y_true", "score"}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"Prediction table is missing columns: {missing}")
    frame = frame[(frame.feature_set.astype(int) == args.feature_set) &
                  frame.model.isin(args.models)].copy()
    expected = {(seed, model) for seed in args.seeds for model in args.models}
    observed = set(zip(frame.seed.astype(int), frame.model.astype(str)))
    if observed != expected:
        raise ValueError(f"Expected seed/model cells do not match input; missing="
                         f"{sorted(expected-observed)}, extra={sorted(observed-expected)}")
    if frame.duplicated(["seed", "model", "sample_id"]).any():
        raise ValueError("Duplicate seed/model/sample_id predictions are not allowed")

    args.output_dir.mkdir(parents=True)
    grid = np.linspace(0.0, 1.0, args.grid_points)
    curve_rows: list[dict[str, object]] = []
    summary_rows: list[dict[str, object]] = []
    svg_curves: list[dict[str, object]] = []
    for model in args.models:
        tprs, aucs = [], []
        for seed in args.seeds:
            cell = frame[(frame.seed.astype(int) == seed) & (frame.model == model)]
            if cell.y_true.nunique() != 2:
                raise ValueError(f"ROC is not estimable for seed={seed}, model={model}")
            fpr, tpr, _ = roc_curve(cell.y_true.astype(int), cell.score.astype(float))
            interpolated = np.interp(grid, fpr, tpr)
            interpolated[0], interpolated[-1] = 0.0, 1.0
            tprs.append(interpolated)
            aucs.append(float(auc(fpr, tpr)))
        matrix = np.vstack(tprs)
        mean_tpr = matrix.mean(axis=0)
        sd_tpr = matrix.std(axis=0, ddof=1)
        for fpr_value, mean_value, sd_value in zip(grid, mean_tpr, sd_tpr):
            curve_rows.append({"feature_set": args.feature_set, "model": model,
                               "n_seeds": len(args.seeds), "fpr": fpr_value,
                               "mean_tpr": mean_value, "sd_tpr": sd_value})
        mean_auc = float(np.mean(aucs))
        sd_auc = float(np.std(aucs, ddof=1))
        half = float(t.ppf(0.975, len(aucs)-1) * sd_auc / np.sqrt(len(aucs)))
        summary_rows.append({"feature_set": args.feature_set, "model": model,
                             "n_seeds": len(args.seeds), "auc_mean": mean_auc,
                             "auc_sample_sd": sd_auc,
                             "auc_ci95_low": max(0.0, mean_auc-half),
                             "auc_ci95_high": min(1.0, mean_auc+half)})
        svg_curves.append({"model": model, "fpr": grid, "mean_tpr": mean_tpr,
                           "sd_tpr": sd_tpr, "auc_mean": mean_auc,
                           "auc_sd": sd_auc})

    pd.DataFrame(curve_rows).to_csv(args.output_dir / "figure5_roc_curves.csv", index=False)
    pd.DataFrame(summary_rows).to_csv(args.output_dir / "figure5_roc_summary.csv", index=False)
    _svg(svg_curves, args.output_dir / "figure5_roc_summary.svg", args.feature_set)
    _png(svg_curves, args.output_dir / "figure5_roc_summary.png", args.feature_set)
    metadata = {
        "classification": "version 1.0.0 output from frozen canonical predictions",
        "input_filename": args.predictions.name,
        "input_sha256": _sha256(args.predictions), "feature_set": args.feature_set,
        "models": args.models, "seeds": args.seeds, "grid_points": args.grid_points,
        "aggregation": "per-seed ROC; TPR linearly interpolated on common FPR grid; "
                       "mean and sample SD across matched seeds",
        "variability_display": "shaded band is mean TPR plus/minus one sample SD, "
                               "constrained to [0,1] for display only",
        "ci": "two-sided t interval for mean AUC; displayed endpoints constrained to [0,1]",
        "run4_excluded": True,
    }
    (args.output_dir / "figure5_metadata.json").write_text(
        json.dumps(metadata, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
