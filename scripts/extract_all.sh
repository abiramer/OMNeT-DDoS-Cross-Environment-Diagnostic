#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
cd "${PROJECT_ROOT}"

INPUT_DIR="${1:-results}"
OUTPUT_DIR="${2:-extracted/labeled8}"
PYTHON_BIN="${PYTHON_BIN:-${PROJECT_ROOT}/.venv-final/Scripts/python.exe}"
if [[ ! -x "${PYTHON_BIN}" ]]; then
  echo "Required extraction interpreter is not executable: ${PYTHON_BIN}" >&2
  echo "Set PYTHON_BIN explicitly; do not fall back to another environment." >&2
  exit 2
fi
mkdir -p "${OUTPUT_DIR}"
shopt -s nullglob
shopt -s globstar
pcaps=("${INPUT_DIR}"/**/*-server.pcap)
if (( ${#pcaps[@]} == 0 )); then
  echo "No server PCAPs found under ${INPUT_DIR}." >&2
  exit 2
fi
outputs=()
skipped_incomplete=0
for pcap in "${pcaps[@]}"; do
  scalar="${pcap%-server.pcap}.sca"
  if [[ ! -f "${scalar}" ]]; then
    echo "Skipping incomplete capture without companion SCA: ${pcap}" >&2
    skipped_incomplete=$((skipped_incomplete + 1))
    continue
  fi
  name="$(basename "${pcap}" -server.pcap)"
  scenario="${name%%-seed*}"
  seed="${name##*-seed}"
  output="${OUTPUT_DIR}/${name}.csv"
  if [[ -e "${output}" ]]; then
    echo "Refusing to overwrite existing extracted CSV: ${output}" >&2
    exit 2
  fi
  "${PYTHON_BIN}" scripts/extract_features.py \
    --pcap "${pcap}" \
    --output "${output}" \
    --scenario "${scenario}" \
    --run "seed${seed}"
  outputs+=("${output}")
done
if (( ${#outputs[@]} == 0 )); then
  echo "No completed server PCAPs were eligible for extraction." >&2
  exit 2
fi
"${PYTHON_BIN}" scripts/validate_features.py --input "${outputs[@]}" \
  --summary "${OUTPUT_DIR}/validation-summary.json"
echo "Skipped incomplete captures: ${skipped_incomplete}"
