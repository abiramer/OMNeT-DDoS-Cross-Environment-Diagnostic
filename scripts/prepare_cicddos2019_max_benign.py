#!/usr/bin/env python3
"""External-memory CICDDoS2019 preparation using maximum unique BENIGN N."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from sklearn.model_selection import GroupShuffleSplit

from pipeline_common import DEFAULT_SEEDS, FEATURES_8, package_versions


def qid(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def qstr(value: object) -> str:
    return "'" + str(value).replace("'", "''") + "'"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json_new(path: Path, value: object) -> None:
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False)


def table_exists(connection: duckdb.DuckDBPyConnection, name: str) -> bool:
    return bool(connection.execute(
        "SELECT count(*) FROM information_schema.tables WHERE table_name = ?", [name]
    ).fetchone()[0])


def normalized_expr(column: str) -> str:
    return f"trim(coalesce({qid(column)}, ''))"


def numeric_expr(column: str) -> str:
    return f"try_cast(nullif({normalized_expr(column)}, '') AS DOUBLE)"


def valid_condition() -> str:
    tests = [f"isfinite({numeric_expr(column)})" for column in FEATURES_8]
    tests.append(f"{normalized_expr('Label')} <> ''")
    return " AND ".join(tests)


def csv_relation(path: Path) -> str:
    return (f"read_csv({qstr(path.resolve().as_posix())}, all_varchar=true, "
            "header=true, parallel=false, ignore_errors=false, null_padding=false)")


def create_schema(connection: duckdb.DuckDBPyConnection, columns: list[str]) -> None:
    source_columns = ",\n".join(f"  {qid(column)} VARCHAR" for column in columns)
    connection.execute(f"""
        CREATE TABLE IF NOT EXISTS valid_records (
        {source_columns},
          source_file VARCHAR,
          source_file_sha256 VARCHAR,
          source_row_number BIGINT,
          source_row_id VARCHAR,
          day VARCHAR,
          source_label VARCHAR,
          Label_binary UTINYINT
        )
    """)
    connection.execute("""
        CREATE TABLE IF NOT EXISTS cleaning_counts (
          source_file VARCHAR, day VARCHAR, source_label VARCHAR, binary_class VARCHAR,
          raw_rows BIGINT, clean_valid_rows BIGINT, invalid_rows BIGINT
        )
    """)
    connection.execute("""
        CREATE TABLE IF NOT EXISTS processed_files (
          source_file VARCHAR PRIMARY KEY, source_file_sha256 VARCHAR,
          raw_rows BIGINT, clean_valid_rows BIGINT, processed_utc VARCHAR
        )
    """)


def ingest_file(connection: duckdb.DuckDBPyConnection, source_root: Path,
                record: dict[str, object], columns: list[str]) -> None:
    relative = str(record["relative_path"])
    already = connection.execute(
        "SELECT count(*) FROM processed_files WHERE source_file = ?", [relative]
    ).fetchone()[0]
    if already:
        print(f"resume: already ingested {relative}", flush=True)
        return
    path = source_root / relative
    relation = csv_relation(path)
    condition = valid_condition()
    label = normalized_expr("Label")
    stats_sql = f"""
        SELECT
          {label} AS source_label,
          CASE WHEN upper({label}) = 'BENIGN' THEN 'BENIGN'
               WHEN {label} = '' THEN 'INVALID_LABEL' ELSE 'DDoS' END AS binary_class,
          count(*)::BIGINT AS raw_rows,
          count(*) FILTER (WHERE {condition})::BIGINT AS clean_valid_rows,
          count(*) FILTER (WHERE NOT coalesce(({condition}), false))::BIGINT AS invalid_rows
        FROM {relation}
        GROUP BY 1, 2
        ORDER BY 1
    """
    stats = connection.execute(stats_sql).fetchall()
    raw_rows = sum(int(row[2]) for row in stats)
    clean_rows = sum(int(row[3]) for row in stats)
    if raw_rows != int(record["rows"]):
        raise ValueError(f"{relative}: inventory rows={record['rows']} but CSV scan={raw_rows}")

    normalized = ",\n".join(
        f"          {normalized_expr(column)} AS {qid(column)}" for column in columns)
    select_columns = ", ".join(qid(column) for column in columns)
    file_hash = str(record["sha256"])
    day = relative.split("/", 1)[0]
    insert_sql = f"""
        INSERT INTO valid_records
        WITH numbered AS (
          SELECT row_number() OVER () - 1 AS source_row_number, * FROM {relation}
        ), normalized AS (
          SELECT
{normalized},
            source_row_number
          FROM numbered
        )
        SELECT {select_columns},
          {qstr(relative)} AS source_file,
          {qstr(file_hash)} AS source_file_sha256,
          source_row_number,
          sha256({qstr(file_hash)} || chr(31) || cast(source_row_number AS VARCHAR))
            AS source_row_id,
          {qstr(day)} AS day,
          {qid('Label')} AS source_label,
          CASE WHEN upper({qid('Label')}) = 'BENIGN' THEN 0 ELSE 1 END::UTINYINT
            AS Label_binary
        FROM normalized
        WHERE {" AND ".join(f"isfinite(try_cast(nullif({qid(c)}, '') AS DOUBLE))" for c in FEATURES_8)}
          AND {qid('Label')} <> ''
    """
    print(f"ingest {relative}: raw={raw_rows} clean={clean_rows}", flush=True)
    connection.execute("BEGIN TRANSACTION")
    try:
        connection.execute(insert_sql)
        inserted = connection.execute(
            "SELECT count(*) FROM valid_records WHERE source_file = ?", [relative]
        ).fetchone()[0]
        if inserted != clean_rows:
            raise AssertionError(f"{relative}: expected {clean_rows} inserts; found {inserted}")
        connection.executemany(
            "INSERT INTO cleaning_counts VALUES (?, ?, ?, ?, ?, ?, ?)",
            [(relative, day, *row) for row in stats])
        connection.execute(
            "INSERT INTO processed_files VALUES (?, ?, ?, ?, ?)",
            [relative, file_hash, raw_rows, clean_rows,
             datetime.now(timezone.utc).isoformat()])
        connection.execute("COMMIT")
    except Exception:
        connection.execute("ROLLBACK")
        raise


def create_exact_ranking(connection: duckdb.DuckDBPyConnection,
                         columns: list[str]) -> None:
    if table_exists(connection, "ranked_records"):
        print("resume: exact ranked_records table already exists", flush=True)
        return
    partition = ", ".join(qid(column) for column in columns)
    canonical_list = ", ".join(qid(column) for column in columns)
    print("exact deduplication across all normalized 88-column source records", flush=True)
    connection.execute("BEGIN TRANSACTION")
    try:
        connection.execute(f"""
            CREATE TABLE ranked_records AS
            SELECT *,
              sha256(to_json(list_value({canonical_list}))) AS row_hash,
              row_number() OVER (
                PARTITION BY {partition}
                ORDER BY day, source_file, source_row_number
              ) AS duplicate_rank
            FROM valid_records
        """)
        connection.execute("COMMIT")
    except Exception:
        connection.execute("ROLLBACK")
        raise
    collision = connection.execute("""
        SELECT row_hash, count(*) AS records
        FROM ranked_records WHERE duplicate_rank = 1
        GROUP BY row_hash HAVING count(*) > 1 LIMIT 1
    """).fetchone()
    if collision:
        raise RuntimeError(f"SHA-256 collision between distinct normalized records: {collision}")


def hamilton_allocations(strata: pd.DataFrame, target: int) -> pd.DataFrame:
    result = strata.copy().sort_values(
        ["day", "source_file", "source_label"]).reset_index(drop=True)
    total = int(result["available_unique_ddos"].sum())
    if target <= 0 or target > total:
        raise ValueError(f"Invalid stratified target {target}; available DDoS={total}")
    exact = result["available_unique_ddos"].astype(float) * target / total
    result["allocated_ddos"] = np.floor(exact).astype("int64")
    result["allocation_remainder"] = exact - result["allocated_ddos"]
    remaining = target - int(result["allocated_ddos"].sum())
    order = result.sort_values(
        ["allocation_remainder", "day", "source_file", "source_label"],
        ascending=[False, True, True, True]).index[:remaining]
    result.loc[order, "allocated_ddos"] += 1
    if int(result["allocated_ddos"].sum()) != target:
        raise AssertionError("Hamilton allocation does not sum to N")
    if (result["allocated_ddos"] > result["available_unique_ddos"]).any():
        raise AssertionError("Hamilton allocation exceeds a stratum capacity")
    return result


def create_selection(connection: duckdb.DuckDBPyConnection, seed: int) -> tuple[int, pd.DataFrame]:
    benign_n = int(connection.execute("""
        SELECT count(*) FROM ranked_records
        WHERE duplicate_rank = 1 AND Label_binary = 0
    """).fetchone()[0])
    if benign_n <= 0:
        raise ValueError("No clean unique BENIGN records remain")
    strata = connection.execute("""
        SELECT day, source_file, source_label,
               count(*)::BIGINT AS available_unique_ddos
        FROM ranked_records
        WHERE duplicate_rank = 1 AND Label_binary = 1
        GROUP BY day, source_file, source_label
        ORDER BY day, source_file, source_label
    """).df()
    allocations = hamilton_allocations(strata, benign_n)
    selection_exists = table_exists(connection, "selected_records")
    if selection_exists:
        existing = connection.execute("""
            SELECT count(*) AS total,
                   count(*) FILTER (WHERE Label_binary=0) AS benign,
                   count(*) FILTER (WHERE Label_binary=1) AS ddos
            FROM selected_records
        """).fetchone()
        existing_counts = tuple(map(int, existing))
        if existing_counts == (2 * benign_n, benign_n, benign_n):
            return benign_n, allocations
        if not table_exists(connection, "selection_progress"):
            raise ValueError(f"Existing partial selection lacks resumable progress: {existing}")
        completed_ddos = int(connection.execute(
            "SELECT coalesce(sum(selected_rows), 0) FROM selection_progress"
        ).fetchone()[0])
        if existing_counts != (benign_n + completed_ddos, benign_n, completed_ddos):
            raise ValueError(f"Existing partial selection is inconsistent: {existing}; "
                             f"progress DDoS={completed_ddos}")

    if table_exists(connection, "ddos_allocations"):
        existing_allocations = connection.execute("""
            SELECT day, source_file, source_label, available_unique_ddos,
                   allocated_ddos, allocation_remainder
            FROM ddos_allocations ORDER BY day, source_file, source_label
        """).df()
        expected_allocations = allocations[[
            "day", "source_file", "source_label", "available_unique_ddos",
            "allocated_ddos", "allocation_remainder"]].sort_values(
                ["day", "source_file", "source_label"]).reset_index(drop=True)
        existing_allocations = existing_allocations.reset_index(drop=True)
        if not existing_allocations.equals(expected_allocations):
            raise ValueError("Existing DDoS allocation table disagrees with the "
                             "deterministically recomputed allocation")
        print("resume: verified existing deterministic DDoS allocation table", flush=True)
    else:
        connection.register("allocation_frame", allocations)
        connection.execute("CREATE TABLE ddos_allocations AS SELECT * FROM allocation_frame")
        connection.unregister("allocation_frame")
    print(f"select all N={benign_n} BENIGN and deterministic stratified N DDoS", flush=True)
    if not selection_exists:
        connection.execute("BEGIN TRANSACTION")
        try:
            connection.execute(f"""
                CREATE TABLE selected_records AS
                SELECT r.*, NULL::BIGINT AS sampling_rank,
                       'all_clean_unique_benign' AS selection_reason,
                       {seed}::BIGINT AS sampling_seed
                FROM ranked_records r
                WHERE r.duplicate_rank = 1 AND r.Label_binary = 0
            """)
            connection.execute("""
                CREATE TABLE selection_progress (
                  day VARCHAR, source_file VARCHAR, source_label VARCHAR,
                  allocated_rows BIGINT, selected_rows BIGINT, sampling_seed BIGINT,
                  completed_utc VARCHAR,
                  PRIMARY KEY(day, source_file, source_label)
                )
            """)
            connection.execute("COMMIT")
        except Exception:
            connection.execute("ROLLBACK")
            raise
    for record in allocations.itertuples(index=False):
        day = str(record.day)
        source_file = str(record.source_file)
        source_label = str(record.source_label)
        allocated = int(record.allocated_ddos)
        done = connection.execute("""
            SELECT count(*) FROM selection_progress
            WHERE day=? AND source_file=? AND source_label=?
        """, [day, source_file, source_label]).fetchone()[0]
        if done:
            print(f"resume: selected DDoS stratum {day}/{source_file}/{source_label}",
                  flush=True)
            continue
        order = f"sha256(row_hash || ':' || {qstr(seed)}), row_hash"
        connection.execute("BEGIN TRANSACTION")
        try:
            if allocated:
                connection.execute(f"""
                    INSERT INTO selected_records
                    WITH chosen AS (
                      SELECT r.* FROM ranked_records r
                      WHERE r.duplicate_rank=1 AND r.Label_binary=1
                        AND r.day={qstr(day)} AND r.source_file={qstr(source_file)}
                        AND r.source_label={qstr(source_label)}
                      ORDER BY {order}
                      LIMIT {allocated}
                    )
                    SELECT chosen.*,
                           row_number() OVER (ORDER BY {order}) AS sampling_rank,
                           'deterministic_hamilton_stratified_without_replacement'
                             AS selection_reason,
                           {seed}::BIGINT AS sampling_seed
                    FROM chosen
                """)
            observed = int(connection.execute("""
                SELECT count(*) FROM selected_records
                WHERE Label_binary=1 AND day=? AND source_file=? AND source_label=?
            """, [day, source_file, source_label]).fetchone()[0])
            if observed != allocated:
                raise AssertionError(f"{day}/{source_file}/{source_label}: "
                                     f"selected {observed}, allocated {allocated}")
            connection.execute(
                "INSERT INTO selection_progress VALUES (?, ?, ?, ?, ?, ?, ?)",
                [day, source_file, source_label, allocated, observed, seed,
                 datetime.now(timezone.utc).isoformat()])
            connection.execute("COMMIT")
            print(f"selected DDoS stratum {source_file}/{source_label}: {observed}",
                  flush=True)
        except Exception:
            connection.execute("ROLLBACK")
            raise
    counts = tuple(map(int, connection.execute("""
        SELECT count(*), count(*) FILTER (WHERE Label_binary=0),
               count(*) FILTER (WHERE Label_binary=1), count(DISTINCT row_hash),
               count(DISTINCT source_row_id)
        FROM selected_records
    """).fetchone()))
    if counts != (2 * benign_n, benign_n, benign_n, 2 * benign_n, 2 * benign_n):
        raise AssertionError(f"Selection uniqueness/balance failure: {counts}")
    return benign_n, allocations


def select_group_split(group_counts: pd.DataFrame, seed: int,
                       test_fraction: float) -> tuple[list[str], str, float]:
    groups = group_counts["source_group"].astype(str).to_numpy()
    splitter = GroupShuffleSplit(n_splits=4000, test_size=test_fraction, random_state=seed)
    target = group_counts[["BENIGN", "DDoS"]].sum().to_numpy(dtype=float) * test_fraction
    total_target = target.sum()
    best: tuple[float, str, list[str]] | None = None
    for _, test_idx in splitter.split(groups, groups=groups):
        test = group_counts.iloc[test_idx]
        class_counts = test[["BENIGN", "DDoS"]].sum().to_numpy(dtype=float)
        if (class_counts <= 0).any():
            continue
        total = class_counts.sum()
        score = (abs(total - total_target) / total_target +
                 (np.abs(class_counts - target) / target).sum())
        test_groups = sorted(test["source_group"].astype(str).tolist())
        tie = hashlib.sha256(
            (str(seed) + "\x1f" + "\x1f".join(test_groups)).encode()).hexdigest()
        candidate = (float(score), tie, test_groups)
        if best is None or candidate < best:
            best = candidate
    if best is None:
        raise ValueError(f"Seed {seed}: no class-preserving source-file group split exists")
    split_id = hashlib.sha256(
        (str(seed) + "\x1e" + "\x1f".join(best[2])).encode()).hexdigest()
    return best[2], split_id, best[0]


def write_splits(connection: duckdb.DuckDBPyConnection, output: Path,
                 seeds: list[int], test_fraction: float) -> tuple[list[dict[str, object]],
                                                                   list[dict[str, object]]]:
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite split manifest: {output}")
    selected = connection.execute("""
        SELECT source_row_id AS sample_id, row_hash, source_file AS source_group,
               source_file, day, source_label AS attack_type, Label_binary AS Label
        FROM selected_records ORDER BY sample_id
    """).df()
    grouped = selected.groupby(["source_group", "Label"]).size().unstack(fill_value=0)
    for label in (0, 1):
        if label not in grouped.columns:
            grouped[label] = 0
    group_counts = grouped[[0, 1]].rename(columns={0: "BENIGN", 1: "DDoS"}).reset_index()
    writer: pq.ParquetWriter | None = None
    split_records: list[dict[str, object]] = []
    composition: list[dict[str, object]] = []
    all_groups = set(selected["source_group"])
    try:
        for seed in seeds:
            test_groups, split_id, score = select_group_split(group_counts, seed, test_fraction)
            test_group_set = set(test_groups)
            frame = selected.copy()
            frame.insert(0, "seed", seed)
            frame.insert(1, "split_id", split_id)
            frame["partition"] = np.where(
                frame["source_group"].isin(test_group_set), "test", "train")
            train = frame[frame.partition == "train"]
            test = frame[frame.partition == "test"]
            train_groups = set(train.source_group)
            observed_test_groups = set(test.source_group)
            row_overlap = set(train.row_hash) & set(test.row_hash)
            id_overlap = set(train.sample_id) & set(test.sample_id)
            group_overlap = train_groups & observed_test_groups
            train_counts = train.Label.value_counts().to_dict()
            test_counts = test.Label.value_counts().to_dict()
            if row_overlap or id_overlap or group_overlap:
                raise AssertionError(f"Seed {seed}: split leakage detected")
            if set(train_counts) != {0, 1} or set(test_counts) != {0, 1}:
                raise ValueError(f"Seed {seed}: group split is not class-preserving")
            if train_groups | observed_test_groups != all_groups:
                raise AssertionError(f"Seed {seed}: groups are missing from split")
            split_records.append({
                "seed": seed, "split_id": split_id, "objective_score": score,
                "train_rows": len(train), "test_rows": len(test),
                "train_benign": int(train_counts[0]), "train_ddos": int(train_counts[1]),
                "test_benign": int(test_counts[0]), "test_ddos": int(test_counts[1]),
                "train_groups": sorted(train_groups), "test_groups": sorted(test_group_set),
                "row_hash_overlap": 0, "sample_id_overlap": 0, "source_group_overlap": 0,
                "class_preserving": True,
            })
            comp = frame.groupby(
                ["partition", "day", "source_file", "attack_type", "Label"]).size()
            for index, count in comp.items():
                partition, day, source_file, attack_type, label = index
                composition.append({
                    "seed": seed, "split_id": split_id, "partition": partition,
                    "day": day, "source_file": source_file, "attack_type": attack_type,
                    "binary_class": "BENIGN" if label == 0 else "DDoS", "rows": int(count),
                })
            table = pa.Table.from_pandas(frame, preserve_index=False)
            if writer is None:
                writer = pq.ParquetWriter(output, table.schema, compression="zstd")
            writer.write_table(table)
    finally:
        if writer is not None:
            writer.close()
    return split_records, composition


def write_outputs(connection: duckdb.DuckDBPyConnection, output_dir: Path,
                  benign_n: int, allocations: pd.DataFrame, inventory: dict[str, object],
                  sampling_seed: int, split_seeds: list[int], test_fraction: float,
                  database_path: Path) -> dict[str, object]:
    paths = {
        "prepared": output_dir / "cicddos2019-max-benign-feature8.parquet",
        "selected": output_dir / "selected_rows.parquet",
        "splits": output_dir / "split_manifest.parquet",
        "cleaning": output_dir / "cleaning_counts.csv",
        "dedup": output_dir / "deduplication_counts.csv",
        "allocation": output_dir / "ddos_sampling_allocation.csv",
        "composition": output_dir / "group_split_composition.csv",
        "leakage": output_dir / "leakage_checks.csv",
        "manifest": output_dir / "preparation_manifest.json",
        "report": output_dir / "preparation_report.md",
    }
    for key, path in paths.items():
        if path.exists():
            raise FileExistsError(f"Refusing to overwrite {key} output: {path}")
    feature_select = ",\n".join(
        f"try_cast({qid(feature)} AS DOUBLE) AS {qid(feature)}" for feature in FEATURES_8)
    connection.execute(f"""
        COPY (
          SELECT
{feature_select},
            Label_binary AS Label,
            source_row_id AS sample_id,
            source_row_id, row_hash, source_file, source_file_sha256,
            source_row_number, day, source_file AS source_group,
            source_label AS attack_type, source_label,
            selection_reason, sampling_seed, sampling_rank
          FROM selected_records ORDER BY sample_id
        ) TO {qstr(paths['prepared'].resolve().as_posix())}
          (FORMAT PARQUET, COMPRESSION ZSTD)
    """)
    connection.execute(f"""
        COPY (
          SELECT source_row_id AS sample_id, source_row_id, row_hash, source_file,
                 source_file_sha256, source_row_number, day,
                 source_file AS source_group, source_label AS attack_type,
                 Label_binary AS Label, selection_reason, sampling_seed, sampling_rank
          FROM selected_records ORDER BY sample_id
        ) TO {qstr(paths['selected'].resolve().as_posix())}
          (FORMAT PARQUET, COMPRESSION ZSTD)
    """)
    cleaning = connection.execute("""
        SELECT * FROM cleaning_counts ORDER BY day, source_file, source_label
    """).df()
    cleaning.to_csv(paths["cleaning"], index=False)
    dedup = connection.execute("""
        SELECT day, source_file, source_label,
               CASE WHEN Label_binary=0 THEN 'BENIGN' ELSE 'DDoS' END AS binary_class,
               count(*)::BIGINT AS clean_valid_rows,
               count(*) FILTER (WHERE duplicate_rank>1)::BIGINT AS exact_duplicates_removed,
               count(*) FILTER (WHERE duplicate_rank=1)::BIGINT AS clean_unique_rows
        FROM ranked_records GROUP BY 1,2,3,4 ORDER BY 1,2,3
    """).df()
    dedup.to_csv(paths["dedup"], index=False)
    allocations.to_csv(paths["allocation"], index=False)
    split_records, composition = write_splits(
        connection, paths["splits"], split_seeds, test_fraction)
    pd.DataFrame(composition).to_csv(paths["composition"], index=False)
    pd.DataFrame(split_records).to_csv(paths["leakage"], index=False)

    raw_binary = cleaning.groupby("binary_class")["raw_rows"].sum().to_dict()
    clean_binary = cleaning.groupby("binary_class")["clean_valid_rows"].sum().to_dict()
    invalid_binary = cleaning.groupby("binary_class")["invalid_rows"].sum().to_dict()
    unique_binary = dedup.groupby("binary_class")["clean_unique_rows"].sum().to_dict()
    duplicate_binary = dedup.groupby("binary_class")["exact_duplicates_removed"].sum().to_dict()
    hashes = {key: sha256_file(path) for key, path in paths.items()
              if key not in {"manifest", "report"}}
    manifest: dict[str, object] = {
        "status": "prepared_pending_independent_validation",
        "dataset": "CICDDoS2019",
        "method": "maximum clean valid exact-record-unique BENIGN with matched DDoS",
        "N": benign_n,
        "class_counts": {
            "raw": {str(k): int(v) for k, v in raw_binary.items()},
            "clean_valid": {str(k): int(v) for k, v in clean_binary.items()},
            "invalid_removed": {str(k): int(v) for k, v in invalid_binary.items()},
            "exact_duplicates_removed": {str(k): int(v) for k, v in duplicate_binary.items()},
            "clean_unique": {str(k): int(v) for k, v in unique_binary.items()},
            "selected": {"BENIGN": benign_n, "DDoS": benign_n},
        },
        "normalization": (
            "All 88 official CSV headers and field strings are stripped of surrounding "
            "whitespace; empty values normalize to the empty string; internal text and "
            "the common official column order are preserved."),
        "exact_deduplication": (
            "DuckDB equality partition over every one of the 88 normalized source fields. "
            "Metadata is excluded from identity. The deterministic representative is the "
            "lowest day/source-file/original-row tuple. SHA-256 of the canonical JSON value "
            "list is recorded only after exact equality grouping; hash collisions are fatal."),
        "balancing": (
            "Retain every clean unique BENIGN row. Allocate exactly N DDoS rows across "
            "day/source-file/source-attack strata by proportional Hamilton largest "
            "remainder, then rank by SHA-256(row_hash, sampling seed) without replacement."),
        "sampling_seed": sampling_seed,
        "oversampling_or_duplication_used": False,
        "source_files": inventory["preparation_input_files"],
        "ancillary_files_excluded": inventory["ancillary_files_preserved"],
        "selected_row_fields": [
            "sample_id", "source_row_id", "row_hash", "source_file",
            "source_file_sha256", "source_row_number", "day", "source_group",
            "attack_type", "Label", "selection_reason", "sampling_seed", "sampling_rank"],
        "split_method": (
            "Source-file group holdout only. For each seed, 4,000 deterministic "
            "GroupShuffleSplit candidates are searched and the class-preserving candidate "
            "closest to 20% overall/BENIGN/DDoS counts is selected. No record fallback."),
        "split_seeds": split_seeds,
        "test_fraction_target": test_fraction,
        "split_records": split_records,
        "matched_experiment_invariant": (
            "The same prepared sample_id rows and one precomputed partition per seed must "
            "be used unchanged for feature sets 4/6/8 and every model family."),
        "output_hashes_sha256": hashes,
        "database": str(database_path),
        "environment": {
            "python_executable": sys.executable,
            "python_version": platform.python_version(),
            "duckdb_version": duckdb.__version__,
            "package_versions": package_versions(),
        },
        "created_utc": datetime.now(timezone.utc).isoformat(),
    }
    write_json_new(paths["manifest"], manifest)
    report = [
        "# CICDDoS2019 maximum-BENIGN preparation report", "",
        f"- Status: prepared; independent validation required before training.",
        f"- Exact N: **{benign_n:,} records per binary class**.",
        f"- Selected total: **{2 * benign_n:,}**.",
        f"- Sampling seed: `{sampling_seed}`.",
        "- BENIGN oversampling/duplication: none; every clean unique BENIGN row retained.",
        "- DDoS selection: deterministic day/file/attack-stratified Hamilton allocation, "
        "  without replacement.", "", "## Class accounting", "",
        "| Stage | BENIGN | DDoS |", "|---|---:|---:|",
    ]
    for stage in ("raw", "clean_valid", "invalid_removed", "exact_duplicates_removed",
                  "clean_unique", "selected"):
        values = manifest["class_counts"][stage]
        report.append(f"| {stage} | {int(values.get('BENIGN', 0)):,} | "
                      f"{int(values.get('DDoS', 0)):,} |")
    report.extend([
        "", "## Leakage validation generated for all ten seeds", "",
        "Every split is source-file-grouped and class-preserving. The independent validator "
        "must confirm zero sample-ID, SHA-256 row-hash, and source-group overlap before "
        "training. Detailed file/day/attack allocation and split composition are in the "
        "machine-readable CSV/Parquet outputs listed in the provenance manifest.", "",
        f"Selected-row manifest SHA-256: `{hashes['selected']}`", "",
        f"Split manifest SHA-256: `{hashes['splits']}`", "",
    ])
    with paths["report"].open("x", encoding="utf-8") as stream:
        stream.write("\n".join(report))
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", required=True, type=Path)
    parser.add_argument("--validated-inventory", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--sampling-seed", type=int, default=104729)
    parser.add_argument("--split-seeds", nargs="+", type=int, default=DEFAULT_SEEDS)
    parser.add_argument("--test-fraction", type=float, default=0.20)
    parser.add_argument("--threads", type=int, default=4)
    parser.add_argument("--memory-limit", default="12GB")
    parser.add_argument("--minimum-free-gib", type=float, default=100.0)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    if platform.python_version() != "3.10.5":
        raise RuntimeError(f"Preparation requires Python 3.10.5, found {platform.python_version()}")
    inventory = json.loads(args.validated_inventory.read_text(encoding="utf-8"))
    if inventory.get("status") != "valid":
        raise ValueError("Validated inventory status is not valid")
    if not 0 < args.test_fraction < 1:
        raise ValueError("--test-fraction must lie strictly between 0 and 1")
    source_root = args.source_root.resolve()
    if args.output_dir.exists() and not args.resume:
        raise FileExistsError(f"Refusing existing preparation directory: {args.output_dir}")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    free_gib = shutil.disk_usage(args.output_dir).free / (1024 ** 3)
    if free_gib < args.minimum_free_gib:
        raise OSError(f"Preparation requires at least {args.minimum_free_gib:.1f} GiB free; "
                      f"found {free_gib:.1f} GiB")

    inventory_dir = args.validated_inventory.resolve().parent
    files_frame = pd.read_csv(inventory_dir / "files.csv")
    data_frame = files_frame[files_frame["relative_path"].str.lower().str.endswith(".csv")]
    if len(data_frame) != len(inventory["preparation_input_files"]):
        raise ValueError("Validated inventory and files.csv disagree on data CSV count")
    schema_values = data_frame["stripped_columns_json"].unique()
    if len(schema_values) != 1:
        raise ValueError("Source CSVs do not share one normalized full-record schema")
    columns = json.loads(schema_values[0])
    if len(columns) != 88 or any(feature not in columns for feature in FEATURES_8 + ["Label"]):
        raise ValueError("Expected one 88-column schema containing the feature superset and label")

    database_path = args.output_dir / "preparation.duckdb"
    connection = duckdb.connect(str(database_path))
    connection.execute(f"SET threads={int(args.threads)}")
    connection.execute(f"SET memory_limit={qstr(args.memory_limit)}")
    connection.execute("SET preserve_insertion_order=true")
    create_schema(connection, columns)
    for record in inventory["preparation_input_files"]:
        path = source_root / record["relative_path"]
        stat = path.stat()
        if stat.st_size != int(record["size_bytes"]):
            raise ValueError(f"Source size changed since inventory: {record['relative_path']}")
        ingest_file(connection, source_root, record, columns)
    processed = connection.execute("SELECT count(*) FROM processed_files").fetchone()[0]
    if processed != len(inventory["preparation_input_files"]):
        raise AssertionError(f"Only {processed} source files were ingested")
    create_exact_ranking(connection, columns)
    benign_n, allocations = create_selection(connection, args.sampling_seed)
    manifest = write_outputs(
        connection, args.output_dir, benign_n, allocations, inventory,
        args.sampling_seed, list(dict.fromkeys(args.split_seeds)),
        args.test_fraction, database_path)
    connection.close()
    print(json.dumps({
        "status": manifest["status"], "N": benign_n,
        "selected_total": 2 * benign_n,
        "manifest": str(args.output_dir / "preparation_manifest.json"),
        "report": str(args.output_dir / "preparation_report.md"),
    }, indent=2))


if __name__ == "__main__":
    main()
