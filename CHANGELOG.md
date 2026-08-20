# Changelog

## 1.0.0 final publication candidate - 2026-08-20

- Added the approved MIT and CC BY 4.0 licensing scope, third-party notices,
  confirmed repository URL, reserved Zenodo DOI, and release date.
- Generated and visually validated Figure 5 from all ten frozen hold-out
  prediction seeds and Figure 6 from the author-prespecified feature-8 XGBoost
  seed-104729 artifact using a non-performance-based selection rule.
- Added figure provenance, publication-freeze validation, and final archive
  integrity metadata. No scientific stage was rerun.

## 1.0.0 public candidate - 2026-08-19

- Curated a clean allowlisted package around verified canonical run5 aggregate
  evidence; excluded raw/row-level datasets, PCAP/SCA/VEC/VCI, model payloads,
  run4, confidential editorial files, environments, caches, and private paths.
- Added public-safe dataset provenance, component/model/Code audits, release
  manifests, portable path examples, licensing gate, citation metadata,
  dual-use guidance, and separate A–F reproduction workflows.
- Added non-overwriting compatible Figure 5 ROC and Figure 6 all-seed XGBoost
  TreeSHAP generators. Their future outputs require author review and are not
  retroactively claimed as canonical evidence.
- No simulation, extraction, dataset preparation, training, prediction, or
  statistical-analysis stage was rerun during release assembly.

## Unreleased - reconstructed protocol

- Reconstructed the OMNeT++/INET topology and application configurations from
  the manuscript description.
- Added ten explicit seeds, PCAP-based feature extraction, CICDDoS2019
  provenance tracking, model training, OMNeT++ evaluation, confidence intervals,
  and paired McNemar analysis.
- Changed Windows launchers to pass INET to `opp_run` as the relative sibling
  path `../inet`, avoiding both `/c/...` and `C:` path parsing failures.
- Corrected switch interface-count expressions to reference the enclosing
  network parameters through `parent` under OMNeT++ 6.0.3.
- Enabled computed FCS and protocol checksums so INET 4.5.4 can serialize the
  server-side Ethernet traffic into PCAP files.
- Recorded the successful 120-second Normal smoke test and made the smoke
  launcher accept any one of the four configurations.
- Changed the TCP connection-flood payload from 0 B to 1 B because INET 4.5.4
  `TcpSessionApp` rejects an empty script when `sendBytes` is zero; clarified
  throughout that the scenario is connection exhaustion, not raw SYN traffic.
- Replaced `TcpGenericServerApp` with `TcpSinkApp` on port 80 because the former
  expects `GenericAppMsg`, whereas `TcpSessionApp` sends a byte stream.
- Recorded the successful UDPFlood seed-0 smoke test: 120 simulated seconds,
  32,015,532 events, and 917,862 packets received by server application 0.
- Recorded the successful DNSAmplification seed-0 smoke test: 120 simulated
  seconds, 20,787,303 events, 222.532 seconds of wall-clock runtime, and
  115,497 packets received by the DNS sink (server application 1).
- Recorded the successful SYNFlood/TCP-connection-flood seed-0 smoke test after
  the `TcpSinkApp` correction: 120 simulated seconds, 229,052 events, and 20
  TCP connections reported by each of the 20 attacker hosts (400 configured
  client sessions). This is evidence for a TCP connection flood, not a raw
  half-open SYN flood.
- Added frozen per-flow IPv4 role/transport rules in `config/ip_roles.json`;
  unknown or ambiguous TCP/UDP flows now fail rather than inheriting a scenario
  label.
- Expanded extraction and CICDDoS2019 preparation to the canonical nested
  4/6/8-feature superset, with microsecond duration and documented IPv4-layer
  packet lengths.
- Added port association for non-initial IPv4 fragments so DNS-amplification
  fragments contribute to directional packet and byte totals.
- Deferred out-of-order non-initial IPv4 fragments until their first fragment
  exposes transport ports, retaining original timestamps and byte counts;
  captures missing the first fragment and lacking a unique configured fallback
  still fail explicitly.
- Added a strictly configured DNS-only UDP 1025-to-53 fallback for observed
  non-initial reflector fragments whose first fragment was lost before the
  victim capture. Observed packet/byte counts are retained without inventing
  the absent first packet; other unresolved fragment roles still fail.
- Froze the DNS reflector `UdpBasicApp` local port explicitly to 1025 after the
  completed run4 SCA and packet data confirmed INET's prior ephemeral binding
  selected that port on every reflector.
- Retained captured fragments when a known-port datagram lacks its final
  fragment, recording incomplete-datagram and fallback counts in a non-
  overwriting `.extraction.json` sidecar. Only observed packets and bytes are
  counted; missing fragments are never synthesized.
- Added strict labelled-CSV validation and non-overwriting batch extraction.
- Changed smoke/full simulation launchers to create new explicit or timestamped
  output directories and refuse existing targets, preventing accidental result
  replacement.
- Quoted command-line PCAP filename overrides as OMNeT++ string expressions and
  added the packaged MinGW runtime directory for non-interactive launchers.
- Added a 60 GiB output-filesystem preflight after an approved full campaign
  was safely stopped with 10 Normal and 3 UDPFlood seeds complete; all partial
  artifacts were preserved and are documented in the run directory.
