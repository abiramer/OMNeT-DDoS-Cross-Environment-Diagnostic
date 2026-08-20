#!/usr/bin/env python3
"""Dependency-free cross-checks for frozen versions, seeds, roles, and features."""
from __future__ import annotations

import json
import argparse
import os
import re
from pathlib import Path

from pipeline_common import DEFAULT_SEEDS, FEATURES_8, RoleMapping

ROOT = Path(__file__).resolve().parents[1]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--inet-root", type=Path,
                        help="INET 4.5.4 root (defaults to INET_ROOT or ../samples/inet4.5)")
    args = parser.parse_args()
    inet_root = args.inet_root or (Path(os.environ["INET_ROOT"])
                                   if os.environ.get("INET_ROOT")
                                   else ROOT.parent / "samples" / "inet4.5")
    environment = (ROOT / "environment.yml").read_text(encoding="utf-8")
    versions = (ROOT / "VERSIONS.md").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    require("python=3.10.5" in environment, "environment.yml must pin Python 3.10.5")
    require("Python | 3.10.5" in versions, "VERSIONS.md must state Python 3.10.5")
    require("Python 3.10.5" in readme, "README.md must state Python 3.10.5")
    inet_version_file = inet_root / "Version"
    require(inet_version_file.is_file(),
            f"required INET tree is missing at {inet_root}; pass --inet-root or set INET_ROOT")
    inet_version = inet_version_file.read_text(encoding="utf-8").splitlines()[0]
    require(re.fullmatch(r"inet-4\.5\.4(?:-.*)?", inet_version) is not None,
            f"required INET 4.5.4, found {inet_version!r}")
    seeds = [int(line) for line in (ROOT / "config" / "seeds.txt").read_text(
        encoding="utf-8").splitlines() if line and not line.startswith("#")]
    require(seeds == DEFAULT_SEEDS, "config/seeds.txt differs from the frozen seed list")
    ini = (ROOT / "omnetpp.ini").read_text(encoding="utf-8")
    match = re.search(r"seed-0-mt\s*=\s*\$\{seed=([^}]+)\}", ini)
    require(match is not None, "omnetpp.ini seed declaration not found")
    require([int(value) for value in match.group(1).split(",")] == seeds,
            "omnetpp.ini seeds differ from config/seeds.txt")
    require('*.reflector[*].app[0].localPort = 1025' in ini,
            "DNS reflector source port must be frozen to 1025")
    scenarios = (ROOT / "config" / "scenarios.yaml").read_text(encoding="utf-8")
    require("ethernet_interface_queue_packets_effective: 1000" in scenarios,
            "config/scenarios.yaml must record the effective 1000-packet queue")
    ethernet_interface = (inet_root / "src" / "inet" /
                          "linklayer" / "ethernet" / "EthernetInterface.ned")
    require(ethernet_interface.is_file(), "INET 4.5.4 EthernetInterface.ned is missing")
    require(re.search(r"packetCapacity\s*=\s*default\(1000\)",
                      ethernet_interface.read_text(encoding="utf-8")) is not None,
            "INET 4.5.4 effective Ethernet queue is not the documented 1000 packets")
    frozen_ini_fragments = [
        "sim-time-limit = 120s", "warmup-period = 10s",
        "*.benign[*].app[0].messageLength = 320B",
        "*.benign[*].app[0].sendInterval = uniform(1s, 2s)",
        "*.attacker[*].app[0].messageLength = 1024B",
        "*.attacker[*].app[0].sendInterval = 1ms",
        "*.attacker[*].app[*].sendBytes = 1B",
        "*.reflector[*].app[0].messageLength = 4096B",
        "*.reflector[*].app[0].sendInterval = 2ms",
    ]
    for fragment in frozen_ini_fragments:
        require(fragment in ini, f"omnetpp.ini omits frozen setting: {fragment}")
    ned = (ROOT / "src" / "ddosvalidation" / "simulations" /
           "DDoSNetwork.ned").read_text(encoding="utf-8")
    require("channel ReferenceEth100M extends Eth100M" in ned and "length = 10m" in ned,
            "DDoSNetwork.ned must use 10 m INET Eth100M links")
    feature_mapping = (ROOT / "config" / "feature_mapping.yaml").read_text(encoding="utf-8")
    for feature in FEATURES_8:
        require(feature in scenarios, f"config/scenarios.yaml omits {feature}")
        require(feature in feature_mapping, f"config/feature_mapping.yaml omits {feature}")
    roles = RoleMapping(ROOT / "config" / "ip_roles.json")
    dns_rules = [rule for rule in roles.rules if rule.traffic_source == "dns_reflector"]
    require(len(dns_rules) == 1 and dns_rules[0].source_port == 1025
            and dns_rules[0].destination_port == 53,
            "DNS fragment fallback must be uniquely frozen to UDP 1025-to-53")
    counts = {name: int(last) - int(first) + 1
              for name, (first, last) in roles.network_roles.items()}
    require(counts == {"benign_clients": 50, "attackers": 20,
                       "dns_reflectors": 10, "victim": 1},
            f"Frozen role counts are inconsistent: {counts}")
    requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8")
    require("scapy==2.6.1" in requirements, "Scapy must be pinned to 2.6.1")
    print(json.dumps({"status": "consistent", "python": "3.10.5",
                      "inet": inet_version,
                      "seeds": len(seeds), "features": len(FEATURES_8),
                      "role_counts": counts}, indent=2))


if __name__ == "__main__":
    main()
