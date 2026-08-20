#!/usr/bin/env bash
set -euo pipefail

# `mingwenv.cmd` normally supplies both paths. Keep non-interactive invocations
# equivalent so OMNeT++ can locate its runtime DLLs.
if [[ -d /opt/mingw64/bin ]]; then
  export PATH="/opt/mingw64/bin:${PATH}"
fi

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
cd "${PROJECT_ROOT}"

# The OMNeT++ 6.0.3 Windows bundle places the required INET 4.5.4 tree under
# samples/inet4.5. An explicitly exported valid INET_ROOT still takes
# precedence, but its version is checked before any output directory is made.
PROJECT_PARENT="$(cd -- "${PROJECT_ROOT}/.." && pwd)"
DEFAULT_INET_ROOT="${PROJECT_PARENT}/samples/inet4.5"
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

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
OUTPUT_DIR="${1:-results/full-${STAMP}}"
if [[ -e "${OUTPUT_DIR}" ]]; then
  echo "Refusing to overwrite existing experiment output: ${OUTPUT_DIR}" >&2
  exit 2
fi

# Empirical seed-0 sizes are approximately 2.8 GB for UDPFlood and 2.3 GB for
# DNSAmplification when PCAP and vector recording are both retained. Require a
# conservative full-campaign budget before starting; the threshold can be
# raised for a particular filesystem but should not be lowered casually.
REQUIRED_FREE_GB="${REQUIRED_FREE_GB:-60}"
if [[ ! "${REQUIRED_FREE_GB}" =~ ^[0-9]+$ ]]; then
  echo "REQUIRED_FREE_GB must be a nonnegative integer." >&2
  exit 2
fi
OUTPUT_PARENT="$(dirname -- "${OUTPUT_DIR}")"
mkdir -p "${OUTPUT_PARENT}"
available_kb="$(df -Pk "${OUTPUT_PARENT}" | awk 'NR == 2 {print $4}')"
required_kb="$((REQUIRED_FREE_GB * 1024 * 1024))"
if (( available_kb < required_kb )); then
  available_gb="$((available_kb / 1024 / 1024))"
  echo "Insufficient free space for the 40-run campaign." >&2
  echo "Output filesystem has about ${available_gb} GiB free; require at least ${REQUIRED_FREE_GB} GiB." >&2
  echo "Choose an output directory on a larger volume. No simulation was started." >&2
  exit 2
fi
mkdir -p "${OUTPUT_DIR}"
echo "INET (verified): ${INET_ROOT}"
echo "INET version:    ${INET_VERSION}"
echo "INET (opp_run):  ${INET_RUN_ROOT}"
echo "Output:          ${OUTPUT_DIR}"

for config in Normal UDPFlood SYNFlood DNSAmplification; do
  opp_run -u Cmdenv \
    -n "src;${INET_RUN_ROOT}/src" \
    -l "${INET_RUN_ROOT}/src/INET" \
    omnetpp.ini -c "${config}" \
    --output-vector-file="${OUTPUT_DIR}/\${configname}-seed\${seed}.vec" \
    --output-scalar-file="${OUTPUT_DIR}/\${configname}-seed\${seed}.sca" \
    "--*.server.pcapRecorder[0].pcapFile=\"${OUTPUT_DIR}/\${configname}-seed\${seed}-server.pcap\"" \
    2>&1 | tee "${OUTPUT_DIR}/${config}.log"
done
