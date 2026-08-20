"""Shared, dependency-light contracts for the reproducibility pipeline."""
from __future__ import annotations

import hashlib
import importlib.metadata
import ipaddress
import json
import platform
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

FEATURE_SETS = {
    4: ["Total Fwd Packets", "Total Backward Packets", "Flow Bytes/s", "Flow Packets/s"],
    6: ["Total Fwd Packets", "Total Backward Packets", "Flow Bytes/s", "Flow Packets/s",
        "Flow Duration", "Total Length of Fwd Packets"],
    8: ["Total Fwd Packets", "Total Backward Packets", "Flow Bytes/s", "Flow Packets/s",
        "Flow Duration", "Total Length of Fwd Packets", "Total Length of Bwd Packets",
        "Fwd Packet Length Mean"],
}
FEATURES_8 = FEATURE_SETS[8]
LABEL_TO_INT = {"BENIGN": 0, "DDoS": 1}
INT_TO_LABEL = {value: key for key, value in LABEL_TO_INT.items()}
TRAFFIC_SOURCES = {"benign_client", "udp_attacker", "tcp_attacker", "dns_reflector"}
DEFAULT_SEEDS = [104729, 130363, 155921, 181081, 206369, 231701,
                 257053, 282427, 307759, 333019]


@dataclass(frozen=True)
class TrafficRule:
    source_role: str
    destination_role: str
    protocol: int
    source_port: int | None
    destination_port: int
    ground_truth_label: str
    traffic_source: str


class RoleMapping:
    """Strict IP identity mapping loaded from the frozen human-readable YAML."""

    def __init__(self, path: Path):
        self.path = Path(path)
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        roles = raw["roles"]
        self.network_roles: dict[str, tuple[ipaddress.IPv4Address, ipaddress.IPv4Address]] = {}
        for name in ("benign_clients", "attackers", "dns_reflectors"):
            self.network_roles[name] = (ipaddress.IPv4Address(roles[name]["first"]),
                                        ipaddress.IPv4Address(roles[name]["last"]))
        victim = ipaddress.IPv4Address(roles["victim"]["address"])
        self.network_roles["victim"] = (victim, victim)
        protocol_numbers = {"TCP": 6, "UDP": 17}
        self.rules = [TrafficRule(
            source_role=item["source_role"], destination_role=item["destination_role"],
            protocol=protocol_numbers[str(item["protocol"]).upper()],
            source_port=(int(item["source_port"]) if "source_port" in item else None),
            destination_port=int(item["destination_port"]),
            ground_truth_label=item["ground_truth_label"], traffic_source=item["traffic_source"],
        ) for item in raw["traffic_rules"]]
        self._validate()

    def _validate(self) -> None:
        occupied: dict[ipaddress.IPv4Address, str] = {}
        for role, (first, last) in self.network_roles.items():
            if first > last:
                raise ValueError(f"Invalid reversed range for {role}")
            for numeric in range(int(first), int(last) + 1):
                address = ipaddress.IPv4Address(numeric)
                if address in occupied:
                    raise ValueError(f"Overlapping role mapping for {address}")
                occupied[address] = role
        for rule in self.rules:
            if rule.ground_truth_label not in LABEL_TO_INT:
                raise ValueError(f"Invalid label in {self.path}: {rule.ground_truth_label}")
            if rule.traffic_source not in TRAFFIC_SOURCES:
                raise ValueError(f"Invalid traffic source in {self.path}: {rule.traffic_source}")

    def role_for(self, address: str) -> str | None:
        try:
            parsed = ipaddress.IPv4Address(address)
        except ipaddress.AddressValueError:
            return None
        for role, (first, last) in self.network_roles.items():
            if first <= parsed <= last:
                return role
        return None

    def classify(self, protocol: int, src: str, sport: int,
                 dst: str, dport: int) -> tuple[str, str]:
        source_role, destination_role = self.role_for(src), self.role_for(dst)
        matches = [rule for rule in self.rules if rule.source_role == source_role
                   and rule.destination_role == destination_role
                   and rule.protocol == int(protocol)
                   and (rule.source_port is None or rule.source_port == int(sport))
                   and rule.destination_port == int(dport)]
        if len(matches) != 1:
            proto_name = {6: "TCP", 17: "UDP"}.get(int(protocol), str(protocol))
            raise ValueError("Unknown or ambiguous transport flow: "
                             f"{src}:{sport} -> {dst}:{dport} {proto_name}; "
                             f"roles={source_role!r}->{destination_role!r}, matches={len(matches)}")
        rule = matches[0]
        return rule.ground_truth_label, rule.traffic_source

    def fragment_fallback_ports(self, protocol: int, src: str,
                                dst: str) -> tuple[int, int] | None:
        """Return configured ports only for a unique role/protocol fallback.

        This is used when a captured non-initial fragment has no captured first
        fragment.  Both ports must be frozen explicitly; otherwise the
        fragment remains unresolved and extraction fails at EOF.
        """
        source_role, destination_role = self.role_for(src), self.role_for(dst)
        matches = [rule for rule in self.rules
                   if rule.source_role == source_role
                   and rule.destination_role == destination_role
                   and rule.protocol == int(protocol)
                   and rule.source_port is not None]
        if len(matches) > 1:
            raise ValueError(
                "Ambiguous configured fragment-port fallback: "
                f"{src}->{dst} protocol={protocol}, matches={len(matches)}")
        if not matches:
            return None
        rule = matches[0]
        return int(rule.source_port), rule.destination_port


