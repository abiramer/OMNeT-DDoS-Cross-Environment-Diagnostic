#!/usr/bin/env python3
"""Independently validate the approved maximum-BENIGN preparation artifacts."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
from datetime import datetime, timezone
from pathlib import Path

import duckdb
import pandas as pd

from pipeline_common import DEFAULT_SEEDS, FEATURES_8


def qstr(value: object) -> str:
    return "'" + str(value).replace("'", "''") + "'"


def qid(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


class Checks:
    def __init__(self) -> None:
        self.rows: list[dict[str, object]] = []

    def require(self, name: str, condition: bool, detail: str) -> None:
        self.rows.append({"check": name, "status": "pass" if condition else "fail",
                          "detail": detail})
        if not condition:
            raise AssertionError(f"{name}: {detail}")


def one(connection: duckdb.DuckDBPyConnection, sql: str) -> int:
    return int(connection.execute(sql).fetchone()[0])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preparation-dir", required=True, type=Path)
    parser.add_argument("--validated-inventory", required=True, type=Path)
    parser.add_argument("--source-root", required=True, type=Path)
    parser.add_argument("--expected-seeds", nargs="+", type=int, default=DEFAULT_SEEDS)
    args = parser.parse_args()
    if platform.python_version() != "3.10.5":
        raise RuntimeError(f"Validation requires Python 3.10.5, found {platform.python_version()}")

    root = args.preparation_dir.resolve()
    manifest_path = root / "preparation_manifest.json"
    validation_path = root / "preparation_validation.json"
    checks_path = root / "preparation_validation_checks.csv"
    if validation_path.exists() or checks_path.exists():
        raise FileExistsError("Refusing to overwrite existing independent validation output")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    inventory = json.loads(args.validated_inventory.read_text(encoding="utf-8"))
    checks = Checks()
    checks.require("preparation_pending_validation",
                   manifest.get("status") == "prepared_pending_independent_validation",
                   f"status={manifest.get('status')!r}")
    checks.require("validated_inventory", inventory.get("status") == "valid",
                   f"status={inventory.get('status')!r}")

    output_names = {
        "prepared": "cicddos2019-max-benign-feature8.parquet",
        "selected": "selected_rows.parquet",
        "splits": "split_manifest.parquet",
        "cleaning": "cleaning_counts.csv",
        "dedup": "deduplication_counts.csv",
        "allocation": "ddos_sampling_allocation.csv",
        "composition": "group_split_composition.csv",
        "leakage": "leakage_checks.csv",
    }
    paths = {key: root / value for key, value in output_names.items()}
    for key, expected in manifest["output_hashes_sha256"].items():
        actual = sha256_file(paths[key])
        checks.require(f"artifact_hash_{key}", actual == expected,
                       f"expected={expected} actual={actual}")

    inventory_by_file = {item["relative_path"]: item
                         for item in inventory["preparation_input_files"]}
    inventory_files = set(inventory_by_file)
    source_root = args.source_root.resolve()
    current_sizes_ok = True
    missing_sources: list[str] = []
    for relative, item in inventory_by_file.items():
        path = source_root / relative
        if not path.is_file():
            missing_sources.append(relative)
            current_sizes_ok = False
        elif path.stat().st_size != int(item["size_bytes"]):
            current_sizes_ok = False
    checks.require("raw_source_files_present_and_sizes_unchanged", current_sizes_ok,
                   f"checked={len(inventory_files)} missing={missing_sources}")

    database = Path(manifest["database"])
    checks.require("preparation_database_present", database.is_file(), str(database))
    connection = duckdb.connect(str(database), read_only=True)
    prepared = f"read_parquet({qstr(paths['prepared'].as_posix())})"
    selected = f"read_parquet({qstr(paths['selected'].as_posix())})"
    splits = f"read_parquet({qstr(paths['splits'].as_posix())})"
    n = int(manifest["N"])

    counts = tuple(map(int, connection.execute(f"""
        SELECT count(*), count(*) FILTER (WHERE Label=0),
               count(*) FILTER (WHERE Label=1), count(DISTINCT sample_id),
               count(DISTINCT source_row_id), count(DISTINCT row_hash)
        FROM {prepared}
    """).fetchone()))
    checks.require("prepared_balanced_unique", counts == (2*n, n, n, 2*n, 2*n, 2*n),
                   f"observed={counts} expected={(2*n, n, n, 2*n, 2*n, 2*n)}")
    finite = " AND ".join(f"isfinite({qid(feature)})" for feature in FEATURES_8)
    checks.require("feature8_all_finite", one(connection,
                   f"SELECT count(*) FROM {prepared} WHERE NOT ({finite})") == 0,
                   f"features={FEATURES_8}")
    prepared_columns = set(connection.execute(f"DESCRIBE SELECT * FROM {prepared}").df()["column_name"])
    checks.require("feature8_and_provenance_columns_present",
                   set(FEATURES_8 + ["Label", "sample_id", "source_row_id", "row_hash",
                       "source_file", "source_file_sha256", "source_row_number", "day",
                       "source_group", "attack_type", "sampling_seed"]).issubset(prepared_columns),
                   f"columns={sorted(prepared_columns)}")

    selected_mismatch = one(connection, f"""
        SELECT count(*) FROM (
          (SELECT sample_id, source_row_id, row_hash, source_file, source_file_sha256,
                  source_row_number, day, source_group, attack_type, Label,
                  selection_reason, sampling_seed, sampling_rank FROM {prepared})
          EXCEPT ALL
          (SELECT * FROM {selected})
        )
    """)
    reverse_mismatch = one(connection, f"""
        SELECT count(*) FROM (
          (SELECT * FROM {selected}) EXCEPT ALL
          (SELECT sample_id, source_row_id, row_hash, source_file, source_file_sha256,
                  source_row_number, day, source_group, attack_type, Label,
                  selection_reason, sampling_seed, sampling_rank FROM {prepared})
        )
    """)
    checks.require("prepared_selected_manifests_match",
                   selected_mismatch == 0 and reverse_mismatch == 0,
                   f"prepared_minus_selected={selected_mismatch} reverse={reverse_mismatch}")

    all_benign_missing = one(connection, """
        SELECT count(*) FROM (
          SELECT source_row_id FROM ranked_records
          WHERE duplicate_rank=1 AND Label_binary=0
          EXCEPT SELECT source_row_id FROM selected_records WHERE Label_binary=0
        )
    """)
    extra_benign = one(connection, """
        SELECT count(*) FROM selected_records
        WHERE Label_binary=0 AND (duplicate_rank<>1 OR selection_reason<>'all_clean_unique_benign')
    """)
    checks.require("all_and_only_unique_clean_benign_retained",
                   all_benign_missing == 0 and extra_benign == 0,
                   f"missing={all_benign_missing} invalid_selected={extra_benign}")
    attack_invalid = one(connection, """
        SELECT count(*) FROM selected_records s
        LEFT JOIN ddos_allocations d USING(day, source_file, source_label)
        WHERE s.Label_binary=1 AND
          (d.allocated_ddos IS NULL OR s.duplicate_rank<>1 OR s.sampling_rank IS NULL OR
           s.sampling_rank>d.allocated_ddos OR
           s.selection_reason<>'deterministic_hamilton_stratified_without_replacement')
    """)
    checks.require("ddos_without_replacement_within_allocation", attack_invalid == 0,
                   f"invalid_selected_attack_rows={attack_invalid}")
    allocation_mismatch = one(connection, """
        SELECT count(*) FROM (
          SELECT d.day, d.source_file, d.source_label, d.allocated_ddos,
                 count(s.source_row_id) AS selected_count
          FROM ddos_allocations d LEFT JOIN selected_records s
            ON s.day=d.day AND s.source_file=d.source_file
            AND s.source_label=d.source_label AND s.Label_binary=1
          GROUP BY ALL HAVING selected_count<>d.allocated_ddos
        )
    """)
    checks.require("ddos_stratum_allocations_exact", allocation_mismatch == 0,
                   f"mismatched_strata={allocation_mismatch}")
    collision_or_duplicate = one(connection, """
        SELECT count(*) FROM (
          SELECT row_hash FROM ranked_records WHERE duplicate_rank=1
          GROUP BY row_hash HAVING count(*)>1
        )
    """)
    selected_nonrepresentative = one(connection,
        "SELECT count(*) FROM selected_records WHERE duplicate_rank<>1")
    checks.require("no_hash_collision_or_exact_duplicate_selected",
                   collision_or_duplicate == 0 and selected_nonrepresentative == 0,
                   f"unique_hash_collisions={collision_or_duplicate} "
                   f"nonrepresentatives={selected_nonrepresentative}")

    selected_source_rows = connection.execute(f"""
        SELECT DISTINCT source_file, source_file_sha256 FROM {selected}
    """).fetchall()
    bad_source_metadata = [(source_file, file_hash) for source_file, file_hash in selected_source_rows
                           if source_file not in inventory_by_file or
                           inventory_by_file[source_file]["sha256"] != file_hash]
    checks.require("selected_source_provenance_matches_inventory", not bad_source_metadata,
                   f"selected_files={len(selected_source_rows)} mismatches={bad_source_metadata[:3]}")

    cleaning = pd.read_csv(paths["cleaning"])
    dedup = pd.read_csv(paths["dedup"])
    allocations = pd.read_csv(paths["allocation"])
    checks.require("cleaning_reconciles_raw_inventory",
                   int(cleaning.raw_rows.sum()) == int(inventory["total_data_rows"]) and
                   bool((cleaning.raw_rows == cleaning.clean_valid_rows + cleaning.invalid_rows).all()),
                   f"raw={int(cleaning.raw_rows.sum())} inventory={inventory['total_data_rows']}")
    checks.require("dedup_reconciles_cleaning",
                   int(dedup.clean_valid_rows.sum()) == int(cleaning.clean_valid_rows.sum()) and
                   bool((dedup.clean_valid_rows == dedup.clean_unique_rows +
                         dedup.exact_duplicates_removed).all()),
                   f"dedup_clean={int(dedup.clean_valid_rows.sum())} "
                   f"cleaning_clean={int(cleaning.clean_valid_rows.sum())}")
    checks.require("allocation_sums_to_N_and_is_within_capacity",
                   int(allocations.allocated_ddos.sum()) == n and
                   bool((allocations.allocated_ddos <= allocations.available_unique_ddos).all()),
                   f"allocated={int(allocations.allocated_ddos.sum())} N={n}")

    expected_seeds = list(dict.fromkeys(args.expected_seeds))
    split_seeds = sorted(map(int, connection.execute(
        f"SELECT DISTINCT seed FROM {splits} ORDER BY seed").fetchnumpy()["seed"]))
    checks.require("exact_expected_split_seeds", split_seeds == sorted(expected_seeds),
                   f"observed={split_seeds} expected={sorted(expected_seeds)}")
    split_rows = one(connection, f"SELECT count(*) FROM {splits}")
    checks.require("every_seed_contains_exact_same_selected_rows",
                   split_rows == 2*n*len(expected_seeds) and one(connection, f"""
                      SELECT count(*) FROM (
                        SELECT sample_id FROM {splits}
                        GROUP BY sample_id
                        HAVING count(*)<>{len(expected_seeds)} OR
                               count(DISTINCT seed)<>{len(expected_seeds)}
                      )
                   """) == 0,
                   f"rows={split_rows} expected={2*n*len(expected_seeds)}")
    missing_or_extra = one(connection, f"""
        SELECT count(*) FROM (
          SELECT seed, sample_id FROM {splits}
          EXCEPT SELECT seeds.seed, s.sample_id
                 FROM (SELECT DISTINCT seed FROM {splits}) seeds CROSS JOIN {selected} s
        )
    """) + one(connection, f"""
        SELECT count(*) FROM (
          SELECT seeds.seed, s.sample_id
          FROM (SELECT DISTINCT seed FROM {splits}) seeds CROSS JOIN {selected} s
          EXCEPT SELECT seed, sample_id FROM {splits}
        )
    """)
    checks.require("split_sample_set_equals_selection", missing_or_extra == 0,
                   f"set_differences={missing_or_extra}")
    invalid_partition = one(connection, f"""
        SELECT count(*) FROM {splits} WHERE partition NOT IN ('train','test')
    """)
    split_class_failures = one(connection, f"""
        SELECT count(*) FROM (
          SELECT seed, partition, count(DISTINCT Label) labels
          FROM {splits} GROUP BY seed, partition HAVING labels<>2
        )
    """)
    row_overlap = one(connection, f"""
        SELECT count(*) FROM (
          SELECT seed, row_hash FROM {splits}
          GROUP BY seed, row_hash HAVING count(DISTINCT partition)>1
        )
    """)
    id_overlap = one(connection, f"""
        SELECT count(*) FROM (
          SELECT seed, sample_id FROM {splits}
          GROUP BY seed, sample_id HAVING count(DISTINCT partition)>1 OR count(*)>1
        )
    """)
    group_overlap = one(connection, f"""
        SELECT count(*) FROM (
          SELECT seed, source_group FROM {splits}
          GROUP BY seed, source_group HAVING count(DISTINCT partition)>1
        )
    """)
    checks.require("class_preserving_group_only_splits",
                   invalid_partition == 0 and split_class_failures == 0,
                   f"invalid_partitions={invalid_partition} class_failures={split_class_failures}")
    checks.require("zero_row_id_hash_and_source_group_overlap",
                   row_overlap == id_overlap == group_overlap == 0,
                   f"row_hash={row_overlap} sample_id={id_overlap} source_group={group_overlap}")

    split_id_failures = 0
    for seed in expected_seeds:
        rows = connection.execute(f"""
            SELECT DISTINCT split_id FROM {splits} WHERE seed={int(seed)}
        """).fetchall()
        test_groups = [row[0] for row in connection.execute(f"""
            SELECT DISTINCT source_group FROM {splits}
            WHERE seed={int(seed)} AND partition='test' ORDER BY source_group
        """).fetchall()]
        expected_id = hashlib.sha256(
            (str(seed) + "\x1e" + "\x1f".join(test_groups)).encode()).hexdigest()
        if len(rows) != 1 or rows[0][0] != expected_id:
            split_id_failures += 1
    checks.require("split_ids_recomputed", split_id_failures == 0,
                   f"failures={split_id_failures}")

    composition = pd.read_csv(paths["composition"])
    split_composition = connection.execute(f"""
        SELECT seed, split_id, partition, day, source_file, attack_type,
               CASE WHEN Label=0 THEN 'BENIGN' ELSE 'DDoS' END binary_class,
               count(*)::BIGINT AS "rows"
        FROM {splits} GROUP BY ALL ORDER BY ALL
    """).df()
    composition = composition.sort_values(list(split_composition.columns)).reset_index(drop=True)
    checks.require("group_composition_reconciles_split_manifest",
                   composition.equals(split_composition),
                   f"csv_rows={len(composition)} recomputed_rows={len(split_composition)}")
    connection.close()

    result = {
        "status": "valid",
        "validated_utc": datetime.now(timezone.utc).isoformat(),
        "N": n,
        "selected_total": 2*n,
        "split_seeds": expected_seeds,
        "prepared_manifest_sha256": sha256_file(manifest_path),
        "prepared_dataset_sha256": manifest["output_hashes_sha256"]["prepared"],
        "selected_rows_sha256": manifest["output_hashes_sha256"]["selected"],
        "split_manifest_sha256": manifest["output_hashes_sha256"]["splits"],
        "raw_sources_rehashed": False,
        "raw_source_integrity_basis": (
            "Previously validated SHA-256 inventory plus current presence/byte-size checks; "
            "selected provenance hashes were matched to that inventory."),
        "checks_passed": len(checks.rows),
        "checks_failed": 0,
    }
    checks_frame = pd.DataFrame(checks.rows)
    checks_frame.to_csv(checks_path, index=False)
    result["checks_csv_sha256"] = sha256_file(checks_path)
    with validation_path.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
