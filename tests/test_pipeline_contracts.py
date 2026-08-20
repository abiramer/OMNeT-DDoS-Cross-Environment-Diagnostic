from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

try:
    import numpy as np
    import pandas as pd
    from evaluate_omnet import load_feature_tables
    from pipeline_common import FEATURES_8, feature_columns
    from prepare_cicddos2019 import normalize_columns
    from prepare_cicddos2019_max_benign import (
        create_exact_ranking, create_schema, create_selection, hamilton_allocations,
        ingest_file, select_group_split)
    from statistical_analysis import mcnemar_tests, summarize
    from train_models import load_precomputed_split
except ModuleNotFoundError as exc:  # the Scapy-only smoke environment is valid for extraction
    raise unittest.SkipTest(f"scientific-stack tests require requirements.txt: {exc}") from exc


class PreparationTests(unittest.TestCase):
    def test_whitespace_headers_and_complete_superset(self):
        aliases = {
            " Total Fwd Packets ": [1], " Tot Bwd Pkts ": [2],
            " Flow Byts/s ": [3.0], " Flow Pkts/s ": [4.0],
            " Flow Duration ": [5], " TotLen Fwd Pkts ": [6],
            " TotLen Bwd Pkts ": [7], " Fwd Pkt Len Mean ": [8.0],
            " Label ": ["BENIGN"],
        }
        normalized = normalize_columns(pd.DataFrame(aliases))
        self.assertEqual(list(normalized[FEATURES_8].columns), FEATURES_8)

    def test_hamilton_attack_strata_sum_exactly_to_n(self):
        strata = pd.DataFrame([
            {"day": "day1", "source_file": "a.csv", "source_label": "A",
             "available_unique_ddos": 10},
            {"day": "day1", "source_file": "b.csv", "source_label": "B",
             "available_unique_ddos": 20},
            {"day": "day2", "source_file": "c.csv", "source_label": "C",
             "available_unique_ddos": 30},
        ])
        allocated = hamilton_allocations(strata, 17)
        self.assertEqual(int(allocated.allocated_ddos.sum()), 17)
        self.assertTrue((allocated.allocated_ddos <= allocated.available_unique_ddos).all())
        again = hamilton_allocations(strata, 17)
        pd.testing.assert_frame_equal(allocated, again)

    def test_group_split_is_class_preserving_and_deterministic(self):
        counts = pd.DataFrame({
            "source_group": [f"g{index}" for index in range(10)],
            "BENIGN": [20, 12, 18, 10, 15, 14, 16, 11, 13, 17],
            "DDoS": [11, 19, 10, 20, 15, 16, 14, 18, 17, 13],
        })
        groups, split_id, _ = select_group_split(counts, 104729, 0.20)
        groups2, split_id2, _ = select_group_split(counts, 104729, 0.20)
        self.assertEqual(groups, groups2)
        self.assertEqual(split_id, split_id2)
        selected = counts[counts.source_group.isin(groups)]
        self.assertGreater(int(selected.BENIGN.sum()), 0)
        self.assertGreater(int(selected.DDoS.sum()), 0)

    def test_exact_full_record_dedup_ignores_source_metadata(self):
        import duckdb
        connection = duckdb.connect()
        connection.execute("""
            CREATE TABLE valid_records (
              feature VARCHAR, distinguishing_field VARCHAR,
              source_file VARCHAR, source_row_number BIGINT, day VARCHAR
            )
        """)
        connection.executemany("INSERT INTO valid_records VALUES (?, ?, ?, ?, ?)", [
            ("1", "same", "day1/a.csv", 1, "day1"),
            ("1", "same", "day2/b.csv", 9, "day2"),
            ("1", "different-legitimate-record", "day2/b.csv", 10, "day2"),
        ])
        create_exact_ranking(connection, ["feature", "distinguishing_field"])
        ranks = connection.execute(
            "SELECT distinguishing_field, duplicate_rank FROM ranked_records "
            "ORDER BY distinguishing_field, duplicate_rank").fetchall()
        self.assertEqual(ranks, [("different-legitimate-record", 1), ("same", 1), ("same", 2)])
        unique_hashes = connection.execute(
            "SELECT count(DISTINCT row_hash) FROM ranked_records WHERE duplicate_rank=1"
        ).fetchone()[0]
        self.assertEqual(unique_hashes, 2)
        connection.close()

    def test_ingestion_keeps_original_row_numbers_and_removes_invalid(self):
        import duckdb
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "day1" / "test.csv"
            path.parent.mkdir()
            columns = [*FEATURES_8, "Label", "distinguishing_field"]
            valid = {feature: "1" for feature in FEATURES_8} | {
                "Label": "BENIGN", "distinguishing_field": "first"}
            invalid = valid | {"Flow Bytes/s": "Infinity", "distinguishing_field": "invalid"}
            valid_last = valid | {"Label": "Attack", "distinguishing_field": "last"}
            pd.DataFrame([valid, invalid, valid_last], columns=columns).to_csv(path, index=False)
            connection = duckdb.connect()
            create_schema(connection, columns)
            ingest_file(connection, root, {
                "relative_path": "day1/test.csv", "sha256": "a" * 64, "rows": 3,
            }, columns)
            observed = connection.execute(
                "SELECT source_row_number, Label_binary, distinguishing_field "
                "FROM valid_records ORDER BY source_row_number").fetchall()
            self.assertEqual(observed, [(0, 0, "first"), (2, 1, "last")])
            counts = connection.execute(
                "SELECT sum(raw_rows), sum(clean_valid_rows), sum(invalid_rows) "
                "FROM cleaning_counts").fetchone()
            self.assertEqual(counts, (3, 2, 1))
            connection.close()

    def test_stratumwise_selection_is_balanced_unique_and_resumable(self):
        import duckdb
        connection = duckdb.connect()
        connection.execute("""
            CREATE TABLE ranked_records (
              row_hash VARCHAR, source_row_id VARCHAR, day VARCHAR,
              source_file VARCHAR, source_label VARCHAR, Label_binary UTINYINT,
              duplicate_rank BIGINT
            )
        """)
        rows = [
            (f"b-{index}", f"bid-{index}", "day1", "benign.csv", "BENIGN", 0, 1)
            for index in range(4)
        ]
        rows += [
            (f"a-{index}", f"aid-{index}", "day1", "attack-a.csv", "AttackA", 1, 1)
            for index in range(8)
        ]
        rows += [
            (f"c-{index}", f"cid-{index}", "day2", "attack-c.csv", "AttackC", 1, 1)
            for index in range(4)
        ]
        connection.executemany("INSERT INTO ranked_records VALUES (?, ?, ?, ?, ?, ?, ?)", rows)
        n, allocation = create_selection(connection, 104729)
        self.assertEqual(n, 4)
        self.assertEqual(int(allocation.allocated_ddos.sum()), 4)
        self.assertEqual(connection.execute(
            "SELECT count(*), count(*) FILTER (WHERE Label_binary=0), "
            "count(*) FILTER (WHERE Label_binary=1), count(DISTINCT row_hash) "
            "FROM selected_records").fetchone(), (8, 4, 4, 8))
        first = connection.execute(
            "SELECT row_hash FROM selected_records ORDER BY row_hash").fetchall()
        n_again, _ = create_selection(connection, 104729)
        second = connection.execute(
            "SELECT row_hash FROM selected_records ORDER BY row_hash").fetchall()
        self.assertEqual(n_again, n)
        self.assertEqual(second, first)
        connection.close()


