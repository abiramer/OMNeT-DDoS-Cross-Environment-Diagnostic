# Legacy `Code/` directory audit

All 460 files in the development repository's `Code/` directory were
classified individually in the private release-preparation audit. None is
copied into this public candidate.

| Classification | Files | Public disposition |
|---|---:|---|
| compatible utility | 2 | excluded: Flask/database Python contains embedded development credentials |
| demonstration | 50 | excluded: templates/static assets belong to the unsafe legacy Flask bundle |
| legacy | 5 | excluded: notebooks and ancillary files contain Colab/local-path or release-unqualified prior-run logic |
| exclude | 403 | excluded: uploaded CSV rows, prediction history, trained artifacts, and other private/legacy data |

The notebooks contain hardcoded local/Colab paths and are not evidence for
canonical run5. The Flask application is optional, was not used to generate
canonical results, depends on obsolete or release-unqualified model files and a development
database, and failed the safe clean-release gate. It has therefore not been
silently rewritten or represented as canonical.

A future Flask release must be rebuilt as a separate compatible demonstration
with safe example configuration, the canonical eight-feature validation
contract, the frozen-artifact loader, no uploaded histories or credentials,
and the controls listed in `SECURITY_AND_DUAL_USE.md`.
