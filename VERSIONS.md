# Exact environment versions

The reference package is pinned to:

| Component | Version |
|---|---:|
| Ubuntu | 22.04.5 LTS (recommended) |
| OMNeT++ | 6.0.3 |
| INET Framework | 4.5.4 |
| C++ compiler | GCC 11.4.0 |
| Python | 3.10.5 (`.venv-final` only) |

Python package versions are pinned in `requirements.txt`. Record the final
installed environment with:

```bash
stamp=$(date +%Y%m%dT%H%M%S)
mkdir -p results/environment
opp_run -v > "results/environment/omnet-version-${stamp}.txt"
./.venv-final/Scripts/python.exe --version > "results/environment/python-version-${stamp}.txt"
./.venv-final/Scripts/python.exe -m pip freeze > "results/environment/pip-freeze-${stamp}.txt"
head -n 1 ../samples/inet4.5/Version > "results/environment/inet-version-${stamp}.txt"
```

The timestamped relative paths prevent earlier environment evidence from being
overwritten.

Canonical reviewer-audit evidence recorded on 2026-08-19:

- `results/environment/python-version-20260819T144816.txt`: Python 3.10.5
- `results/environment/pip-freeze-20260819T144816.txt`: nonempty package snapshot

The run5 status records OMNeT++ 6.0.3 and INET
`inet-4.5.4-0a1d409733`. The canonical campaign ran through the OMNeT++ Windows
MinGW environment, but a separate timestamped snapshot of the exact Windows
host build and C++ compiler point version is not part of the retained public
evidence. Ubuntu 22.04.5 LTS and GCC 11.4.0 above are the recommended reference
reproduction environment, not a claim about the canonical Windows host.

The training script refuses to run under a Python version other than 3.10.5 and
refuses to mix artifacts when the recorded package-version manifest changes.
The exact INET revision used for the reported results is retained below; the
absence of a separate host/compiler snapshot is disclosed above as an
environment-provenance limitation.

On the packaged Windows tree, the required INET source/build is
`../samples/inet4.5` and its `Version` file is
`inet-4.5.4-0a1d409733`. The sibling `../inet` repository is INET 4.4.1 and is
explicitly rejected by the simulation launchers.
