#!/usr/bin/env python3
"""Read-only, chunked inventory of the official CICDDoS2019 source files."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import platform
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from pipeline_common import FEATURES_8
from prepare_cicddos2019 import ALIASES


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def json_text(value: object) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False)


def resolve_columns(original_columns: list[str]) -> tuple[dict[str, str], list[str]]:
    stripped = [name.strip() for name in original_columns]
    duplicates = sorted(name for name, count in Counter(stripped).items() if count > 1)
    resolved: dict[str, str] = {}
    for canonical, candidates in ALIASES.items():
        found = [name for name in candidates if name in stripped]
        if len(found) == 1:
            resolved[canonical] = original_columns[stripped.index(found[0])]
    return resolved, duplicates


def inventory_file(path: Path, root: Path, chunk_size: int) -> tuple[
        dict[str, object], list[dict[str, object]], list[dict[str, object]],
        list[dict[str, object]]]:
    stat_before = path.stat()
    digest = file_sha256(path)
    header = pd.read_csv(path, nrows=0)
    original_columns = [str(name) for name in header.columns]
    resolved, duplicate_stripped = resolve_columns(original_columns)
    missing_required = [name for name in [*FEATURES_8, "Label"] if name not in resolved]

    column_records = [{
        "relative_path": path.relative_to(root).as_posix(),
        "ordinal": ordinal,
        "original_header": original,
        "stripped_header": original.strip(),
        "had_surrounding_whitespace": original != original.strip(),
    } for ordinal, original in enumerate(original_columns)]

    rows = 0
    duplicate_rows = 0
    seen_hashes: set[int] = set()
    labels: Counter[str] = Counter()
    blank_values_by_column: Counter[str] = Counter()
    invalid_by_feature = {
        feature: {"blank": 0, "nonnumeric_or_missing_token": 0,
                  "positive_infinity": 0, "negative_infinity": 0}
        for feature in FEATURES_8
    }
    invalid_required_rows = 0
    blank_labels = 0

    for frame in pd.read_csv(
            path, dtype=str, keep_default_na=False, na_filter=False,
            chunksize=chunk_size, low_memory=False):
        rows += len(frame)
        text_frame = frame.astype("string")
        hashes = pd.util.hash_pandas_object(text_frame, index=False).to_numpy(dtype=np.uint64)
        unique_hashes, counts = np.unique(hashes, return_counts=True)
        already_seen = np.fromiter(
            (int(value) in seen_hashes for value in unique_hashes),
            dtype=bool, count=len(unique_hashes))
        duplicate_rows += int(counts[already_seen].sum())
        duplicate_rows += int((counts[~already_seen] - 1).sum())
        seen_hashes.update(int(value) for value in unique_hashes[~already_seen])

        stripped_frame = text_frame.apply(lambda series: series.str.strip())
        for name in original_columns:
            blank_values_by_column[name] += int(stripped_frame[name].eq("").sum())

        if "Label" in resolved:
            label_values = stripped_frame[resolved["Label"]]
            blank_labels += int(label_values.eq("").sum())
            labels.update(str(value) if value else "<BLANK>" for value in label_values)

        row_invalid = np.zeros(len(frame), dtype=bool)
        for feature in FEATURES_8:
            source = resolved.get(feature)
            if source is None:
                row_invalid[:] = True
                continue
            values = stripped_frame[source]
            blank = values.eq("").to_numpy()
            numeric = pd.to_numeric(values.mask(blank), errors="coerce")
            numeric_array = numeric.to_numpy(dtype=float, na_value=np.nan)
            nan = np.isnan(numeric_array)
            posinf = np.isposinf(numeric_array)
            neginf = np.isneginf(numeric_array)
            nonnumeric = nan & ~blank
            invalid_by_feature[feature]["blank"] += int(blank.sum())
            invalid_by_feature[feature]["nonnumeric_or_missing_token"] += int(nonnumeric.sum())
            invalid_by_feature[feature]["positive_infinity"] += int(posinf.sum())
            invalid_by_feature[feature]["negative_infinity"] += int(neginf.sum())
            row_invalid |= blank | nan | posinf | neginf
        if "Label" not in resolved:
            row_invalid[:] = True
        else:
            row_invalid |= stripped_frame[resolved["Label"]].eq("").to_numpy()
        invalid_required_rows += int(row_invalid.sum())

    stat_after = path.stat()
    unchanged = (stat_before.st_size == stat_after.st_size and
                 stat_before.st_mtime_ns == stat_after.st_mtime_ns)
    relative = path.relative_to(root).as_posix()
    label_records = [{
        "relative_path": relative,
        "source_label": label,
        "binary_label": "BENIGN" if label.upper() == "BENIGN" else (
            "UNMAPPED" if label == "<BLANK>" else "DDoS"),
        "row_count": count,
    } for label, count in sorted(labels.items())]
    invalid_records = []
    for feature in FEATURES_8:
        invalid_records.append({
            "relative_path": relative,
            "canonical_feature": feature,
            "source_header": resolved.get(feature, ""),
            **invalid_by_feature[feature],
            "invalid_total": sum(invalid_by_feature[feature].values()),
        })

    record: dict[str, object] = {
        "relative_path": relative,
        "day": relative.split("/", 1)[0],
        "filename": path.name,
        "extension": path.suffix,
        "size_bytes": stat_before.st_size,
        "modified_time_utc": datetime.fromtimestamp(
            stat_before.st_mtime, timezone.utc).isoformat(),
        "sha256": digest,
        "row_count": rows,
        "column_count": len(original_columns),
        "columns_json": json_text(original_columns),
        "stripped_columns_json": json_text([name.strip() for name in original_columns]),
        "headers_with_surrounding_whitespace": sum(
            name != name.strip() for name in original_columns),
        "duplicate_headers_after_strip_json": json_text(duplicate_stripped),
        "resolved_required_columns_json": json_text(resolved),
        "missing_required_columns_json": json_text(missing_required),
        "labels_json": json_text(dict(sorted(labels.items()))),
        "benign_rows": labels.get("BENIGN", 0),
        "ddos_rows": sum(count for label, count in labels.items()
                         if label.upper() != "BENIGN" and label != "<BLANK>"),
        "blank_label_rows": blank_labels,
        "duplicate_rows_within_file": duplicate_rows,
        "unique_raw_row_hashes": len(seen_hashes),
        "invalid_required8_or_label_rows": invalid_required_rows,
        "blank_values_all_columns": sum(blank_values_by_column.values()),
        "blank_values_by_column_json": json_text(dict(sorted(blank_values_by_column.items()))),
        "source_unchanged_during_inventory": unchanged,
        "status": "valid" if not missing_required and not duplicate_stripped and unchanged else "invalid",
    }
    return record, column_records, label_records, invalid_records


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        raise ValueError(f"No rows available for {path.name}")
    with path.open("x", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--chunk-size", type=int, default=100_000)
    args = parser.parse_args()
    root = args.root.resolve()
    files = sorted(path for day in (root / "day1", root / "day2")
                   for path in day.rglob("*") if path.is_file())
    if not files:
        raise ValueError(f"No files found below {root / 'day1'} and {root / 'day2'}")
    if args.output_dir.exists():
        raise FileExistsError(f"Refusing to overwrite inventory directory: {args.output_dir}")
    args.output_dir.mkdir(parents=True)

    records: list[dict[str, object]] = []
    columns: list[dict[str, object]] = []
    labels: list[dict[str, object]] = []
    invalid_values: list[dict[str, object]] = []
    for index, path in enumerate(files, 1):
        print(f"[{index}/{len(files)}] inventory {path.relative_to(root).as_posix()}", flush=True)
        record, file_columns, file_labels, file_invalid = inventory_file(
            path, root, args.chunk_size)
        records.append(record)
        columns.extend(file_columns)
        labels.extend(file_labels)
        invalid_values.extend(file_invalid)
        print(f"  rows={record['row_count']} duplicates={record['duplicate_rows_within_file']} "
              f"invalid={record['invalid_required8_or_label_rows']} status={record['status']}",
              flush=True)

    write_csv(args.output_dir / "files.csv", records)
    write_csv(args.output_dir / "columns.csv", columns)
    write_csv(args.output_dir / "labels.csv", labels)
    write_csv(args.output_dir / "invalid_values.csv", invalid_values)
    aggregate_labels: Counter[str] = Counter()
    for row in labels:
        aggregate_labels[str(row["source_label"])] += int(row["row_count"])
    summary = {
        "status": "valid" if all(row["status"] == "valid" for row in records) else "invalid",
        "dataset": "CICDDoS2019",
        "provenance": "Official CICDDoS2019 files supplied locally by the author",
        "source_root": str(root),
        "source_subdirectories": ["day1", "day2"],
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "python_executable": sys.executable,
        "python_version": platform.python_version(),
        "pandas_version": pd.__version__,
        "numpy_version": np.__version__,
        "file_count": len(records),
        "total_size_bytes": sum(int(row["size_bytes"]) for row in records),
        "total_rows": sum(int(row["row_count"]) for row in records),
        "aggregate_source_labels": dict(sorted(aggregate_labels.items())),
        "aggregate_binary_labels": {
            "BENIGN": sum(int(row["benign_rows"]) for row in records),
            "DDoS": sum(int(row["ddos_rows"]) for row in records),
        },
        "duplicate_rows_within_files": sum(
            int(row["duplicate_rows_within_file"]) for row in records),
        "invalid_required8_or_label_rows": sum(
            int(row["invalid_required8_or_label_rows"]) for row in records),
        "files_with_missing_required_columns": [
            row["relative_path"] for row in records
            if json.loads(str(row["missing_required_columns_json"]))],
        "files_unchanged_during_inventory": all(
            bool(row["source_unchanged_during_inventory"]) for row in records),
        "duplicate_definition": (
            "Repeated 64-bit pandas hash of the complete parsed raw text row, counted "
            "within each source file; cross-file duplicates are deferred to preparation."),
        "invalid_definition": (
            "A row with a blank/nonnumeric/nonfinite canonical 8-feature value or blank label."),
        "outputs": ["files.csv", "columns.csv", "labels.csv", "invalid_values.csv"],
    }
    summary_path = args.output_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False), flush=True)
    if summary["status"] != "valid":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
