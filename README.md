# OMNeT++ DDoS Cross-Environment Diagnostic — final candidate v1.0.0

This clean package contains the source, configuration, tests, public-safe
provenance, and aggregate evidence needed to reproduce and audit the canonical
run5 study. It was assembled selectively; it is not a copy of the private
working repository.

Publication-freeze status: **local final candidate; not yet uploaded**. The
approved licenses and reserved publication metadata are included. No GitHub
or Zenodo upload was performed while creating this candidate.

- GitHub repository: <https://github.com/abiramer/OMNeT-DDoS-Cross-Environment-Diagnostic>
- Reserved Zenodo DOI: <https://doi.org/10.5281/zenodo.22025873>
- Version: `1.0.0`
- Release date: `2026-08-20`

## Scientific scope and interpretation

The workflow trains BENIGN-versus-DDoS classifiers on the official
CICDDoS2019 flow records and applies frozen models, without retraining, to
per-flow-labelled OMNeT++ traffic. This is a **cross-environment diagnostic**:
it measures scenario-consistent classification and exposes failures under a
controlled reconstructed protocol. It does not prove simulator realism,
fidelity, external validity, or closure of a “reality gap.”

Only run5 is canonical: OMNeT++ 6.0.3, INET 4.5.4 revision
`inet-4.5.4-0a1d409733`, Python 3.10.5, Scapy 2.6.1, ten frozen training seeds,
and ten canonical simulation seeds per scenario. Run4 used INET 4.4.1 and is
excluded from all public scientific results. No favorable seed is selected.

The TCP case is a **TCP connection-exhaustion/connection-flood scenario**, not
a raw forged half-open SYN implementation. DNS feature extraction counts only
captured IPv4 fragments and never synthesizes missing fragments.

## What is and is not included

Included:

- the NED/INI simulation project and frozen configuration;
- dataset inventory, preparation, training, evaluation, statistics, table, and
  compatible Figure 5/6 generation source;
- focused tests and configuration validation;
- model metadata, exact hyperparameters, feature order, package snapshots, and
  hashes of every frozen artifact;
- public-safe aggregate results, provenance, and reviewer validations.

Excluded:

- raw CICDDoS2019 ZIP/CSV files and all dataset rows;
- prepared/sampled row tables, split-ID tables, and row-level predictions;
- PCAP, SCA, VEC, and VCI files;
- run4, partial, smoke-output, cache, virtual-environment, and binary artifacts;
- joblib/model payloads excluded because redistribution is not approved;
- manuscripts, reviewer correspondence, internal author checklists, and local
  machine logs;
- the legacy Flask/Colab bundle, which failed the public safety gate.

See `EXCLUDED_FILES_SUMMARY.md`, `COMPONENT_COMPLETENESS.md`, and
`MODEL_ARTIFACTS_NOT_REDISTRIBUTED.md`.

## Repository structure

```text
config/                         frozen roles, features, scenarios, applications, seeds, path template
src/ddosvalidation/             NED topology and package definitions
scripts/                        canonical pipeline and compatible reporting utilities
tests/                          synthetic/unit tests
evidence/environment/           Python and package snapshots
evidence/provenance/            aggregate source inventory, cleaning, sampling, split/leakage evidence
evidence/training/              aggregate ten-seed training metrics
evidence/model_metadata/        exact parameters and feature order; no model payloads
evidence/model_inventory/       hashes/status for every frozen model-directory artifact
evidence/omnet/                 aggregate run/scenario metrics and agreement; no flow predictions
evidence/statistics/            aggregate summaries, paired tests, McNemar, tables
evidence/validation/            public-safe validation reports and hashes
```

No custom `.cc`, `.h`, or `.msg` module exists in the implemented project, and
no package-local Makefile is required. The topology instantiates INET modules
through NED and is launched with `opp_run`; INET itself is an external
dependency.

## Exact environment

- OMNeT++ 6.0.3
- INET Framework 4.5.4, verified revision `inet-4.5.4-0a1d409733`
- Python 3.10.5 (exact, not merely any Python 3.10)
- packages pinned by `requirements.txt`; frozen installed snapshot under
  `evidence/environment/`
