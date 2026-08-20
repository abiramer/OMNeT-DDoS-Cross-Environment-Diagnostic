#!/usr/bin/env python3
"""Extract strictly labelled CIC-compatible bidirectional IPv4 flows.

The first observed transport packet establishes forward direction. Packet
lengths are IPv4 total lengths (header plus payload), not Ethernet frame sizes.
Every IPv4 fragment is counted and associated with the ports in its first
fragment; an orphan non-initial fragment is a hard error.
"""
from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from pathlib import Path

from scapy.all import IP, IPv6, TCP, UDP, PcapReader

from pipeline_common import RoleMapping, stable_id

DEFAULT_ROLE_CONFIG = Path(__file__).resolve().parents[1] / "config" / "ip_roles.json"


@dataclass
class Flow:
    protocol: int
    src: str
    sport: int
    dst: str
    dport: int
    start: float
    last: float
    ground_truth_label: str
    traffic_source: str
    sequence: int
    fwd_packets: int = 0
    bwd_packets: int = 0
    fwd_bytes: int = 0
    bwd_bytes: int = 0

    def add(self, forward: bool, timestamp: float, size: int) -> None:
        # A non-initial IPv4 fragment may be observed before its first
        # fragment.  It is processed once the ports become known, so retain
        # its original capture timestamp even though it is added later.
        self.start = min(self.start, timestamp)
        self.last = max(self.last, timestamp)
        if forward:
            self.fwd_packets += 1
            self.fwd_bytes += size
        else:
            self.bwd_packets += 1
            self.bwd_bytes += size


def canonical(proto: int, src: str, sport: int, dst: str, dport: int):
    a, b = (src, sport), (dst, dport)
    return (proto, a, b) if a <= b else (proto, b, a)


def packet_records(packet, fragments: dict[tuple, tuple[int, int]],
                   pending: dict[tuple, list[tuple[float, int, bool, int]]],
                   roles: RoleMapping, fragment_stats: dict[str, int]):
    """Return zero or more transport records, resolving reordered fragments.

    Non-initial fragments that precede their first fragment are held with
    their original timestamp and IPv4 length.  Once the first fragment exposes
    the ports, the held records are returned in capture-time order.  A capture
    that never supplies the first fragment remains a hard error at EOF.
    """
    if IPv6 in packet and (TCP in packet or UDP in packet):
        raise ValueError("IPv6 transport traffic is not covered by config/ip_roles.json")
    if IP not in packet:
        return []
    net = packet[IP]
    proto = int(net.proto)
    if proto not in (6, 17):
        return []
    src, dst = str(net.src), str(net.dst)
    fragment_key = (str(net.src), str(net.dst), proto, int(net.id))
    offset = int(net.frag)
    timestamp = float(packet.time)
    size = int(net.len or len(bytes(net)))
    if offset == 0:
        layer = TCP if proto == 6 else UDP
        if layer not in packet:
            raise ValueError(f"First IPv4 fragment lacks its transport header: {fragment_key}")
        ports = (int(packet[layer].sport), int(packet[layer].dport))
        buffered = pending.pop(fragment_key, [])
        if buffered and not bool(net.flags.MF):
            raise ValueError(f"Malformed IPv4 datagram has later fragments but MF is unset: {fragment_key}")
        saw_final = any(not more_fragments for _, _, more_fragments, _ in buffered)
        if bool(net.flags.MF) and not saw_final:
            fragments[fragment_key] = ports
        else:
            fragments.pop(fragment_key, None)
        sport, dport = ports
        records = [(proto, src, sport, dst, dport, size, timestamp)]
        records.extend((proto, src, sport, dst, dport, held_size, held_time)
                       for held_time, held_size, _, _ in buffered)
        return sorted(records, key=lambda item: item[-1])
    if fragment_key not in fragments:
        fallback = roles.fragment_fallback_ports(proto, src, dst)
        if fallback is not None:
            fragment_stats["fallback_fragments"] += 1
            sport, dport = fallback
            return [(proto, src, sport, dst, dport, size, timestamp)]
        fragment_stats["deferred_fragments"] += 1
        pending.setdefault(fragment_key, []).append(
            (timestamp, size, bool(net.flags.MF), offset))
        return []
    sport, dport = fragments[fragment_key]
    if not bool(net.flags.MF):
        del fragments[fragment_key]
    return [(proto, src, sport, dst, dport, size, timestamp)]


