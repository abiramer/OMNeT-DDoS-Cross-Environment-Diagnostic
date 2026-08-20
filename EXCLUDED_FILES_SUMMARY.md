# Excluded files and regeneration summary

Excluded material remains preserved in the private working repository. This
release audit does not modify excluded scientific evidence.

| Category | Reason for exclusion | Regeneration/retrieval | Preserved locally |
|---|---|---|---|
| CICDDoS2019 ZIP/CSV/PCAP/log sources | dataset rows and large third-party material are not needed in Git history | obtain from the official URL; verify hashes; run README Workflow 2 | yes |
| prepared/sampled CICDDoS2019 rows and preparation database | derived row-level data; redistribution rights and privacy clearance are not established for this release; multi-gigabyte | run inventory/preparation with a new `work/prepared` path | yes |
| hold-out and OMNeT++ flow predictions | row-level/sample identifiers; 5,225,664 and 1,237,440 rows | run training/evaluation after obtaining data/models | yes |
| canonical run5 PCAP/SCA/VEC/VCI | approximately 47.84 GiB; unsuitable for repository history | run the 40-simulation campaign with a new result name | yes |
| run4 and partial/failed/smoke campaigns | noncanonical INET 4.4.1 diagnostic and partial, failed, or smoke outputs; excluded from final results | do not use; reproduce only with INET 4.5.4 | yes |
| frozen model joblib and split-ID payloads | outside the approved redistribution scope; some files are large or dataset-derived | hashes/metadata are included; regenerate locally or use an authorized exact copy | yes |
| legacy Flask/Colab/feature-importance bundle | credentials, uploaded rows, local paths, obsolete models/features, and claims without release-qualified evidence | rebuild as a separate hardened compatible demonstration | yes |
| manuscripts, LaTeX package, reviewer comments/responses, rendered pages | confidential editorial material, not reproducibility payload | not applicable | yes |
| internal author checklist and working notes | internal verification/author-only actions | public evidence is represented by aggregate validation reports | yes |
| `.venv*`, caches, compiler/runtime binaries, temp files | machine-specific, redundant, or generated | recreate the pinned environment from requirements | yes |
| local logs and path-bearing manifests | may disclose private machine paths/usernames | public-safe summaries are included instead | yes |
| old release-manifest utility | hardcoded obsolete inclusion policy (including internal checklist) | use the candidate's public manifest and validator | yes |
| `.zenodo.json` | not required by this package; confirmed citation metadata is in `CITATION.cff`, while the reserved Zenodo DOI is not yet a public record | create during the author-performed Zenodo deposition only if the service workflow requires it | not applicable |
| legacy Figure 5/6 images | single-run or release-unqualified provenance | use the completed, validated figures under `figures/figure5/` and `figures/figure6/` | yes |

The publication-ready candidate contains no file larger than GitHub's ordinary 100 MB
per-file limit. Large approved assets, if any, should be published separately
with versioned archive hashes and cross-references.
