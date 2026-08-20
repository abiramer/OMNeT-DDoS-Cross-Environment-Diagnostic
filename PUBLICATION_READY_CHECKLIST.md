# Publication-ready checklist

Version: 1.0.0  
Release date: 2026-08-20  
Repository: <https://github.com/abiramer/OMNeT-DDoS-Cross-Environment-Diagnostic>  
Reserved DOI: <https://doi.org/10.5281/zenodo.22025873>

This checklist covers the local publication-freeze candidate only. No external
upload or publication has occurred.

| Gate | State | Evidence |
|---|---|---|
| Verified v1.0.0 audit candidate remains unchanged | PASS | Original `SHA256SUMS.txt` SHA-256 remains `65d6dffdbddba909e8aa313abc39844ac52797f1766aa025c174118a19f1612a`. |
| Confirmed GitHub URL, reserved DOI, version, and date | PASS | `README.md`, `CITATION.cff`. |
| MIT source-code license | PASS | `LICENSE`, `LICENSES/MIT.txt`. |
| CC BY 4.0 documentation/figure/aggregate-result license | PASS | `LICENSE`, `LICENSES/CC-BY-4.0.txt`. |
| Third-party and excluded-artifact boundaries | PASS | `THIRD_PARTY_NOTICES.md`, `EXCLUDED_FILES_SUMMARY.md`. |
| CFF author order and confirmed metadata | PASS | YAML parse and required-field validation under Python 3.10.5; author order preserved. |
| Figure 5 frozen-input provenance | PASS | `figures/figure5/`, all four classifiers and all ten frozen seeds; input hash recorded. |
| Figure 5 visual inspection | PASS | PNG and SVG inspected; no clipping or overlap in approved render. |
| Figure 6 deterministic author selection | PASS | XGBoost, feature 8, seed 104729; first predefined ordered seed, independent of performance. |
| Figure 6 artifact verification/loading | PASS | Inventory-matching SHA-256 `c7bda804520817d02357cdb3c259a531652f3e99355fac4e3b52b0bae178f122`; loaded with pinned stack. |
| Figure 6 provenance and interpretation boundary | PASS | `figures/figure6/figure6_provenance.json`, `figures/FIGURE_PROVENANCE.md`; no fidelity claim. |
| Figure 6 visual inspection | PASS | PNG and SVG inspected; no clipping or overlap in approved render. |
| Python 3.10.5 validation runtime | PASS | Isolated audit runtime reports Python 3.10.5; pinned requirements installed without altering scientific evidence. |
| Python compilation | PASS | `scripts`, `src`, and `tests` compiled successfully. |
| Complete unit-test suite | PASS | 23/23 tests passed; the expected no-libpcap warning did not affect synthetic file-based PCAP tests. |
| Configuration consistency | PASS | Python 3.10.5, INET `inet-4.5.4-0a1d409733`, 10 seeds, 8 features, and role counts validated. |
| Shell syntax | PASS | All 3 included shell scripts passed MinGW Bash `-n`. |
| OMNeT++/INET component completeness | PASS | NED-only project; no custom `.cc`/`.h` modules are present or required. NED import validation is included in the final public-release check. |
| AI pipeline component completeness | PASS | Inventory, preparation, training, evaluation, statistics, figures, and tests are present. |
| Model-payload policy | PASS | Payloads remain excluded; Figure 6 used the private frozen artifact only to create licensed aggregate figure output. |
| CICDDoS2019 redistribution policy | PASS | Raw and row-level datasets remain excluded; portable acquisition/path instructions are present. |
| Forbidden-file, credential, and private-path scan | PASS | No forbidden payload, credential, development path, virtual environment, or temporary cache remains. Public contact email addresses are not file-system paths. |
| `NaN` string audit | PASS | No result table uses `NaN` for undefined metrics. Recorded occurrences are XGBoost's frozen missing-value sentinel in model metadata and source-code handling; undefined metrics remain `not estimable`. |
| 400,000-per-class audit | PASS | No active 400,000-per-class assumption; the sole documentation mention explicitly says the obsolete constant is absent. |
| run4 audit | PASS | run4 appears only in exclusion/guard statements; no run4 scientific result is included. |
| Public-release validation against final checksums | PASS | Candidate and independently extracted provisional archive both passed with INET import checking and zero failures. |
| Manifest uniqueness and checksum verification | PASS | 218 unique paths; 217 non-self checksum entries; MinGW `sha256sum -c` returned 0. |
| Final ZIP and independent extracted-ZIP validation | PASS | Root-layout provisional archive contained and extracted 218 hash-identical files with no enclosing directory; the named final archive is rebuilt after this checklist and subjected to the same independent check. |

Overall state: **PASS** for the local publication-freeze candidate. This does
not mean an external GitHub or Zenodo publication has occurred.
