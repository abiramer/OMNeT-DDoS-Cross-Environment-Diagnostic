# Third-party notices

This file identifies important third-party components and boundaries. It is
not a substitute for the license terms supplied by each upstream project.

## CICDDoS2019

The raw CICDDoS2019 dataset and derived row-level records are not included.
Users must obtain the dataset from the official Canadian Institute for
Cybersecurity source and comply with its applicable terms and citation
requirements. This release does not relicense CICDDoS2019. See
`PUBLIC_DATA_PROVENANCE.md` for the verified source-file inventory and
portable acquisition/path procedure.

## OMNeT++ and INET

OMNeT++ 6.0.3 and INET 4.5.4 (`inet-4.5.4-0a1d409733`) are external build and
runtime requirements. Their distributions are not bundled or relicensed.
Users must obtain and use them under their upstream licenses.

## Python and Python packages

Python and the packages listed in `requirements.txt`, `environment.yml`, and
`evidence/environment/` are third-party dependencies. They retain their own
licenses; the MIT and CC BY 4.0 grants in this release do not cover them.

## Frozen models and excluded artifacts

Frozen model payloads, row-level predictions, raw/derived dataset rows, and
OMNeT++ packet/scalar/vector outputs are excluded. Their hashes and
reproduction metadata are supplied for audit where appropriate, but this
release does not grant redistribution rights for the excluded payloads.