- Made batch extraction require a companion SCA completion artifact, so an
  interrupted PCAP is skipped rather than silently entering analysis.
- Extracted and validated all 23 completed captures from the storage-limited
  campaign attempt: 9,213 per-flow-labelled records (1,153 BENIGN and 8,060
  DDoS), zero unknown/invalid flows; the incomplete UDP capture was skipped and
  preserved.
- Completed a fresh 40-run campaign (`full-canonical-v1-run4`) with
  ten seeds for each scenario and 40 nonempty PCAP/SCA/VEC/VCI artifacts
  (47.83 GiB). Extracted 10,312 labelled flows into 40 labelled 8-feature
  tables; aggregate validation reported `valid`, zero unknown/invalid flows,
  zero skipped captures, and zero zero-duration flows.
- Recorded captured-only DNS fragmentation diagnostics for the canonical
  campaign: 1,032,100 observed fragments used the frozen reflector/UDP
  1025-to-53 fallback and 1,165,639 incomplete datagrams were retained without
  synthesizing missing packets or bytes.
- Discovered during the post-run environment audit that the launcher had
  selected sibling `../inet` (tag `v4.4.1`) rather than the required INET
  4.5.4 build. Marked run4 noncanonical while preserving every artifact;
  changed both launchers to select `../samples/inet4.5` and fail before output
  creation unless its `Version` identifies 4.5.4.
- Added non-overwriting per-scenario console logs to full campaigns so runtime
  completion evidence is preserved with PCAP/SCA/VEC/VCI artifacts.
- Added stable source-row/sample identifiers, before/after cleaning class
  counts, duplicate counts, provenance, and without-replacement sampling.
- Completed the canonical run5 campaign with the verified INET 4.5.4 release
  build: exactly 10 successful runs per scenario and 40 nonempty PCAP/SCA/VEC/
  VCI sets. Preserved run4 as noncanonical INET-4.4.1 diagnostic evidence.
- Inventoried all 18 official CICDDoS2019 data CSVs plus one preserved ancillary
  lock file recursively, recording relative paths, sizes, SHA-256 hashes,
  columns, labels, rows, duplicates, invalid values, and provenance without
  modifying the source tree.
- Replaced fixed per-class sampling with the approved maximum-BENIGN protocol:
  normalize and compare every one of the 88 official source fields for exact
  deduplication, retain every clean finite unique BENIGN record, and select an
  exactly matched DDoS count without replacement using deterministic
  day/file/attack-stratified Hamilton allocation.
- Added precomputed class-preserving source-file-group splits for all ten seeds,
  machine-readable selection/split provenance and hashes, and an independent
  validator that proves zero sample-ID, full-record-hash, duplicate-record, and
  source-group leakage before training.
- Removed record-level splitting from the training entry point. Training now
  requires the independently validated split manifest and reuses it unchanged
  across 4/6/8 features and all model families.
- Verified the approved matched preparation at `N=108,381` per class (216,762
  selected rows). Independent validation passed 31/31 checks, including exact
  balance, finite features, full-record uniqueness, source provenance, all ten
  class-preserving source-file splits, and zero sample-ID/row-hash/group
  leakage. No model training was started during preparation or validation.
- Added matched 4/6/8 training partitions, per-feature artifact directories,
  full binary metrics, saved feature/preprocessing/model/environment metadata,
  and environment-mixing refusal.
- Replaced scenario-wide evaluation truth with required per-flow ground truth;
  added run/scenario metrics, prediction proportions, agreement, Cohen's kappa,
  ensemble agreement, and across-simulation-seed confidence intervals.
- Added seed-paired feature/model analysis, matched-only exact McNemar tests,
  paired error-difference confidence intervals, and Holm correction.
- Completed the approved canonical 4/6/8-feature training for all ten frozen
  seeds and all four model families, producing 120 metric rows and 5,225,664
  matched hold-out predictions under Python 3.10.5 in `.venv-final`.
- Added the identical SciKeras model factory to the OMNeT++ evaluator so joblib
  can resolve the immutable trainer-script `__main__.keras_mlp` reference;
  completed run5 evaluation, matched statistical analysis, and final tables.
- Preserved ordinary mean-based t intervals in raw audit columns while
  constraining only displayed CI endpoints for [0,1]-bounded classification
  metrics; seed values, means, SDs, MCC, paired differences, and tests remain
  unchanged.
- Added concise all-seed hold-out, per-scenario OMNeT++, feature-sensitivity,
  confusion, agreement, and matched-McNemar tables plus a 36-check timestamped
  reviewer validator. No favorable training seed is selected.
- Recorded the effective INET 4.5.4 Ethernet-interface queue capacity of 1,000
  packets, added the mandatory reviewer evidence map and terminology audit, and
  generated a non-uploading public-release manifest with inclusion decisions,
  hashes, exact commands, restrictions, and the reserved Zenodo DOI.
- Added focused synthetic tests, configuration consistency checks, and final
  manuscript-table assembly.

Record every correction made during smoke testing here before creating the
frozen `protocol-v1.0.0` tag. Do not record result-driven parameter tuning as a
correction; instead predefine and justify a new protocol version.
