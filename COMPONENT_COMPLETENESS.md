# Mandatory component-completeness audit

This audit describes the contents of the clean candidate release, not the
larger private working directory. `canonical` means part of the frozen run5
evidential pipeline; `compatible utility` means usable with the same contracts
but added or retained for reproduction/reporting; `documentation` does not
generate evidence.

## A. OMNeT++/INET simulation project

Status: **complete for the implemented NED/INI project, subject to an external
OMNeT++/INET installation**.

Included components:

- `src/ddosvalidation/**/*.ned`: canonical topology and package definitions;
- `omnetpp.ini`: canonical scenario and application parameters;
- `config/scenarios.yaml`, `applications.yaml`, `ip_roles.json`,
  `feature_mapping.yaml`, and `seeds.txt`;
- `scripts/run_simulations.sh`, `run_smoke_test.sh`, `extract_all.sh`,
  `extract_features.py`, and `check_config_consistency.py`;
- release README parameter table, output layout, INET integration instructions,
  and individual Normal, UDP-flood, TCP-connection-exhaustion, and
  DNS-amplification commands.

There are **zero** package-local `.cc`, `.h`, `.msg`, Makefile, makefrag,
`.project`, `.cproject`, or `.oppbuildspec` files in the source repository.
This is not an omitted custom-module build: the model uses INET's existing NED
modules and applications and is launched with `opp_run`. Consequently, custom
C++ compilation is not applicable. INET must be supplied externally as the
verified release `inet-4.5.4-0a1d409733`; its source or binaries are not copied.

Static clean-copy checks confirm that all five imported NED types are provided
by the documented INET tree, the four INI configuration names match both run
scripts, configuration validation selects INET 4.5.4, and no run4 or INET 4.4.1
path is selected. The local `opp_nedtool` executable could not be launched in
the restricted validation shell, so a full external NED resolver invocation
remains a pre-publication host check. No simulation was rerun.

The TCP implementation is a TCP connection-exhaustion/connection-flood
approximation using parallel sessions, not a raw forged half-open SYN flood.
DNS accounting counts observed IPv4 fragments and does not synthesize missing
fragments. PCAP, SCA, VEC, and VCI outputs are excluded.

## B. AI preparation, training, evaluation, and reporting

Status: **source complete; long-running stages not executed during release
assembly**.

The included canonical scripts cover raw inventory, inventory validation,
finite-value cleaning, 88-field exact-record deduplication, deterministic
Hamilton-stratified DDoS sampling without replacement, source-file-group
splits, nested 4/6/8 features, train-only preprocessing, XGBoost/RF/MLP
training, hybrid predictions, metadata, hold-out and OMNeT++ evaluation,
metrics, paired tests, exact matched McNemar tests, Holm correction, final
tables, and reviewer-output validation.

`scripts/generate_figure5.py` and `scripts/generate_figure6.py` are compatible
reporting utilities added for public completeness. Figure 5 computes per-seed
ROC curves on matched frozen predictions and reports a common-grid mean plus
sample SD across all ten seeds. Figure 6 verifies and explains the frozen
feature-8 XGBoost seed-104729 artifact selected by the author as the first seed
in the predefined ordered list, independently of performance. Both refuse
existing output directories. Their approved publication-freeze outputs and
provenance are under `figures/`.

Exact hyperparameters and feature order are retained in
`evidence/model_metadata/`; label orientation is `BENIGN=0`, `DDoS=1`.
`StandardScaler` is fitted inside each training pipeline on training rows only.
The ten seeds are in `config/seeds.txt`. Python/package versions are in
`evidence/environment/`.

The training code is CPU-compatible. XGBoost and RF use `n_jobs=-1`; XGBoost
does not request a GPU. TensorFlow may use available CPU/GPU kernels. Seeds are
set for XGBoost, RF, and Keras, but exact bitwise MLP reproducibility can still
vary with TensorFlow device, kernels, thread scheduling, and early-stopping
numerics. The frozen versions and seed-level outputs are therefore part of the
audit evidence.

Static scans found no Colab mounted-drive dependency, unpublished-notebook
dependency, author-machine absolute path, run4 input, 400,000-per-class
constant, or single-run metric constant in the included training pipeline.
All dataset and artifact roots are command-line arguments; missing inputs fail
with an explicit exception.

## C. Frozen trained-model artifacts

Status: **not distributed; redistribution is not approved by this release**.

The source contained 245 files under `models/max-benign-run5-inet454/`: 90
inference joblib pipelines, 153 verification/metadata files, and two large
row-level/metadata files subject to additional review. Every file is listed by
size, SHA-256, model family, feature set, seed, dependency, feature order,
loading command, and status in
`evidence/model_inventory/MODEL_ARTIFACT_INVENTORY.csv`.

Only small model metadata and aggregate metrics are present in this repository.
No joblib, Keras weight payload, split-ID row table, training-metadata payload,
or hold-out prediction table is included, and this package does not state that
models are included. For Figure 6, the clean-candidate utility loaded and
verified the locally retained feature-8 XGBoost seed-104729 artifact against
its inventory hash under the pinned Python 3.10.5 stack. Other excluded model
payloads are outside the release load-test scope. Independent Figure 6
regeneration requires an authorized copy of the exact hashed artifact. Any
future separately authorized model distribution should use versioned release
assets or Zenodo files, not Git history.

SciKeras artifacts reference `__main__.keras_mlp`. The compatibility factory
is intentionally present in `scripts/evaluate_omnet.py`; external loaders must
register the same callable before `joblib.load`.

## D. Flask demonstration application

Status: **excluded; safety gate failed**.

The development Flask bundle contains embedded database credentials, uploaded
user/prediction CSVs, legacy model artifacts, database contents/assumptions,
and prior-run graphics without release-qualified provenance. It is optional
and was not used to generate
canonical run5 evidence. Because it is not in the clean release, no startup or
network-service smoke test was performed.

Any future compatible interface must use the frozen feature validator and
model loader, contain no secret/default credential, restrict file type and
size, disable debug mode for nonlocal use, and add authentication, access
control, rate limiting, secure storage, and production hardening. It must be
described as a demonstration, not a simulator-fidelity validator.

## E. CICDDoS2019 acquisition and path configuration

Status: **complete without redistributing dataset rows**.

`config/paths.example.yaml` provides clearly labelled portable example values.
Every pipeline
script accepts paths via command-line arguments; readers never edit source to
set a dataset path. README examples cover Windows drive paths and Unix paths,
the exact expected directory tree and 18 input CSV filenames, acquisition,
hash verification, and user responsibility for dataset terms.

Public-safe provenance and source hashes are in `PUBLIC_DATA_PROVENANCE.md` and
`evidence/provenance/`. Raw CSV/ZIP files, prepared rows, split rows, and
prediction rows are absent. A clean-release scan checks for the author's
development root, usernames, home directories, and Colab drive paths.

## F. End-to-end public workflow

Status: **documented with gates**.

The README separates simulation, dataset preparation, AI training, frozen-model
evaluation, OMNeT++ reevaluation, statistics, Figure 5/6, optional Flask, and
end-to-end workflows. Each lists prerequisites, inputs, command, runtime class,
outputs, validation, and canonical counts. The 40-simulation campaign and
ten-seed training are prominently marked long-running and use new output names.
Frozen-model evaluation requires an authorized exact model bundle; the Flask
demonstration is a deliberate release-scope exclusion.