- Scapy 2.6.1
- recommended reference OS/compiler: Ubuntu 22.04.5 LTS / GCC 11.4.0; record
  the actual reproduction host separately

The canonical Windows layout used `../samples/inet4.5` relative to this
project. Public users may install elsewhere, but must pass/configure INET 4.5.4
and must not select INET 4.4.1.

### Installation

From an OMNeT++ 6.0.3 MinGW shell or a Unix shell with OMNeT++ initialized:

```bash
# Create the environment with an already-installed CPython 3.10.5.
py -3.10 -m venv .venv-final        # Windows Python launcher example
# python3.10 -m venv .venv-final    # Unix example; verify it is exactly 3.10.5

source .venv-final/Scripts/activate # Windows OMNeT++ MinGW shell
# source .venv-final/bin/activate   # Unix
python --version
python -m pip install -r requirements.txt
python -m pip check
```

Stop if `python --version` is not exactly `Python 3.10.5`. Do not combine
artifacts made by different Python environments.

Set portable external roots and initialize OMNeT++ before simulation. Windows
MinGW-shell example:

```bash
export OMNET_ROOT="/c/Tools/omnetpp-6.0.3"
export INET_ROOT="/c/Tools/inet-4.5.4"
source "$OMNET_ROOT/setenv" -f
opp_run -v
head -n 1 "$INET_ROOT/Version"
test "$(head -n 1 "$INET_ROOT/Version")" = "inet-4.5.4-0a1d409733"
```

Unix example: set `OMNET_ROOT=/opt/omnetpp-6.0.3` and
`INET_ROOT=/opt/inet-4.5.4`, then source `$OMNET_ROOT/setenv`.

## Portable paths

All scientific scripts accept paths via command-line arguments. Relative paths
resolve from the documented project root. `config/paths.example.yaml` is a
template for wrappers; no Python source edit is required.

Windows example:

```yaml
dataset:
  raw_root: "D:/datasets/CICDDoS2019"
simulation:
  omnet_root: "C:/Tools/omnetpp-6.0.3"
  inet_root: "C:/Tools/inet-4.5.4"
```

Unix example:

```yaml
dataset:
  raw_root: "/data/CICDDoS2019"
simulation:
  omnet_root: "/opt/omnetpp-6.0.3"
  inet_root: "/opt/inet-4.5.4"
```

Do not commit a personalized path file. Commands below use project-relative
`CICDDoS2019`, `work`, and `artifacts` paths.

## Obtain CICDDoS2019 independently

Official source: <https://www.unb.ca/cic/datasets/ddos-2019.html> (verified
2026-08-19). Obtain the official CIC-DDoS2019 CSV archives under their
applicable terms and preserve the source filenames. This package does not
redistribute dataset rows.

Expected local layout:

```text
CICDDoS2019/
  day1/01-12/
    DrDoS_DNS.csv DrDoS_LDAP.csv DrDoS_MSSQL.csv DrDoS_NTP.csv
    DrDoS_NetBIOS.csv DrDoS_SNMP.csv DrDoS_SSDP.csv DrDoS_UDP.csv
    Syn.csv TFTP.csv UDPLag.csv
  day2/03-11/
    LDAP.csv MSSQL.csv NetBIOS.csv Portmap.csv Syn.csv UDP.csv UDPLag.csv
```

The official archive names used locally were `CSV-01-12.zip` and
`CSV-03-11.zip`. Hashes, byte sizes, row counts, labels, invalid counts, and
cleaning provenance are in `PUBLIC_DATA_PROVENANCE.md` and
`evidence/provenance/official_source_inventory.csv`. A LibreOffice lock file
found beside one source CSV was excluded as ancillary metadata.

## Frozen identity, labels, and features

`config/ip_roles.json` defines the only accepted simulated transport roles:

- `10.0.0.2`–`10.0.0.51`: `BENIGN` / `benign_client`;
- `10.0.0.52`–`10.0.0.71` to UDP/9000: `DDoS` / `udp_attacker`;
- the attacker range to TCP/80: `DDoS` / `tcp_attacker`;
- `10.0.0.146`–`10.0.0.155` to UDP/53: `DDoS` / `dns_reflector`;
- victim/server: `10.0.0.130`.

