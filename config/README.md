# Configuration contracts

`ip_roles.json` is the frozen, machine-readable ground-truth identity mapping.
Its ranges are inclusive. A flow is classified from the first observed packet's
source/destination identities, IP protocol, and destination service port. Any
TCP/UDP flow matching zero or multiple rules is an extraction error.
The DNS rule also freezes source port 1025. This uniquely permits captured
non-initial DNS fragments whose first fragment was lost before the victim to
be assigned to the UDP 1025-to-53 reflector flow; no fallback is permitted for
roles whose source port is not explicitly frozen.

`feature_mapping.yaml` defines the bidirectional key, timeouts, first-packet
direction rule, eight CIC-compatible features, microsecond duration unit,
IPv4-layer length convention, fragmentation association, and zero-duration
rate convention.

`scenarios.yaml` and `applications.yaml` record the frozen simulator protocol;
`seeds.txt` is the ten-seed list shared by simulation and ML experiments.

Run `python scripts/check_config_consistency.py` after configuration edits. A
scientific methodology change requires coauthor review before complete runs.
