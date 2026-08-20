#!/usr/bin/env python3
"""Validate a completed CICDDoS2019 inventory without reopening CSV contents."""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def truth(value: object) -> bool:
    return str(value).strip().lower() == "true"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--inventory-dir", type=Path, required=True)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(f"Refusing to overwrite validated inventory: {args.output}")

    files = pd.read_csv(args.inventory_dir / "files.csv", dtype=str, keep_default_na=False)
    labels = pd.read_csv(args.inventory_dir / "labels.csv", dtype=str, keep_default_na=False)
    invalid = pd.read_csv(
        args.inventory_dir / "invalid_values.csv", dtype=str, keep_default_na=False)
    original_summary = json.loads((args.inventory_dir / "summary.json").read_text(encoding="utf-8"))
    required_file_columns = {
        "relative_path", "size_bytes", "modified_time_utc", "sha256", "row_count",
        "column_count", "status", "missing_required_columns_json",
        "duplicate_headers_after_strip_json", "source_unchanged_during_inventory",
        "duplicate_rows_within_file", "invalid_required8_or_label_rows",
    }
    missing_inventory_columns = sorted(required_file_columns - set(files.columns))
    if missing_inventory_columns:
        raise ValueError(f"files.csv lacks columns: {missing_inventory_columns}")

    is_lock = files["relative_path"].map(
        lambda value: Path(value).name.startswith(".~lock.") and value.endswith(".csv#"))
    is_csv = files["relative_path"].str.lower().str.endswith(".csv") & ~is_lock
    unknown = files.loc[~is_csv & ~is_lock, "relative_path"].tolist()
    if unknown:
        raise ValueError(f"Unclassified recursively inventoried files: {unknown}")
    data_files = files.loc[is_csv].copy()
    lock_files = files.loc[is_lock].copy()
    if len(data_files) != 18:
        raise ValueError(f"Expected 18 data CSVs; found {len(data_files)}")
    if len(lock_files) != 1:
        raise ValueError(f"Expected one preserved ancillary lock file; found {len(lock_files)}")

    failures: list[str] = []
    source_root = args.source_root.resolve()
    discovered = sorted(
        path.relative_to(source_root).as_posix()
        for day in (source_root / "day1", source_root / "day2")
        for path in day.rglob("*") if path.is_file())
    recorded = sorted(files["relative_path"].tolist())
    if discovered != recorded:
        failures.append("Current recursive file list differs from the completed inventory")

    for row in files.to_dict("records"):
        path = source_root / str(row["relative_path"])
        if not path.is_file():
            failures.append(f"Missing source: {row['relative_path']}")
            continue
        stat = path.stat()
        current_mtime = datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat()
        if stat.st_size != int(row["size_bytes"]):
            failures.append(f"Size changed: {row['relative_path']}")
        if current_mtime != row["modified_time_utc"]:
            failures.append(f"Modification time changed: {row['relative_path']}")
        if not SHA256_RE.fullmatch(str(row["sha256"])):
            failures.append(f"Invalid recorded SHA-256: {row['relative_path']}")
        if not truth(row["source_unchanged_during_inventory"]):
            failures.append(f"Source changed during inventory: {row['relative_path']}")

    for row in data_files.to_dict("records"):
        if row["status"] != "valid":
            failures.append(f"Invalid data CSV status: {row['relative_path']}")
        if int(row["row_count"]) <= 0 or int(row["column_count"]) != 88:
            failures.append(f"Unexpected dimensions: {row['relative_path']}")
        if json.loads(row["missing_required_columns_json"]):
            failures.append(f"Missing required columns: {row['relative_path']}")
        if json.loads(row["duplicate_headers_after_strip_json"]):
            failures.append(f"Duplicate stripped headers: {row['relative_path']}")
        if int(row["duplicate_rows_within_file"]) > int(row["row_count"]):
            failures.append(f"Impossible duplicate count: {row['relative_path']}")
        if int(row["invalid_required8_or_label_rows"]) > int(row["row_count"]):
            failures.append(f"Impossible invalid-row count: {row['relative_path']}")

    lock = lock_files.iloc[0]
    if int(lock["size_bytes"]) > 1024 or int(lock["row_count"]) != 0:
        failures.append("Ancillary lock file is not a small zero-row metadata artifact")

    label_totals = Counter()
    for row in labels.to_dict("records"):
        label_totals[str(row["source_label"])] += int(row["row_count"])
    if dict(sorted(label_totals.items())) != original_summary["aggregate_source_labels"]:
        failures.append("Label totals do not reconcile with summary.json")
    if int(data_files["row_count"].astype("int64").sum()) != int(original_summary["total_rows"]):
        failures.append("Data row totals do not reconcile with summary.json")
    data_paths = set(data_files["relative_path"])
    data_invalid = invalid.loc[invalid["relative_path"].isin(data_paths)]
    ancillary_invalid = invalid.loc[~invalid["relative_path"].isin(data_paths)]
    if len(data_invalid) != len(data_files) * 8:
        failures.append(
            f"Expected {len(data_files) * 8} data-file per-feature invalid records; "
            f"found {len(data_invalid)}")
    if set(ancillary_invalid["relative_path"]) != set(lock_files["relative_path"]):
        failures.append("Per-feature ancillary records do not match classified lock files")

    if failures:
        raise ValueError("Inventory validation failed:\n- " + "\n- ".join(failures))

    preparation_inputs = [{
        "relative_path": row["relative_path"],
        "size_bytes": int(row["size_bytes"]),
        "sha256": row["sha256"],
        "rows": int(row["row_count"]),
        "duplicate_rows_within_file": int(row["duplicate_rows_within_file"]),
        "invalid_required8_or_label_rows": int(row["invalid_required8_or_label_rows"]),
    } for row in data_files.sort_values("relative_path").to_dict("records")]
    result = {
        "status": "valid",
        "dataset": "CICDDoS2019",
        "provenance": original_summary["provenance"],
        "validated_utc": datetime.now(timezone.utc).isoformat(),
        "inventory_directory": str(args.inventory_dir.resolve()),
        "source_root": str(source_root),
        "recursive_files_recorded": len(files),
        "data_csv_files_validated": len(data_files),
        "data_csv_files_by_day": {
            day: int(data_files["relative_path"].str.startswith(day + "/").sum())
            for day in ("day1", "day2")
        },
        "ancillary_files_preserved": [{
            "relative_path": lock["relative_path"],
            "classification": "LibreOffice-style lock metadata; not a CICFlowMeter data CSV",
            "size_bytes": int(lock["size_bytes"]),
            "sha256": lock["sha256"],
            "excluded_from_preparation": True,
        }],
        "total_data_rows": int(data_files["row_count"].astype("int64").sum()),
        "source_label_counts": original_summary["aggregate_source_labels"],
        "binary_label_counts_before_cleaning": original_summary["aggregate_binary_labels"],
        "duplicate_rows_within_files": int(
            data_files["duplicate_rows_within_file"].astype("int64").sum()),
        "invalid_required8_or_label_rows": int(
            data_files["invalid_required8_or_label_rows"].astype("int64").sum()),
        "all_data_files_have_8_feature_superset_and_label": True,
        "all_source_sizes_and_timestamps_unchanged": True,
        "sha256_recorded_for_every_recursive_file": True,
        "cross_file_duplicates_computed": False,
        "cross_file_duplicate_reason": "Deferred to preparation over matched full-row hashes.",
        "preparation_input_files": preparation_inputs,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