Labels never come from scenario names or predictions. Unknown or ambiguous
transport flows fail. Model orientation is `BENIGN=0`, `DDoS=1`.

Nested feature order:

1. `Total Fwd Packets`
2. `Total Backward Packets`
3. `Flow Bytes/s`
4. `Flow Packets/s`
5. `Flow Duration` (integer microseconds)
6. `Total Length of Fwd Packets`
7. `Total Length of Bwd Packets`
8. `Fwd Packet Length Mean`

Packet lengths are IPv4 total lengths, not captured Ethernet-frame lengths.
Zero-duration rates are explicitly not estimable. See
`config/feature_mapping.yaml` for the complete contract.

## Numerical OMNeT++ configuration

| Parameter | Canonical value |
|---|---:|
| benign clients | 50 |
| attackers | 20 |
| DNS reflectors | 10 |
| victim/server | 1 |
| link type/capacity | `Eth100M`, 100 Mbps |
| link length / propagation delay | 10 m / 50 ns |
| Ethernet-interface queue capacity | 1,000 packets (INET 4.5.4 default; not overridden) |
| simulation duration | 120 s |
| benign UDP | uniform 1–2 s interval/client, 320-byte message, server UDP/9000 |
| UDP flood | 1 ms interval/attacker, 1,024-byte message, server UDP/9000 |
| TCP connection exhaustion | 20 sessions/attacker, open uniformly at 20–21 s, 1-byte send, close at 100 s, server TCP/80 |
| DNS amplification | 2 ms interval/reflector, 4,096-byte message, source UDP/1025 to victim UDP/53 |
| seeds | 104729, 130363, 155921, 181081, 206369, 231701, 257053, 282427, 307759, 333019 |

The exact application and scenario values are machine-readable in `config/`.

## Workflow overview

| Workflow | Runtime class | Canonical count/output |
|---|---|---|
| configuration/tests | short | consistency JSON; 22-test canonical baseline |
| one Normal/TCP smoke run | short to moderate | new timestamped simulation directory |
| one UDP/DNS smoke run | substantial | new timestamped simulation directory |
| full simulation | **long-running** | 40 runs; 10/scenario; 40 nonempty PCAP/SCA/VEC/VCI sets |
| dataset inventory/preparation | **long-running, high disk** | 70,427,637 raw rows; 216,762 selected rows |
| ten-seed 4/6/8 training | **long-running** | 120 seed/model metric rows |
| aggregate evaluation/statistics | moderate to long | 4,800 OMNeT++ metric rows; 270 paired; 660 McNemar |
| Figure 5/6 utilities | moderate to long | new CSV/SVG/metadata directory; author review required |

Every write command below uses a new output name. Never point a reproduction at
the frozen run5 paths.

## Workflow 1 — simulation only

Prerequisites: OMNeT++ 6.0.3, external INET 4.5.4 at the documented relative
location, configuration validation, and adequate disk. Inputs are `src/`,
`omnetpp.ini`, and `config/`.

Short smoke/configuration commands:

```bash
python scripts/check_config_consistency.py --inet-root "$INET_ROOT"
./scripts/run_smoke_test.sh Normal
./scripts/run_smoke_test.sh UDPFlood
./scripts/run_smoke_test.sh SYNFlood
./scripts/run_smoke_test.sh DNSAmplification
```

Individual canonical configuration names can also be checked without changing
the INI:

```bash
INET_RUN_ROOT="$(realpath --relative-to=. "$INET_ROOT")"
opp_run -u Cmdenv -n "src;${INET_RUN_ROOT}/src" -l "${INET_RUN_ROOT}/src/INET" -c Normal omnetpp.ini
opp_run -u Cmdenv -n "src;${INET_RUN_ROOT}/src" -l "${INET_RUN_ROOT}/src/INET" -c UDPFlood omnetpp.ini
opp_run -u Cmdenv -n "src;${INET_RUN_ROOT}/src" -l "${INET_RUN_ROOT}/src/INET" -c SYNFlood omnetpp.ini
opp_run -u Cmdenv -n "src;${INET_RUN_ROOT}/src" -l "${INET_RUN_ROOT}/src/INET" -c DNSAmplification omnetpp.ini
```