def flow_row(flow: Flow, scenario: str, run: str) -> dict[str, object]:
    duration_s = max(0.0, flow.last - flow.start)
    duration_us = int(round(duration_s * 1_000_000))
    packets = flow.fwd_packets + flow.bwd_packets
    total_bytes = flow.fwd_bytes + flow.bwd_bytes
    # A rate for equal timestamps is mathematically undefined. Empty CSV fields
    # preserve that fact; validate_features.py checks this convention.
    bytes_rate = total_bytes / duration_s if duration_s > 0 else None
    packets_rate = packets / duration_s if duration_s > 0 else None
    return {
        "flow_id": stable_id(scenario, run, flow.sequence, flow.protocol, flow.src,
                             flow.sport, flow.dst, flow.dport, f"{flow.start:.9f}"),
        "run": run, "scenario": scenario,
        "protocol": {6: "TCP", 17: "UDP"}[flow.protocol],
        "src_ip": flow.src, "src_port": flow.sport,
        "dst_ip": flow.dst, "dst_port": flow.dport,
        "flow_start_s": f"{flow.start:.9f}",
        "flow_duration_s": f"{duration_s:.9f}",
        "ground_truth_label": flow.ground_truth_label,
        "traffic_source": flow.traffic_source,
        "Total Fwd Packets": flow.fwd_packets,
        "Total Backward Packets": flow.bwd_packets,
        "Flow Bytes/s": "" if bytes_rate is None else f"{bytes_rate:.9f}",
        "Flow Packets/s": "" if packets_rate is None else f"{packets_rate:.9f}",
        "Flow Duration": duration_us,
        "Total Length of Fwd Packets": flow.fwd_bytes,
        "Total Length of Bwd Packets": flow.bwd_bytes,
        "Fwd Packet Length Mean": (f"{flow.fwd_bytes / flow.fwd_packets:.9f}"
                                   if flow.fwd_packets else ""),
    }


FIELDS = [
    "flow_id", "run", "scenario", "protocol", "src_ip", "src_port", "dst_ip",
    "dst_port", "flow_start_s", "flow_duration_s", "ground_truth_label",
    "traffic_source", "Total Fwd Packets", "Total Backward Packets",
    "Flow Bytes/s", "Flow Packets/s", "Flow Duration",
    "Total Length of Fwd Packets", "Total Length of Bwd Packets",
    "Fwd Packet Length Mean",
]


def extract(pcap: Path, output: Path, scenario: str, run: str,
            idle_timeout: float, active_timeout: float,
            role_config: Path = DEFAULT_ROLE_CONFIG) -> dict[str, int]:
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite existing extracted CSV: {output}")
    metadata_output = output.with_suffix(".extraction.json")
    if metadata_output.exists():
        raise FileExistsError(f"Refusing to overwrite extraction metadata: {metadata_output}")
    roles = RoleMapping(role_config)
    flows: dict[tuple, Flow] = {}
    fragments: dict[tuple, tuple[int, int]] = {}
    pending_fragments: dict[tuple, list[tuple[float, int, bool, int]]] = {}
    fragment_stats = {"deferred_fragments": 0, "fallback_fragments": 0}
    rows: list[dict[str, object]] = []
    sequence = 0
    with PcapReader(str(pcap)) as packets:
        for packet in packets:
            for proto, src, sport, dst, dport, size, now in packet_records(
                    packet, fragments, pending_fragments, roles, fragment_stats):
                key = canonical(proto, src, sport, dst, dport)
                flow = flows.get(key)
                if flow and (now - flow.last > idle_timeout or now - flow.start > active_timeout):
                    rows.append(flow_row(flow, scenario, run))
                    del flows[key]
                    flow = None
                if flow is None:
                    label, traffic_source = roles.classify(proto, src, sport, dst, dport)
                    sequence += 1
                    flow = Flow(proto, src, sport, dst, dport, now, now,
                                label, traffic_source, sequence)
                    flows[key] = flow
                forward = ((src, sport, dst, dport) ==
                           (flow.src, flow.sport, flow.dst, flow.dport))
                flow.add(forward, now, size)
    if pending_fragments:
        count = sum(len(items) for items in pending_fragments.values())
        example = next(iter(pending_fragments))
        raise ValueError(
            f"Capture ended with {count} non-initial IPv4 fragment(s) missing "
            f"their first fragment; example={example}")
    # If the first fragment was observed, its ports are known and every
    # observed fragment has already contributed its packet and byte count.  A
    # missing final fragment is capture/network loss, not mapping ambiguity;
    # record it without inventing the absent packet.
    incomplete_fragment_datagrams = len(fragments)
    rows.extend(flow_row(flow, scenario, run) for flow in flows.values())
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    summary = {
        "flows": len(rows),
        "unknown_or_invalid_flows": 0,
        "deferred_fragments": fragment_stats["deferred_fragments"],
        "fallback_fragments": fragment_stats["fallback_fragments"],
        "incomplete_fragment_datagrams": incomplete_fragment_datagrams,
        "packet_count_policy": "captured IPv4 fragments only; no missing fragment synthesized",
    }
    metadata_output.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pcap", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--scenario", required=True)
    parser.add_argument("--run", required=True)
    parser.add_argument("--idle-timeout", type=float, default=15.0)
    parser.add_argument("--active-timeout", type=float, default=120.0)
    parser.add_argument("--role-config", type=Path, default=DEFAULT_ROLE_CONFIG)
    args = parser.parse_args()
    summary = extract(args.pcap, args.output, args.scenario, args.run,
                      args.idle_timeout, args.active_timeout, args.role_config)
    print(f"Extracted {summary['flows']} labelled flows; unknown/invalid: 0; "
          f"fallback fragments: {summary['fallback_fragments']}; "
          f"incomplete fragment datagrams: {summary['incomplete_fragment_datagrams']}; "
          f"output={args.output}")


if __name__ == "__main__":
    main()
