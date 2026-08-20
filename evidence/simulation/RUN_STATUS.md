# Canonical run5 status — INET 4.5.4

This is the completed manuscript-eligible simulation campaign. It used
OMNeT++ 6.0.3 and the verified release build from
`../samples/inet4.5`, whose `Version` is `inet-4.5.4-0a1d409733`.
The launcher's version preflight passed before this fresh output directory was
created. The earlier `full-canonical-v1-run4` campaign is retained separately
as noncanonical diagnostic evidence because it used INET 4.4.1.

## Simulation completion evidence

- Launcher exit status: 0.
- `Normal.log`: 10 runs, 10 successful.
- `UDPFlood.log`: 10 runs, 10 successful.
- `SYNFlood.log`: 10 runs, 10 successful.
- `DNSAmplification.log`: 10 runs, 10 successful.
- Each scenario has exactly the ten frozen seeds in `config/seeds.txt`, with no
  missing or extra SCA completion artifact.
- Artifact audit: 40 nonempty PCAP, 40 nonempty SCA, 40 nonempty VEC, and 40
  nonempty VCI files; zero zero-byte files.
- Campaign size at audit: 47.84 GiB.
- No `opp_run` process remained after completion.

No result file in this directory was deleted, moved, or overwritten.

## Canonical labelled extraction

Extraction used only `.venv-final/Scripts/python.exe` (Python 3.10.5, Scapy
2.6.1) and wrote new artifacts to
`extracted/full-canonical-v1-run5-inet454-labeled8`.

- 40 labelled 8-feature CSVs and 40 extraction sidecars.
- 10,312 total flows: 2,012 BENIGN and 8,300 DDoS.
- Scenario totals:
  - Normal: 500 BENIGN, 0 DDoS.
  - UDPFlood: 512 BENIGN, 200 DDoS.
  - SYNFlood/TCP connection flood: 500 BENIGN, 8,000 DDoS.
  - DNSAmplification: 500 BENIGN, 100 DDoS.
- Aggregate validator status: `valid`.
- Unknown or invalid labelled flows: 0.
- Zero-duration flows: 0.
- Incomplete captures skipped: 0.

The DNS sidecars record 1,032,100 observed fallback fragments and 1,165,639
incomplete fragment datagrams across the ten seeds. These are captured-only
diagnostics: observed packets and IPv4 bytes are counted, while missing
fragments are never synthesized.

Only this run5-INET4.5.4 campaign may be used for final manuscript simulation
results.