Those direct commands run simulations; use the smoke launcher when you want a
new guarded output path.

Full campaign — **LONG-RUNNING; creates 40 simulations and very large files**:

```bash
./scripts/run_simulations.sh results/full-reproduction-v1-inet454-NEW
```

Expected outputs: ten runs per configuration and 40 nonempty files of each
PCAP/SCA/VEC/VCI type. Validate counts, nonzero sizes, logs, and the frozen seed
set before extraction. Canonical run5 occupied about 47.84 GiB. Do not commit
these outputs.

## Workflow 2 — CICDDoS2019 preparation only

Prerequisites: user-supplied official files in the exact tree, Python 3.10.5,
requirements installed, substantial disk/time. Inputs are raw CSVs only.

```bash
python scripts/inventory_cicddos2019.py \
  --root CICDDoS2019 \
  --output-dir work/inventory/run-NEW
python scripts/validate_cicddos2019_inventory.py \
  --inventory-dir work/inventory/run-NEW \
  --source-root CICDDoS2019 \
  --output work/inventory/run-NEW/validated_summary.json
python scripts/prepare_cicddos2019.py \
  --source-root CICDDoS2019 \
  --validated-inventory work/inventory/run-NEW/validated_summary.json \
  --output-dir work/prepared/run-NEW \
  --sampling-seed 104729 \
  --split-seeds 104729 130363 155921 181081 206369 231701 257053 282427 307759 333019
python scripts/validate_prepared_dataset.py \
  --preparation-dir work/prepared/run-NEW \
  --validated-inventory work/inventory/run-NEW/validated_summary.json \
  --source-root CICDDoS2019
```

Expected canonical accounting: raw BENIGN 113,828; raw DDoS 70,313,809;
invalid removed 1,097/2,169,653; exact duplicates removed 4,350/440,457;
clean unique BENIGN `N=108,381`; select every BENIGN and exactly 108,381 DDoS
without replacement. Validation must report 31/31 checks and zero row-hash,
sample-ID, and source-group overlap for each split.

## Workflow 3 — AI training only

Prerequisites: a valid prepared table and split manifest from Workflow 2,
Python 3.10.5, pinned scientific stack, sufficient CPU/RAM/disk. The scaler is
fitted only inside each training pipeline.

**LONG-RUNNING; 3 feature sets × 10 splits × 4 model families:**

```bash
python scripts/train_models.py \
  --data work/prepared/run-NEW/cicddos2019-max-benign-feature8.parquet \
  --split-manifest work/prepared/run-NEW/split_manifest.parquet \
  --preparation-validation work/prepared/run-NEW/preparation_validation.json \
  --output-dir artifacts/models/run-NEW \
  --feature-sets 4 6 8 \
  --seeds 104729 130363 155921 181081 206369 231701 257053 282427 307759 333019
```

Expected output: 120 metric rows, matched sample/split IDs across feature sets
and model families, joblib pipelines, metadata, and predictions. Compare
aggregate metrics with `CANONICAL_RESULTS.md`; do not expect bitwise-identical
MLP floating-point results across different TensorFlow hardware/kernels.

## Workflow 4 — evaluation of frozen models

No frozen joblib payload is included, so this workflow intentionally stops
until the authors approve a separate model asset. After restoring a verified
bundle under `artifacts/models/max-benign-run5-inet454/` and matching every
hash in `evidence/model_inventory/MODEL_ARTIFACT_INVENTORY.csv`, use Workflow 5.

Validation before use:

```bash
python -m pip check
python -c "import json; print(json.load(open('evidence/environment/environment_versions.json'))['python'])"
```

Expected value is `3.10.5`. MLP loading must use the
`__main__.keras_mlp` compatibility factory described below.

## Workflow 5 — regenerate OMNeT++ evaluation

Prerequisites: separately restored verified models plus new labelled flow CSVs
from a completed simulation/extraction. Extraction commands:

```bash
./scripts/extract_all.sh \
  results/full-reproduction-v1-inet454-NEW \
  work/extracted/run-NEW
python scripts/validate_features.py \
  --input work/extracted/run-NEW/*.csv \
  --summary work/extracted/run-NEW/validation-summary.json
```

Validation must report zero unknown/invalid flows. Evaluate without retraining:

```bash
python scripts/evaluate_omnet.py \
  --features work/extracted/run-NEW/*.csv \
  --models artifacts/models/max-benign-run5-inet454 \
  --output-dir artifacts/reports/omnet-run-NEW \
  --feature-sets 4 6 8
```

Expected canonical reference: 40 labelled CSVs, 10,312 unique flows (2,012
BENIGN; 8,300 DDoS), 1,237,440 crossed predictions, and 4,800 run/scenario
metric rows. Old unlabeled flows are rejected; scenario names never recreate
ground truth.

## Workflow 6 — statistical analysis only

Prerequisites: matched seed metrics and hold-out predictions from the same
frozen training run. Runtime is moderate/long due to 5,225,664 predictions.

```bash
stamp=$(date +%Y%m%dT%H%M%S)
stats_dir="artifacts/reports/statistics-${stamp}"
python scripts/statistical_analysis.py \
  --metrics artifacts/models/run-NEW/seed_metrics.csv \
  --predictions artifacts/models/run-NEW/test_predictions.parquet \
  --output-dir "$stats_dir"
python scripts/build_final_tables.py \
  --training-statistics "$stats_dir/metrics_mean_sd_95ci.csv" \
  --training-metrics artifacts/models/run-NEW/seed_metrics.csv \
  --training-predictions artifacts/models/run-NEW/test_predictions.parquet \
  --omnet-run-metrics artifacts/reports/omnet-run-NEW/run_scenario_metrics.csv \
  --omnet-predictions artifacts/reports/omnet-run-NEW/flow_predictions.csv \
  --paired-comparisons "$stats_dir/paired_feature_and_model_comparisons.csv" \
  --mcnemar "$stats_dir/paired_mcnemar.csv" \
  --output "artifacts/reports/final-tables-${stamp}.md" \
  --supplementary-output "artifacts/reports/supplementary-index-${stamp}.md"
```

Expected reference: 108 metric-summary rows, 270 paired comparisons, and 660
matched exact McNemar tests with Holm correction. Unmatched samples are never
tested. Undefined metrics remain `not estimable`. Only displayed endpoints for
metrics naturally bounded to [0,1] are constrained to [0,1]; seed values,
means, SDs, raw t endpoints, unbounded statistics, and tests are unchanged.

## Workflow 7 — Figure 5 and Figure 6

These compatible utilities create **new**, non-overwriting outputs from frozen
artifacts. The publication-freeze outputs are included under `figures/` with
their aggregate data and provenance. They do not modify frozen predictions or
model artifacts.

Figure 5, matched ten-seed ROC summary (moderate):

```bash
python scripts/generate_figure5.py \
  --predictions artifacts/models/max-benign-run5-inet454/test_predictions.parquet \
  --output-dir artifacts/reports/figure5-feature8-NEW \
  --feature-set 8 \
  --models xgboost rf mlp hybrid
```

Outputs: curve CSV, AUC mean/SD/95% CI CSV, PNG, SVG, and metadata. Validate
that all four models and all ten seeds are present and inspect both figures.

Figure 6, author-prespecified representative XGBoost TreeSHAP summary
(moderate):

```bash
python scripts/generate_figure6.py \
  --data work/prepared/run-NEW/cicddos2019-max-benign-feature8.parquet \
  --models artifacts/models/max-benign-run5-inet454 \
  --seed-list config/seeds.txt \
  --model-inventory evidence/model_inventory/MODEL_ARTIFACT_INVENTORY.csv \
  --training-metadata artifacts/models/max-benign-run5-inet454/training_metadata.json \
  --output-dir artifacts/reports/figure6-feature8-NEW \
  --seed 104729 \
  --sample-size 10000 \
  --sampling-seed 104729
```

