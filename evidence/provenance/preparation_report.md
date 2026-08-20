# CICDDoS2019 maximum-BENIGN preparation report

- Status: prepared; independent validation required before training.
- Exact N: **108,381 records per binary class**.
- Selected total: **216,762**.
- Sampling seed: `104729`.
- BENIGN oversampling/duplication: none; every clean unique BENIGN row retained.
- DDoS selection: deterministic day/file/attack-stratified Hamilton allocation,   without replacement.

## Class accounting

| Stage | BENIGN | DDoS |
|---|---:|---:|
| raw | 113,828 | 70,313,809 |
| clean_valid | 112,731 | 68,144,156 |
| invalid_removed | 1,097 | 2,169,653 |
| exact_duplicates_removed | 4,350 | 440,457 |
| clean_unique | 108,381 | 67,703,699 |
| selected | 108,381 | 108,381 |

## Leakage validation generated for all ten seeds

Every split is source-file-grouped and class-preserving. The independent validator must confirm zero sample-ID, SHA-256 row-hash, and source-group overlap before training. Detailed file/day/attack allocation and split composition are in the machine-readable CSV/Parquet outputs listed in the provenance manifest.

Selected-row manifest SHA-256: `902c22d120dff65c5529fd0e123622a6122531d5ce5589021e987ee1b52b3575`

Split manifest SHA-256: `0ecb7978ab509151cc1f2b4e2fbabe6b2ef98450597be8f4999d82ab92d383b5`