class MatchedSplitTests(unittest.TestCase):
    def test_identical_split_ids_for_all_feature_sets(self):
        rows = 40
        data = pd.DataFrame({feature: np.arange(rows, dtype=float) for feature in FEATURES_8})
        data["Label"] = [0, 1] * (rows // 2)
        data["sample_id"] = [f"sample-{index}" for index in range(rows)]
        data["row_hash"] = [f"hash-{index}" for index in range(rows)]
        data["source_group"] = [f"source-{index // 10}" for index in range(rows)]
        manifest = pd.DataFrame({
            "seed": 104729, "split_id": "synthetic-group-split",
            "sample_id": data.sample_id, "row_hash": data.row_hash,
            "source_group": data.source_group, "Label": data.Label,
            "partition": np.where(data.source_group.eq("source-3"), "test", "train"),
        })
        split = load_precomputed_split(data, manifest, 104729)
        expected = split["test_ids"]
        observed = {}
        for size in (4, 6, 8):
            _ = data.iloc[split["test_pos"]][feature_columns(size)]
            observed[size] = data.iloc[split["test_pos"]].sample_id.tolist()
        self.assertEqual(observed[4], expected)
        self.assertEqual(observed[6], expected)
        self.assertEqual(observed[8], expected)


class EvaluationContractTests(unittest.TestCase):
    def test_refuses_unlabeled_legacy_csv(self):
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "legacy.csv"
            pd.DataFrame({feature: [1.0] for feature in FEATURES_8} |
                         {"run": ["seed1"], "scenario": ["UDPFlood"]}).to_csv(path, index=False)
            with self.assertRaisesRegex(ValueError, "Refusing unlabeled/legacy"):
                load_feature_tables([path])

    def test_scenario_never_overrides_ground_truth(self):
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "labelled.csv"
            values = {feature: [1.0] for feature in FEATURES_8}
            values.update({"run": ["seed1"], "scenario": ["UDPFlood"],
                           "ground_truth_label": ["BENIGN"],
                           "traffic_source": ["benign_client"], "flow_id": ["f1"]})
            pd.DataFrame(values).to_csv(path, index=False)
            loaded = load_feature_tables([path])
            self.assertEqual(loaded.loc[0, "y_true"], 0)


class StatisticalMatchingTests(unittest.TestCase):
    def test_bounded_ci_constrains_display_only(self):
        rows = []
        for seed, value in enumerate([0.97, 0.98, 0.99, 1.0, 1.0,
                                      1.0, 1.0, 1.0, 1.0, 1.0], start=1):
            row = {"feature_set": 6, "model": "mlp", "seed": seed}
            for metric in ("accuracy", "precision", "recall", "f1", "roc_auc",
                           "pr_auc_benign", "pr_auc_ddos", "balanced_accuracy"):
                row[metric] = value
            row["mcc"] = value
            rows.append(row)
        result = summarize(pd.DataFrame(rows))
        bounded = result[result.metric.eq("pr_auc_benign")].iloc[0]
        self.assertGreater(bounded.ci95_high_raw, 1.0)
        self.assertEqual(bounded.ci95_high, 1.0)
        self.assertTrue(bounded.ci95_display_constrained_to_0_1)
        self.assertAlmostEqual(bounded["mean"], np.mean([row["pr_auc_benign"] for row in rows]))
        mcc = result[result.metric.eq("mcc")].iloc[0]
        self.assertGreater(mcc.ci95_high, 1.0)
        self.assertFalse(mcc.ci95_display_constrained_to_0_1)

    def test_mcnemar_is_not_run_on_unmatched_samples(self):
        frame = pd.DataFrame([
            {"feature_set": 4, "seed": 1, "sample_id": "a", "model": "rf",
             "y_true": 0, "y_pred": 0},
            {"feature_set": 6, "seed": 1, "sample_id": "b", "model": "rf",
             "y_true": 0, "y_pred": 1},
        ])
        result = mcnemar_tests(frame)
        self.assertEqual(result.loc[0, "status"], "not tested: unmatched samples")
        self.assertTrue(pd.isna(result.loc[0, "mcnemar_exact_p"]))


if __name__ == "__main__":
    unittest.main()