Outputs: aggregate CSV, PNG, SVG, caption, and provenance; no row-level SHAP
values are written. Seed 104729 is the first entry in the predefined
numerically ordered frozen seed list and was selected independently of model
performance. The script verifies the inventory hash and canonical metadata,
uses 10,000 frozen hold-out rows selected without replacement by deterministic
SHA-256 rank, and uses XGBoost 2.1.1 native tree-path-dependent TreeSHAP (no
external background sample). The contributions explain the DDoS-class raw
margin of this classifier; they are not simulator-realism or fidelity evidence.

## Workflow 8 — optional Flask demonstration

Unavailable in this candidate. The legacy Flask bundle was optional, did not
generate run5 evidence, and was excluded after credential/data/model safety
review. Do not attempt a startup command from this release. A future separate
demo must pass the controls in `CODE_AUDIT.md` and
`SECURITY_AND_DUAL_USE.md`, then undergo a localhost-only import/startup smoke
test without exposing a network service.

## Workflow 9 — complete end-to-end reproduction

Run Workflows 1, 2, 3, 5, 6, and 7 in that order, always using new `work/`,
`artifacts/`, and `results/` output names. Workflow 1's full campaign and
Workflow 3 are the two principal long-running operations; Workflow 2 is also
large and disk-intensive. Do not launch them accidentally. Workflow 4 applies
only when approved frozen assets are obtained, and Workflow 8 is unavailable.

## Tests and release validation

Short checks:

```bash
python -m compileall -q scripts tests
python scripts/check_config_consistency.py --inet-root "$INET_ROOT"
python -m unittest discover -s tests -v
bash -n scripts/*.sh
python scripts/validate_public_release.py .
```

The canonical prior test evidence was 22/22 unit tests and 31/31 preparation
checks. A warning that no libpcap provider is available is not a failure when
the synthetic file-based Scapy PCAP tests pass. Live capture is not required.

`scripts/validate_public_release.py` checks forbidden outputs, private paths,
credentials, file sizes, required components, manifests, and hashes. It does
not run simulations, preparation, training, predictions, or statistics.

## Expected canonical counts and hashes

- raw rows: 70,427,637; selected rows: 216,762 (`N=108,381` per class);
- hold-out metrics: 120 rows; matched predictions: 5,225,664 rows;
- simulations: 40 total, ten per scenario;
- labelled OMNeT++ flows: 10,312; predictions: 1,237,440 rows;
- run/scenario metrics: 4,800; paired comparisons: 270; McNemar tests: 660;
- selected-row manifest hash:
  `902c22d120dff65c5529fd0e123622a6122531d5ce5589021e987ee1b52b3575`;
- split-manifest hash:
  `0ecb7978ab509151cc1f2b4e2fbabe6b2ef98450597be8f4999d82ab92d383b5`.

Full aggregate/input hashes are in `PUBLIC_DATA_PROVENANCE.md`,
`evidence/model_inventory/MODEL_ARTIFACT_INVENTORY.csv`, and
`SHA256SUMS.txt`.

## SciKeras loading requirement

The MLP joblib artifacts were serialized while `train_models.py` ran as a
script, so the factory reference is `__main__.keras_mlp`.
`scripts/evaluate_omnet.py` deliberately registers the identical callable
before loading. External loaders must do the same; do not rewrite the frozen
artifacts to hide the requirement.

## Output naming and overwrite protection

Use `run-NEW`, a timestamp, or a versioned reproduction tag for every output.
Canonical scripts refuse occupied output locations at critical stages. Git
ignore rules exclude generated data/models/results. Preserve source and frozen
evidence; never “clean” an output directory by deleting it in an automated
reproduction command.

## Licensing, citation, security, and contact

Original source code is MIT licensed. Original documentation, figures, and
aggregate results are CC BY 4.0 licensed. CICDDoS2019, OMNeT++/INET,
third-party dependencies, and excluded model artifacts are not relicensed.
Read `LICENSE`, `LICENSES/`, and `THIRD_PARTY_NOTICES.md`. Cite this release
and CICDDoS2019 as described in `CITATION.cff` and
`PUBLIC_DATA_PROVENANCE.md`. Follow
`SECURITY_AND_DUAL_USE.md` and run simulations only on authorized isolated
systems.

Corresponding author: Abir Amer, `abir.amer@mubs.edu.lb`.
