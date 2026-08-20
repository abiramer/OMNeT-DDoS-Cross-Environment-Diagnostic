#!/usr/bin/env python3
"""Create an auditable CICDDoS2019 eight-feature superset dataset."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from pipeline_common import FEATURES_8, stable_id

ALIASES = {
    "Total Fwd Packets": ["Total Fwd Packets", "Tot Fwd Pkts"],
    "Total Backward Packets": ["Total Backward Packets", "Tot Bwd Pkts"],
    "Flow Bytes/s": ["Flow Bytes/s", "Flow Byts/s"],
    "Flow Packets/s": ["Flow Packets/s", "Flow Pkts/s"],
    "Flow Duration": ["Flow Duration"],
    "Total Length of Fwd Packets": ["Total Length of Fwd Packets", "TotLen Fwd Pkts"],
    "Total Length of Bwd Packets": ["Total Length of Bwd Packets", "TotLen Bwd Pkts"],
    "Fwd Packet Length Mean": ["Fwd Packet Length Mean", "Fwd Pkt Len Mean"],
    "Label": ["Label", "label"],
}
OPTIONAL_GROUP_ALIASES = {
    "capture_id": ["capture_id", "capture", "Capture", "Capture ID"],
    "day": ["day", "Day", "capture_day", "Capture Day"],
    "attack_subset": ["attack_subset", "Attack Subset", "subset", "Subset"],
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def normalize_columns(frame: pd.DataFrame) -> pd.DataFrame:
    frame = frame.copy()
    # Required explicitly because official CICFlowMeter exports often contain
    # leading whitespace in their headers.
    frame.columns = frame.columns.str.strip()
    if frame.columns.duplicated().any():
        duplicates = frame.columns[frame.columns.duplicated()].tolist()
        raise ValueError(f"Duplicate columns after stripping whitespace: {duplicates}")
    rename = {}
    for canonical, candidates in ALIASES.items():
        found = [name for name in candidates if name in frame.columns]
        if len(found) != 1:
            raise ValueError(f"Expected one column for {canonical}; found {found}; "
                             f"available={list(frame.columns)}")
        rename[found[0]] = canonical
    return frame.rename(columns=rename)


def class_counts(labels: pd.Series) -> dict[str, int]:
    normalized = labels.astype(str).str.strip()
    return {str(key): int(value) for key, value in normalized.value_counts().items()}


def binary_counts(labels: pd.Series) -> dict[str, int]:
    return {"BENIGN": int((labels == 0).sum()), "DDoS": int((labels == 1).sum())}


def prepare(paths: list[Path], per_class: int, seed: int,
            chunk_size: int) -> tuple[pd.DataFrame, dict[str, object]]:
    parts: list[pd.DataFrame] = []
    source_records = []
    retained_group_metadata: set[str] = set()
    raw_class_total: dict[str, int] = {}
    for path in paths:
        digest = sha256(path)
        before, invalid, offset = 0, 0, 0
        source_raw_counts: dict[str, int] = {}
        for raw in pd.read_csv(path, low_memory=False, chunksize=chunk_size):
            frame = normalize_columns(raw)
            before += len(frame)
            for label, count in class_counts(frame["Label"]).items():
                source_raw_counts[label] = source_raw_counts.get(label, 0) + count
                raw_class_total[label] = raw_class_total.get(label, 0) + count
            # Hash the complete normalized raw row before feature reduction so
            # equal 8-feature values do not collapse scientifically distinct rows.
            full_hash = pd.util.hash_pandas_object(frame, index=False).astype("uint64")
            reduced = frame[FEATURES_8 + ["Label"]].copy()
            reduced["source_file"] = path.name
            reduced["source_file_sha256"] = digest
            row_numbers = np.arange(offset, offset + len(frame), dtype=np.int64)
            reduced["source_row_number"] = row_numbers
            reduced["source_row_id"] = [stable_id(digest, int(number))
                                        for number in row_numbers]
            reduced["_full_row_hash"] = full_hash.to_numpy()
            reduced["source_label"] = reduced["Label"].astype(str).str.strip()
            for canonical, candidates in OPTIONAL_GROUP_ALIASES.items():
                found = next((name for name in candidates if name in frame.columns), None)
                if found is not None:
                    reduced[canonical] = frame[found].astype(str).str.strip()
                    retained_group_metadata.add(canonical)
            reduced[FEATURES_8] = reduced[FEATURES_8].apply(pd.to_numeric, errors="coerce")
            reduced.replace([np.inf, -np.inf], np.nan, inplace=True)
            chunk_invalid = reduced[FEATURES_8 + ["Label"]].isna().any(axis=1)
            chunk_invalid |= reduced["source_label"].eq("")
            invalid += int(chunk_invalid.sum())
            reduced = reduced.loc[~chunk_invalid].copy()
            reduced["Label"] = np.where(
                reduced["source_label"].str.upper() == "BENIGN", 0, 1).astype("int8")
            parts.append(reduced)
            offset += len(frame)
        source_records.append({"file": path.name, "input_path": str(path),
                               "sha256": digest, "raw_rows": before,
                               "raw_class_counts": source_raw_counts,
                               "invalid_rows_removed": invalid})
    if not parts:
        raise ValueError("No input rows were read")
    data = pd.concat(parts, ignore_index=True)
    counts_after_cleaning = binary_counts(data["Label"])
    before_duplicates = len(data)
    duplicate_mask = data.duplicated(subset=["_full_row_hash"], keep="first")
    duplicates_by_class = binary_counts(data.loc[duplicate_mask, "Label"])
    data = data.loc[~duplicate_mask].copy()
    duplicates_removed = before_duplicates - len(data)
    counts_unique = binary_counts(data["Label"])
    if min(counts_unique.values()) < per_class:
        raise ValueError(f"Not enough unique records for sampling without replacement: {counts_unique}")
    sampled = pd.concat([
        data[data.Label == label].sample(per_class, random_state=seed, replace=False)
        for label in (0, 1)
    ], ignore_index=True).sample(frac=1, random_state=seed).reset_index(drop=True)
    sampled["sample_id"] = sampled["source_row_id"]
    sampled.drop(columns=["_full_row_hash"], inplace=True)
    manifest: dict[str, object] = {
        "dataset": "CICDDoS2019",
        "input_files": source_records,
        "input_filenames": [path.name for path in paths],
        "features": FEATURES_8,
        "feature_sets": {"4": FEATURES_8[:4], "6": FEATURES_8[:6], "8": FEATURES_8},
        "label_mapping": {"BENIGN": 0, "all_selected_non_BENIGN_attack_labels": 1},
        "raw_class_counts": raw_class_total,
        "binary_class_counts_after_invalid_cleaning": counts_after_cleaning,
        "duplicate_rows_detected_and_removed": int(duplicates_removed),
        "duplicates_by_binary_class": duplicates_by_class,
        "deduplication_procedure": (
            "64-bit pandas hash of every normalized raw CSV column before 8-feature reduction"),
        "unique_class_counts_before_sampling": counts_unique,
        "class_counts_after_sampling": binary_counts(sampled["Label"]),
        "selected_per_class_without_replacement": per_class,
        "sampling_seed": seed,
        "oversampling_or_duplication_used": False,
        "stable_identifier": "sample_id/source_row_id = SHA-256(source-file SHA-256, zero-based row number)",
        "grouping_columns_retained": ["source_file", "source_file_sha256",
                                      *sorted(retained_group_metadata)],
        "output_rows": len(sampled),
    }
    return sampled, manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", nargs="+", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--per-class", type=int, default=400_000)
    parser.add_argument("--seed", type=int, default=104729)
    parser.add_argument("--chunk-size", type=int, default=250_000)
    args = parser.parse_args()
    if args.per_class <= 0:
        raise ValueError("--per-class must be positive")
    for target in (args.output, args.manifest):
        if target.exists():
            raise FileExistsError(f"Refusing to overwrite existing prepared artifact: {target}")
    sampled, manifest = prepare(args.input, args.per_class, args.seed, args.chunk_size)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.output.suffix.lower() == ".csv":
        sampled.to_csv(args.output, index=False)
    else:
        sampled.to_parquet(args.output, index=False)
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(args.output), "rows": len(sampled),
                      "class_counts": manifest["class_counts_after_sampling"],
                      "duplicates_removed": manifest["duplicate_rows_detected_and_removed"]}, indent=2))


if __name__ == "__main__":
    # The journal-revision protocol uses maximum clean unique BENIGN balancing
    # and external-memory exact full-record deduplication.  Keep the legacy
    # helpers above importable for compatibility tests, but route every CLI run
    # through the approved implementation so the obsolete fixed-400k sampler
    # cannot be invoked accidentally.
    from prepare_cicddos2019_max_benign import main as approved_main
    approved_main()
