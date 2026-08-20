# Publication-ready checklist

Version: 1.0.0  
Release date: 2026-08-20  
Repository: <https://github.com/abiramer/OMNeT-DDoS-Cross-Environment-Diagnostic>  
Reserved DOI: <https://doi.org/10.5281/zenodo.22025873>

This checklist covers the publication-ready local candidate. Its source has
been pushed to the private GitHub repository, but no GitHub release or public
Zenodo record has been published. The DOI is reserved and is not publicly
active through Zenodo until the author performs deposition.

## Mandatory local gates

| Gate | State | Evidence |
|---|---|---|
| Verified v1.0.0 audit candidate remains unchanged | PASS | Original `SHA256SUMS.txt` SHA-256 remains `65d6dffdbddba909e8aa313abc39844ac52797f1766aa025c174118a19f1612a`. |
| Confirmed GitHub URL, reserved DOI, version, and date | PASS | `README.md`, `CITATION.cff`; release-state language distinguishes the reserved DOI from a public Zenodo record. |
| MIT source-code license | PASS | `LICENSE`, `LICENSES/MIT.txt`. |
| CC BY 4.0 documentation/figure/aggregate-result license | PASS | `LICENSE`, `LICENSES/CC-BY-4.0.txt`. |
| Third-party boundaries | PASS | `THIRD_PARTY_NOTICES.md`, `EXCLUDED_FILES_SUMMARY.md`. |
| CFF author order and confirmed metadata | PASS | YAML parse and required-field validation under Python 3.10.5; six-author order matches the verified audit candidate. |
| Figure 5 frozen-input provenance and visual inspection | PASS | `figures/figure5/`; all four classifiers and all ten frozen seeds; input hash recorded; approved PNG/SVG show no clipping or overlap. |
| Figure 6 deterministic selection, artifact verification, and loading | PASS | XGBoost feature 8 seed 104729; inventory-matching SHA-256 `c7bda804520817d02357cdb3c259a531652f3e99355fac4e3b52b0bae178f122`; loaded with the pinned stack. |
| Figure 6 provenance, interpretation boundary, and visual inspection | PASS | `figures/figure6/figure6_provenance.json`, `figures/FIGURE_PROVENANCE.md`; approved PNG/SVG; no simulator-fidelity claim. |
| Python 3.10.5 validation runtime | PASS | Isolated audit runtime reports Python 3.10.5; pinned requirements installed without changing scientific evidence. |
| Python compilation | PASS | `scripts`, `src`, and `tests` compiled successfully. |
| Complete unit-test suite | PASS | 23/23 tests passed; the expected no-libpcap warning did not affect synthetic file-based PCAP tests. |
| Configuration consistency | PASS | Python 3.10.5, INET `inet-4.5.4-0a1d409733`, 10 seeds, 8 features, and role counts validated. |
| Shell syntax | PASS | All 3 included shell scripts passed MinGW Bash `-n`. |
| OMNeT++/INET component completeness and NED imports | PASS | NED-only project; no custom `.cc`/`.h` module is required; public validation resolves imports against verified INET 4.5.4. |
| AI pipeline component completeness | PASS | Inventory, preparation, training, evaluation, statistics, figures, and tests are present. |
| Forbidden-file, credential, private-path, and release-metadata token scans | PASS | No forbidden payload, credential, development path, virtual environment, cache artifact, or unset publication-metadata token is included. Public contact email addresses are not file-system paths. |
| Unfinished-language audit | PASS | `validation_artifacts/publication_language_audit_20260820/`; every residual match is classified as a limitation, prerequisite, historical statement, example, or executable/scientific terminology; Category A/B residual count is zero. |
| `NaN` string audit | PASS | No result table uses `NaN` for undefined metrics. Recorded occurrences are XGBoost's frozen missing-value sentinel in metadata and explicit source-code handling; published undefined metrics remain `not estimable`. |
| Obsolete 400,000-per-class audit | PASS | No active 400,000-per-class assumption; the documentation mention explicitly identifies that constant as obsolete. |
| run4 exclusion audit | PASS | run4 appears only in historical/exclusion/guard statements; no run4 scientific result is included. |
| Manifest uniqueness and checksum verification | PASS | 218 unique paths; 217 non-self checksum entries; checksum verification returns zero. |
| Final ZIP and independent extracted-ZIP validation | PASS | Root-layout archive contains and extracts 218 hash-identical files with unique paths, no enclosing directory, and clean checksum/forbidden-file/credential scans. |

Overall state: **PASS** for all mandatory local publication gates.

## Finalized limitations and release-scope exclusions

- Raw and derived row-level CICDDoS2019 data are not redistributed. Users must
  acquire the official dataset under its applicable terms and run the portable
  preparation workflow.
- Frozen model payloads and split-ID payloads are not redistributed. Figure 6
  was generated and validated from the locally retained exact feature-8
  XGBoost seed-104729 artifact. Independent regeneration requires an authorized
  copy with the recorded SHA-256; the utility does not substitute another
  model.
- The Flask demonstration is outside release scope and was not used for
  canonical run5 results.
- The canonical campaign used the OMNeT++ Windows MinGW environment. A separate
  timestamped exact Windows host/compiler snapshot is not among public evidence;
  the documented Ubuntu/GCC combination is a recommended reproduction
  reference, not a claim about the canonical host.
- The package is a cross-environment diagnostic and does not establish
  simulator realism or fidelity.
- Publishing a GitHub release and activating the reserved DOI through Zenodo
  are author-performed deployment steps. They do not change the frozen
  scientific evidence or the PASS state of the mandatory local gates.
