#!/usr/bin/env python3
"""Validate a clean public-release copy without executing scientific stages."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


FORBIDDEN_SUFFIXES = {
    ".pcap", ".pcapng", ".sca", ".vec", ".vci", ".joblib", ".h5", ".keras",
    ".pkl", ".pickle", ".duckdb", ".parquet", ".docx", ".doc", ".tex", ".zip",
    ".key", ".pem", ".p12", ".pyc", ".pyo",
}
FORBIDDEN_DIR_NAMES = {
    ".venv", ".venv-final", "venv", "prepared", "extracted", "models",
    "__pycache__", "uploads", "tmp", "temp",
}
REQUIRED = {
    "README.md", "CITATION.cff", "LICENSE", "LICENSES/MIT.txt",
    "LICENSES/CC-BY-4.0.txt", "THIRD_PARTY_NOTICES.md", ".gitignore",
    "VERSIONS.md", "CHANGELOG.md", "requirements.txt", "environment.yml",
    "omnetpp.ini", "PUBLIC_DATA_PROVENANCE.md", "CANONICAL_RESULTS.md",
    "PUBLIC_RELEASE_MANIFEST.csv", "PUBLIC_RELEASE_MANIFEST.md", "SHA256SUMS.txt",
    "EXCLUDED_FILES_SUMMARY.md", "COMPONENT_COMPLETENESS.md", "CODE_AUDIT.md",
    "MODEL_ARTIFACTS_NOT_REDISTRIBUTED.md", "SECURITY_AND_DUAL_USE.md",
    "PUBLICATION_READY_CHECKLIST.md", "figures/FIGURE_PROVENANCE.md",
    "figures/figure1/figure1_pipeline.jpeg",
    "figures/figure2/figure2_feature_selection.png",
    "figures/figure3/figure3_omnet_topology.jpeg",
    "figures/figure4/figure4_flask_interface.jpeg",
    "figures/figure5/figure5_roc_summary.png",
    "figures/figure5/figure5_roc_summary.svg",
    "figures/figure6/figure6_shap_summary.png",
    "figures/figure6/figure6_shap_summary.svg",
    "figures/figure6/figure6_provenance.json",
    "config/paths.example.yaml", "config/seeds.txt", "config/scenarios.yaml",
    "config/applications.yaml", "config/ip_roles.json", "config/feature_mapping.yaml",
    "src/ddosvalidation/simulations/DDoSNetwork.ned", "scripts/run_simulations.sh",
    "scripts/run_smoke_test.sh", "scripts/check_config_consistency.py",
    "scripts/extract_features.py", "scripts/prepare_cicddos2019.py",
    "scripts/train_models.py", "scripts/evaluate_omnet.py",
    "scripts/statistical_analysis.py", "scripts/build_final_tables.py",
    "scripts/generate_figure5.py", "scripts/generate_figure6.py",
    "tests/test_pipeline_contracts.py", "tests/test_roles_and_extraction.py",
    "evidence/model_inventory/MODEL_ARTIFACT_INVENTORY.csv",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def resolve_ned_imports(root: Path, inet_root: Path) -> list[str]:
    failures: list[str] = []
    inet_src = inet_root / "src"
    version_file = inet_root / "Version"
    if not version_file.is_file() or version_file.read_text(encoding="utf-8").splitlines()[0] != "inet-4.5.4-0a1d409733":
        failures.append("INET root does not report inet-4.5.4-0a1d409733")
        return failures
    imports: set[str] = set()
    for ned in (root / "src").rglob("*.ned"):
        imports.update(re.findall(r"(?m)^\s*import\s+([A-Za-z0-9_.]+)\s*;", ned.read_text(encoding="utf-8")))
    declaration = r"\b(?:simple|module|network|channel|moduleinterface|channelinterface)\s+{symbol}\b"
    for imported in sorted(imports):
        package, symbol = imported.rsplit(".", 1)
        directory = inet_src / Path(*package.split("."))
        found = False
        if directory.is_dir():
            pattern = re.compile(declaration.format(symbol=re.escape(symbol)))
            for candidate in directory.glob("*.ned"):
                if pattern.search(candidate.read_text(encoding="utf-8", errors="ignore")):
                    found = True
                    break
        if not found:
            failures.append(f"Unresolved NED import: {imported}")
    return failures


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", type=Path, default=Path("."))
    parser.add_argument("--inet-root", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    failures: list[str] = []
    if not root.is_dir():
        raise FileNotFoundError(root)

    files = sorted(path for path in root.rglob("*") if path.is_file())
    relative = {path.relative_to(root).as_posix() for path in files}
    failures.extend(f"Missing required file: {name}" for name in sorted(REQUIRED - relative))
    for path in files:
        rel = path.relative_to(root).as_posix()
        if path.suffix.lower() in FORBIDDEN_SUFFIXES:
            failures.append(f"Forbidden file type: {rel}")
        if any(part.lower() in FORBIDDEN_DIR_NAMES for part in path.relative_to(root).parts[:-1]):
            failures.append(f"Forbidden generated directory: {rel}")
        if path.stat().st_size >= 100_000_000:
            failures.append(f"File reaches GitHub 100 MB limit: {rel}")
        if path.is_symlink():
            failures.append(f"Symlink is not allowed in self-contained release: {rel}")

    text_suffixes = {".md", ".txt", ".py", ".sh", ".json", ".yaml", ".yml",
                     ".ini", ".csv", ".cff", ".html", ".css"}
    private_patterns = {
        "author development root": re.compile(r"(?i)C:[\\/]omnetpp-6\.0\.3"),
        "home directory": re.compile(r"(?i)/(?:home|Users)/[^\s\"']+"),
        "Colab mounted drive": re.compile("(?i)/content/" + "drive"),
        "author Windows user path": re.compile(r"(?i)C:[\\/]Users[\\/]abir\.amer"),
    }
    credential_patterns = {
        "password assignment": re.compile(r"(?i)password\s*=\s*[\"'][^\"']+[\"']"),
        "API key assignment": re.compile(r"(?i)api[_-]?key\s*=\s*[\"'][^\"']+[\"']"),
        "bearer token": re.compile(r"(?i)bearer\s+[A-Za-z0-9_.-]{16,}"),
    }
    for path in files:
        if path.suffix.lower() not in text_suffixes:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        rel = path.relative_to(root).as_posix()
        for label, pattern in private_patterns.items():
            if pattern.search(text):
                failures.append(f"Private path ({label}) in {rel}")
        for label, pattern in credential_patterns.items():
            if pattern.search(text):
                failures.append(f"Credential indicator ({label}) in {rel}")
        for placeholder in ["GITHUB_RELEASE_URL_" + "PEND" + "ING",
                            "ZENODO_DOI_" + "PEND" + "ING",
                            "RELEASE_DATE_" + "PEND" + "ING",
                            "LICENSE_SELECTION_" + "REQUIRED.md"]:
            if placeholder in text:
                failures.append(f"Publication placeholder ({placeholder}) in {rel}")

    citation = (root / "CITATION.cff").read_text(encoding="utf-8")
    for required_text in [
        "https://github.com/abiramer/OMNeT-DDoS-Cross-Environment-Diagnostic",
        "10.5281/zenodo.22025873", "date-released: 2026-08-20",
        "version: 1.0.0",
    ]:
        if required_text not in citation:
            failures.append(f"CITATION.cff lacks confirmed metadata: {required_text}")

    figure5 = json.loads((root / "figures/figure5/figure5_metadata.json").read_text())
    if figure5.get("seeds") != [104729, 130363, 155921, 181081, 206369,
                                231701, 257053, 282427, 307759, 333019]:
        failures.append("Figure 5 does not record all ten frozen seeds in order")
    if figure5.get("run4_excluded") is not True:
        failures.append("Figure 5 does not explicitly exclude run4")
    figure6 = json.loads((root / "figures/figure6/figure6_provenance.json").read_text())
    if figure6.get("training_seed") != 104729 or figure6.get("feature_set") != 8:
        failures.append("Figure 6 does not record feature-8 seed 104729")
    if figure6.get("artifact_sha256") != "c7bda804520817d02357cdb3c259a531652f3e99355fac4e3b52b0bae178f122":
        failures.append("Figure 6 artifact SHA-256 is not the frozen inventory value")

    ini = (root / "omnetpp.ini").read_text(encoding="utf-8")
    ini_configs = set(re.findall(r"(?m)^\[Config\s+([^\]]+)\]", ini))
    expected_configs = {"Normal", "UDPFlood", "SYNFlood", "DNSAmplification"}
    if ini_configs != expected_configs:
        failures.append(f"INI configurations differ: {sorted(ini_configs)}")
    for launcher in ["scripts/run_simulations.sh", "scripts/run_smoke_test.sh"]:
        text = (root / launcher).read_text(encoding="utf-8")
        missing = expected_configs - {name for name in expected_configs if name in text}
        if missing:
            failures.append(f"{launcher} does not reference configs: {sorted(missing)}")

    scientific_text = (root / "CANONICAL_RESULTS.md").read_text(encoding="utf-8").lower()
    if "only run5" not in scientific_text or "run4 is excluded" not in scientific_text:
        failures.append("Canonical results must explicitly include only run5 and exclude run4")
    if "half-open syn" in scientific_text and "not" not in scientific_text:
        failures.append("Unqualified half-open SYN claim in canonical results")
    if "synthes" in scientific_text and "never synthes" not in scientific_text:
        failures.append("Unqualified DNS synthesis claim in canonical results")

    if args.inet_root is not None:
        failures.extend(resolve_ned_imports(root, args.inet_root.resolve()))

    sums = root / "SHA256SUMS.txt"
    if sums.is_file():
        for line in sums.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            expected, rel = line.split("  ", 1)
            target = root / rel
            if not target.is_file():
                failures.append(f"Hash target missing: {rel}")
            elif sha256(target) != expected:
                failures.append(f"SHA-256 mismatch: {rel}")

    status = {"status": "valid" if not failures else "invalid",
              "files": len(files), "bytes": sum(path.stat().st_size for path in files),
              "failures": failures, "inet_import_check": args.inet_root is not None}
    print(json.dumps(status, indent=2))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
