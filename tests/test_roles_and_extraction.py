from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

from scapy.all import IP, TCP, UDP, Raw, fragment, wrpcap

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from extract_features import Flow, extract, flow_row  # noqa: E402
from pipeline_common import RoleMapping  # noqa: E402


class RoleMappingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.roles = RoleMapping(ROOT / "config" / "ip_roles.json")

    def test_all_role_boundaries(self):
        expectations = {
            "10.0.0.2": "benign_clients", "10.0.0.51": "benign_clients",
            "10.0.0.52": "attackers", "10.0.0.71": "attackers",
            "10.0.0.130": "victim",
            "10.0.0.146": "dns_reflectors", "10.0.0.155": "dns_reflectors",
        }
        for address, expected in expectations.items():
            with self.subTest(address=address):
                self.assertEqual(self.roles.role_for(address), expected)
        for address in ("10.0.0.1", "10.0.0.72", "10.0.0.129",
                        "10.0.0.131", "10.0.0.145", "10.0.0.156"):
            with self.subTest(address=address):
                self.assertIsNone(self.roles.role_for(address))

    def test_exact_traffic_labels(self):
        cases = [
            ((17, "10.0.0.2", 40000, "10.0.0.130", 9000),
             ("BENIGN", "benign_client")),
            ((17, "10.0.0.52", 40001, "10.0.0.130", 9000),
             ("DDoS", "udp_attacker")),
            ((6, "10.0.0.71", 40002, "10.0.0.130", 80),
             ("DDoS", "tcp_attacker")),
            ((17, "10.0.0.146", 1025, "10.0.0.130", 53),
             ("DDoS", "dns_reflector")),
        ]
        for values, expected in cases:
            with self.subTest(values=values):
                self.assertEqual(self.roles.classify(*values), expected)

    def test_unknown_ip_and_ambiguous_transport_fail(self):
        bad = [
            (17, "10.0.0.72", 1, "10.0.0.130", 9000),
            (6, "10.0.0.52", 1, "10.0.0.130", 9000),
            (17, "10.0.0.52", 1, "10.0.0.130", 53),
            (17, "10.0.0.130", 9000, "10.0.0.2", 1),
        ]
        for values in bad:
            with self.subTest(values=values), self.assertRaisesRegex(ValueError, "Unknown or ambiguous"):
                self.roles.classify(*values)


class FeatureMathTests(unittest.TestCase):
    def test_directional_counts_lengths_mean_duration_and_rates(self):
        flow = Flow(17, "10.0.0.2", 12345, "10.0.0.130", 9000,
                    1.0, 1.0, "BENIGN", "benign_client", 1)
        flow.add(True, 1.0, 100)
        flow.add(True, 1.5, 300)
        flow.add(False, 2.0, 200)
        row = flow_row(flow, "UDPFlood", "seed1")
        self.assertEqual(row["ground_truth_label"], "BENIGN")  # no scenario leakage
        self.assertEqual(row["Total Fwd Packets"], 2)
        self.assertEqual(row["Total Backward Packets"], 1)
        self.assertEqual(row["Total Length of Fwd Packets"], 400)
        self.assertEqual(row["Total Length of Bwd Packets"], 200)
        self.assertEqual(float(row["Fwd Packet Length Mean"]), 200.0)
        self.assertEqual(row["Flow Duration"], 1_000_000)
        self.assertEqual(float(row["Flow Bytes/s"]), 600.0)
        self.assertEqual(float(row["Flow Packets/s"]), 3.0)

    def test_zero_duration_has_explicit_undefined_rates(self):
        flow = Flow(17, "10.0.0.2", 12345, "10.0.0.130", 9000,
                    1.0, 1.0, "BENIGN", "benign_client", 1)
        flow.add(True, 1.0, 100)
        row = flow_row(flow, "Normal", "seed1")
        self.assertEqual(row["Flow Duration"], 0)
        self.assertEqual(row["Flow Bytes/s"], "")
        self.assertEqual(row["Flow Packets/s"], "")


