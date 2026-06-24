#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
MANIFEST="${AIHUB_MANIFEST:-"${ROOT_DIR}/config/aihub_datasets.tsv"}"
DATA_DIR="${AIHUB_DATA_DIR:-"${ROOT_DIR}/data/aihub"}"
TOOLS_DIR="${AIHUB_TOOLS_DIR:-"${ROOT_DIR}/tools"}"
AIHUBSHELL="${AIHUBSHELL:-"${TOOLS_DIR}/aihubshell"}"
AIHUBSHELL_URL="https://api.aihub.or.kr/api/aihubshell.do"
ENV_FILE="${AIHUB_ENV_FILE:-"${ROOT_DIR}/.env"}"

load_env_file() {
  if [[ -f "${ENV_FILE}" ]]; then
    set -a
    # shellcheck disable=SC1090
    source "${ENV_FILE}"
    set +a
  fi
}

usage() {
  cat <<'USAGE'
Usage:
  scripts/download_aihub.sh info
  scripts/download_aihub.sh install
  scripts/download_aihub.sh list-files [datasetkey]
  scripts/download_aihub.sh download [datasetkey] [filekey[,filekey...]]

Environment:
  AIHUB_API_KEY   Required for download mode.
  AIHUB_DATA_DIR  Optional output directory. Defaults to data/aihub.
USAGE
}

require_manifest() {
  if [[ ! -f "${MANIFEST}" ]]; then
    echo "Missing manifest: ${MANIFEST}" >&2
    exit 1
  fi
}

dataset_keys() {
  require_manifest
  awk 'NR > 1 && NF > 0 && $1 !~ /^#/ { print $1 }' "${MANIFEST}"
}

print_info() {
  require_manifest
  column -t -s $'\t' "${MANIFEST}"
}

install_aihubshell() {
  mkdir -p "${TOOLS_DIR}"
  echo "Downloading aihubshell to ${AIHUBSHELL}"
  curl -fL "${AIHUBSHELL_URL}" -o "${AIHUBSHELL}"
  chmod +x "${AIHUBSHELL}"
}

ensure_aihubshell() {
  if [[ ! -x "${AIHUBSHELL}" ]]; then
    install_aihubshell
  fi
}

warn_runtime_compatibility() {
  if ! grep -P "" /dev/null >/dev/null 2>&1; then
    cat >&2 <<'WARNING'
Warning: this shell's grep does not support -P.
AIHub recommends Linux/WSL for aihubshell. On macOS, use GNU grep first on PATH
or run this script from Linux/WSL if aihubshell fails.
WARNING
  fi
}

ensure_api_key() {
  AIHUB_API_KEY="${AIHUB_API_KEY:-${AIHUB_APIKEY:-}}"
  if [[ -z "${AIHUB_API_KEY:-}" ]]; then
    echo "AIHUB_API_KEY is required for downloads." >&2
    echo "Example: AIHUB_API_KEY='your-api-key' $0 download" >&2
    exit 1
  fi
}

list_files() {
  ensure_aihubshell
  warn_runtime_compatibility
  local key="${1:-}"

  if [[ -n "${key}" ]]; then
    "${AIHUBSHELL}" -mode l -datasetkey "${key}"
    return
  fi

  while IFS= read -r datasetkey; do
    echo
    echo "== Dataset ${datasetkey} =="
    "${AIHUBSHELL}" -mode l -datasetkey "${datasetkey}"
  done < <(dataset_keys)
}

download_dataset() {
  ensure_aihubshell
  warn_runtime_compatibility
  ensure_api_key
  mkdir -p "${DATA_DIR}"
  export AIHUB_APIKEY="${AIHUB_API_KEY}"

  local datasetkey="$1"
  local filekeys="${2:-}"

  echo
  echo "== Downloading dataset ${datasetkey} into ${DATA_DIR} =="
  (
    cd "${DATA_DIR}"
    if [[ -n "${filekeys}" ]]; then
      "${AIHUBSHELL}" -mode d -datasetkey "${datasetkey}" -filekey "${filekeys}"
    else
      "${AIHUBSHELL}" -mode d -datasetkey "${datasetkey}"
    fi
  )
}

download_all() {
  local requested_key="${1:-}"
  local requested_filekeys="${2:-}"

  if [[ -n "${requested_key}" ]]; then
    download_dataset "${requested_key}" "${requested_filekeys}"
    return
  fi

  while IFS= read -r datasetkey; do
    download_dataset "${datasetkey}"
  done < <(dataset_keys)
}

main() {
  load_env_file

  local command="${1:-}"
  shift || true

  case "${command}" in
    info)
      print_info
      ;;
    install)
      install_aihubshell
      ;;
    list-files)
      list_files "${1:-}"
      ;;
    download)
      download_all "${1:-}" "${2:-}"
      ;;
    -h|--help|help|"")
      usage
      ;;
    *)
      echo "Unknown command: ${command}" >&2
      usage >&2
      exit 1
      ;;
  esac
}

main "$@"
