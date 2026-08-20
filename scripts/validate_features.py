#!/usr/bin/env python3
"""Validate labelled OMNeT++ feature CSVs and emit an auditable summary."""
from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path

from pipeline_common import FEATURES_8, LABEL_TO_INT, RoleMapping, TRAFFIC_SOURCES

DEFAULT_ROLE_CONFIG = Path(__file__).resolve().parents[1] / "config" / "ip_roles.json"
REQUIRED_METADATA = ["flow_id", "run", "scenario", "protocol", "src_ip", "src_port",
                     "dst_ip", "dst_port", "ground_truth_label", "traffic_source"]


def _number(row: dict[str, str], column: str, row_number: int,
            allow_empty: bool = False) -> float | None:
    text = str(row.get(column, "")).strip()
    if not text and allow_empty:
        return None
    try:
        value = float(text)
    except ValueError as exc:
        raise ValueError(f"row {row_number}: {column} is not numeric: {text!r}") from exc
    if not math.isfinite(value):
        raise ValueError(f"row {row_number}: {column} must be finite")
    return value


def validate_csv(path: Path, roles: RoleMapping) -> dict[str, object]:
    with path.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        missing = [name for name in REQUIRED_METADATA + FEATURES_8
                   if name not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f"{path}: missing required columns: {missing}")
        seen_ids, benign, ddos, zero_duration, rows = set(), 0, 0, 0, 0
        for row_number, row in enumerate(reader, start=2):
            rows += 1
            flow_id = row["flow_id"]
            if not flow_id or flow_id in seen_ids:
                raise ValueError(f"{path}: row {row_number}: empty or duplicate flow_id")
            seen_ids.add(flow_id)
            label, source = row["ground_truth_label"], row["traffic_source"]
            if label not in LABEL_TO_INT or source not in TRAFFIC_SOURCES:
                raise ValueError(f"{path}: row {row_number}: invalid label/source {label!r}/{source!r}")
            benign += label == "BENIGN"
            ddos += label == "DDoS"
            counts = [_number(row, name, row_number)
                      for name in ("Total Fwd Packets", "Total Backward Packets")]
            if any(value is None or value < 0 or not value.is_integer() for value in counts):
                raise ValueError(f"{path}: row {row_number}: packet counts must be nonnegative integers")
            duration = _number(row, "Flow Duration", row_number)
            fwd_length = _number(row, "Total Length of Fwd Packets", row_number)
            bwd_length = _number(row, "Total Length of Bwd Packets", row_number)
            fwd_mean = _number(row, "Fwd Packet Length Mean", row_number, allow_empty=True)
            if any(value is not None and value < 0
                   for value in (duration, fwd_length, bwd_length, fwd_mean)):
                raise ValueError(f"{path}: row {row_number}: duration/lengths must be nonnegative")
            bytes_rate = _number(row, "Flow Bytes/s", row_number, allow_empty=True)
            packets_rate = _number(row, "Flow Packets/s", row_number, allow_empty=True)
            if duration == 0:
                zero_duration += 1
                if bytes_rate is not None or packets_rate is not None:
                    raise ValueError(f"{path}: row {row_number}: zero-duration rates must be empty")
            elif bytes_rate is None or packets_rate is None or bytes_rate < 0 or packets_rate < 0:
                raise ValueError(f"{path}: row {row_number}: positive duration requires finite rates")
            proto = {"TCP": 6, "UDP": 17}.get(row["protocol"].upper())
            if proto is None:
                raise ValueError(f"{path}: row {row_number}: invalid protocol {row['protocol']!r}")
            expected = roles.classify(proto, row["src_ip"], int(row["src_port"]),
                                      row["dst_ip"], int(row["dst_port"]))
            if (label, source) != expected:
                raise ValueError(f"{path}: row {row_number}: expected {expected}, "
                                 f"found {(label, source)}")
    return {"file": str(path), "rows": rows, "benign": int(benign), "ddos": int(ddos),
            "zero_duration": zero_duration, "unknown_or_invalid_flows": 0}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", nargs="+", required=True, type=Path)
    parser.add_argument("--role-config", type=Path, default=DEFAULT_ROLE_CONFIG)
    parser.add_argument("--summary", type=Path)
    args = parser.parse_args()
    if args.summary and args.summary.exists():
        raise FileExistsError(f"Refusing to overwrite existing validation summary: {args.summary}")
    roles = RoleMapping(args.role_config)
    records = [validate_csv(path, roles) for path in args.input]
    summary = {"files": records, "total_rows": sum(item["rows"] for item in records),
               "unknown_or_invalid_flows": 0, "status": "valid"}
    rendered = json.dumps(summary, indent=2)
    if args.summary:
        args.summary.parent.mkdir(parents=True, exist_ok=True)
        args.summary.write_text(rendered, encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
