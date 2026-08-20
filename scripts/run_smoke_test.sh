#!/usr/bin/env bash
set -euo pipefail

if [[ -d /opt/mingw64/bin ]]; then
  export PATH="/opt/mingw64/bin:${PATH}"
fi

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
cd "${PROJECT_ROOT}"

CONFIG="${1:-Normal}"
case "${CONFIG}" in
  Normal|UDPFlood|SYNFlood|DNSAmplification) ;;
  *)
    echo "Unknown configuration: ${CONFIG}" >&2
    echo "Choose: Normal, UDPFlood, SYNFlood, or DNSAmplification" >&2
    exit 2
    ;;
esac

# Use a new timestamped directory so a smoke test can never overwrite a prior
# PCAP/SCA/VEC/VCI result. An explicit second argument is also accepted but must
# name a path that does not yet exist.
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
OUTPUT_DIR="${2:-results/smoke-${CONFIG}-${STAMP}}"
if [[ -e "${OUTPUT_DIR}" ]]; then
  echo "Refusing to overwrite existing smoke-test output: ${OUTPUT_DIR}" >&2
  exit 2
fi
mkdir -p "${OUTPUT_DIR}"

PROJECT_PARENT="$(cd -- "${PROJECT_ROOT}/.." && pwd)"
DEFAULT_INET_ROOT="${PROJECT_PARENT}/samples/inet4.5"
# Ignore a stale path left in the shell by an earlier setup attempt.
if [[ -n "${INET_ROOT:-}" && ! -f "${INET_ROOT}/src/inet/package.ned" ]]; then
  echo "Ignoring stale INET_ROOT: ${INET_ROOT}" >&2
  unset INET_ROOT
fi
if [[ -z "${INET_ROOT:-}" && -f "${DEFAULT_INET_ROOT}/src/inet/package.ned" ]]; then
  INET_ROOT="${DEFAULT_INET_ROOT}"
  export INET_ROOT
fi

: "${INET_ROOT:?INET 4.5.4 was not detected at ../samples/inet4.5}"
if [[ ! -f "${INET_ROOT}/src/inet/package.ned" ]]; then
  echo "Invalid INET_ROOT: ${INET_ROOT}" >&2
  echo "Expected: ${INET_ROOT}/src/inet/package.ned" >&2
  exit 2
fi
INET_VERSION_FILE="${INET_ROOT}/Version"
if [[ ! -f "${INET_VERSION_FILE}" ]]; then
  echo "INET version file is missing: ${INET_VERSION_FILE}" >&2
  exit 2
fi
INET_VERSION="$(head -n 1 "${INET_VERSION_FILE}" | tr -d '\r')"
if [[ ! "${INET_VERSION}" =~ ^inet-4\.5\.4($|-) ]]; then
  echo "Refusing to run with ${INET_VERSION}; required INET version is 4.5.4." >&2
  exit 2
fi

# Keep paths passed to opp_run relative. This avoids both MSYS /c/... paths and
# Windows drive-letter colons (C:), which this OMNeT++ shell is splitting.
if [[ "${INET_ROOT}" == "${DEFAULT_INET_ROOT}" ]]; then
  INET_RUN_ROOT="../samples/inet4.5"
elif command -v realpath >/dev/null 2>&1; then
  INET_RUN_ROOT="$(realpath --relative-to="${PROJECT_ROOT}" "${INET_ROOT}")"
else
  echo "INET is not beside the project and realpath is unavailable." >&2
  echo "Place INET at ${DEFAULT_INET_ROOT}, or install GNU realpath." >&2
  exit 2
fi

mkdir -p results
echo "Project: ${PROJECT_ROOT}"
echo "Configuration: ${CONFIG}, run 0"
echo "Output: ${OUTPUT_DIR}"
echo "INET (verified): ${INET_ROOT}"
echo "INET version:    ${INET_VERSION}"
echo "INET (opp_run):  ${INET_RUN_ROOT}"
opp_run -u Cmdenv \
  -n "src;${INET_RUN_ROOT}/src" \
  -l "${INET_RUN_ROOT}/src/INET" \
  omnetpp.ini -c "${CONFIG}" -r 0 \
  --output-vector-file="${OUTPUT_DIR}/${CONFIG}-seed104729.vec" \
  --output-scalar-file="${OUTPUT_DIR}/${CONFIG}-seed104729.sca" \
  "--*.server.pcapRecorder[0].pcapFile=\"${OUTPUT_DIR}/${CONFIG}-seed104729-server.pcap\""