class SyntheticPcapTests(unittest.TestCase):
    def _extract_packets(self, packets, scenario="DNSAmplification"):
        with tempfile.TemporaryDirectory() as directory:
            pcap = Path(directory) / "synthetic.pcap"
            output = Path(directory) / "flows.csv"
            wrpcap(str(pcap), packets)
            summary = extract(pcap, output, scenario, "seed-test", 15.0, 120.0)
            import csv
            with output.open(newline="", encoding="utf-8") as stream:
                return list(csv.DictReader(stream)), summary

    def test_fragmented_ipv4_counts_every_fragment_and_bytes(self):
        datagram = IP(src="10.0.0.146", dst="10.0.0.130", id=77) / UDP(
            sport=1025, dport=53) / Raw(b"x" * 4000)
        fragments = fragment(datagram, fragsize=1000)
        for index, packet in enumerate(fragments):
            packet.time = 1.0 + index * 0.001
        frame, summary = self._extract_packets(fragments)
        self.assertEqual(summary["unknown_or_invalid_flows"], 0)
        self.assertEqual(len(frame), 1)
        self.assertEqual(frame[0]["traffic_source"], "dns_reflector")
        self.assertEqual(int(frame[0]["Total Fwd Packets"]), len(fragments))
        expected_bytes = sum(len(bytes(packet)) for packet in fragments)
        self.assertEqual(int(frame[0]["Total Length of Fwd Packets"]), expected_bytes)

    def test_out_of_order_fragment_before_first_is_deferred_without_loss(self):
        datagram = IP(src="10.0.0.154", dst="10.0.0.130", id=308) / UDP(
            sport=1025, dport=53) / Raw(b"x" * 4000)
        fragments = fragment(datagram, fragsize=1000)
        reordered = [fragments[1], fragments[0], *fragments[2:]]
        for index, packet in enumerate(reordered):
            packet.time = 2.0 + index * 0.001
        frame, _ = self._extract_packets(reordered)
        self.assertEqual(len(frame), 1)
        self.assertEqual(frame[0]["traffic_source"], "dns_reflector")
        self.assertEqual(int(frame[0]["Total Fwd Packets"]), len(reordered))
        self.assertEqual(int(frame[0]["Total Length of Fwd Packets"]),
                         sum(len(bytes(packet)) for packet in reordered))
        self.assertEqual(float(frame[0]["flow_start_s"]), 2.0)

    def test_fragment_capture_missing_first_fragment_fails(self):
        datagram = IP(src="10.0.0.52", dst="10.0.0.130", id=99) / UDP(
            sport=45000, dport=9000) / Raw(b"x" * 4000)
        fragments = fragment(datagram, fragsize=1000)[1:]
        for index, packet in enumerate(fragments):
            packet.time = 3.0 + index * 0.001
        with self.assertRaisesRegex(ValueError, "missing their first fragment"):
            self._extract_packets(fragments)

    def test_dns_fragments_missing_first_use_frozen_port_fallback(self):
        datagram = IP(src="10.0.0.146", dst="10.0.0.130", id=100) / UDP(
            sport=1025, dport=53) / Raw(b"x" * 4000)
        observed = fragment(datagram, fragsize=1000)[1:]
        for index, packet in enumerate(observed):
            packet.time = 4.0 + index * 0.001
        frame, _ = self._extract_packets(observed)
        self.assertEqual(len(frame), 1)
        self.assertEqual(frame[0]["src_port"], "1025")
        self.assertEqual(frame[0]["dst_port"], "53")
        self.assertEqual(frame[0]["traffic_source"], "dns_reflector")
        self.assertEqual(int(frame[0]["Total Fwd Packets"]), len(observed))
        self.assertEqual(int(frame[0]["Total Length of Fwd Packets"]),
                         sum(len(bytes(packet)) for packet in observed))

    def test_missing_final_fragment_counts_observed_packets_and_is_reported(self):
        datagram = IP(src="10.0.0.146", dst="10.0.0.130", id=101) / UDP(
            sport=1025, dport=53) / Raw(b"x" * 4000)
        observed = fragment(datagram, fragsize=1000)[:-1]
        for index, packet in enumerate(observed):
            packet.time = 5.0 + index * 0.001
        frame, summary = self._extract_packets(observed)
        self.assertEqual(len(frame), 1)
        self.assertEqual(int(frame[0]["Total Fwd Packets"]), len(observed))
        self.assertEqual(int(frame[0]["Total Length of Fwd Packets"]),
                         sum(len(bytes(packet)) for packet in observed))
        self.assertEqual(summary["incomplete_fragment_datagrams"], 1)

    def test_benign_flow_in_attack_scenario_remains_benign(self):
        request = IP(src="10.0.0.51", dst="10.0.0.130") / UDP(
            sport=45000, dport=9000) / Raw(b"request")
        reply = IP(src="10.0.0.130", dst="10.0.0.51") / UDP(
            sport=9000, dport=45000) / Raw(b"reply")
        request.time, reply.time = 2.0, 2.5
        frame, _ = self._extract_packets([request, reply], scenario="UDPFlood")
        self.assertEqual(frame[0]["ground_truth_label"], "BENIGN")
        self.assertEqual(int(frame[0]["Total Fwd Packets"]), 1)
        self.assertEqual(int(frame[0]["Total Backward Packets"]), 1)

    def test_unknown_transport_flow_fails_clearly(self):
        packet = IP(src="10.0.0.72", dst="10.0.0.130") / TCP(sport=1, dport=80)
        packet.time = 1.0
        with self.assertRaisesRegex(ValueError, "Unknown or ambiguous transport flow"):
            self._extract_packets([packet], scenario="SYNFlood")


if __name__ == "__main__":
    unittest.main()