def feature_columns(feature_set: int) -> list[str]:
    try:
        return FEATURE_SETS[int(feature_set)]
    except KeyError as exc:
        raise ValueError(f"Unsupported feature set {feature_set}; choose 4, 6, or 8") from exc


def stable_id(*parts: object) -> str:
    return hashlib.sha256("\x1f".join(str(part) for part in parts).encode("utf-8")).hexdigest()


def safe_binary_metrics(y_true: Iterable[int], y_pred: Iterable[int],
                        score: Iterable[float] | None = None) -> dict[str, object]:
    import numpy as np
    from sklearn.metrics import (
        accuracy_score, average_precision_score, balanced_accuracy_score,
        confusion_matrix, f1_score, matthews_corrcoef, precision_score,
        recall_score, roc_auc_score,
    )

    y = np.asarray(list(y_true), dtype=int)
    pred = np.asarray(list(y_pred), dtype=int)
    tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
    positive_truth = int(np.sum(y == 1))
    positive_pred = int(np.sum(pred == 1))
    result: dict[str, object] = {
        "accuracy": float(accuracy_score(y, pred)),
        "precision": (float(precision_score(y, pred)) if positive_pred
                      else "not estimable"),
        "recall": (float(recall_score(y, pred)) if positive_truth
                   else "not estimable"),
        "f1": (float(f1_score(y, pred)) if positive_truth or positive_pred
               else "not estimable"),
        "balanced_accuracy": (float(balanced_accuracy_score(y, pred))
                              if np.unique(y).size == 2 else "not estimable"),
        "mcc": (float(matthews_corrcoef(y, pred))
                if np.unique(y).size == 2 and np.unique(pred).size == 2
                else "not estimable"),
        "tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp),
    }
    if score is not None and np.unique(y).size == 2:
        values = np.asarray(list(score), dtype=float)
        result.update({"roc_auc": float(roc_auc_score(y, values)),
                       "pr_auc_benign": float(average_precision_score(1 - y, 1 - values)),
                       "pr_auc_ddos": float(average_precision_score(y, values))})
    else:
        result.update({"roc_auc": "not estimable", "pr_auc_benign": "not estimable",
                       "pr_auc_ddos": "not estimable"})
    return result


def package_versions() -> dict[str, str]:
    packages = ["numpy", "pandas", "pyarrow", "duckdb", "scikit-learn", "xgboost",
                "tensorflow", "keras", "scikeras", "joblib", "scapy", "scipy"]
    versions = {}
    for package in packages:
        try:
            versions[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            versions[package] = "not installed"
    return {"python": platform.python_version(), "implementation": sys.implementation.name,
            **versions}


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")
