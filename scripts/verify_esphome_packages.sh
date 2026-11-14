#!/usr/bin/env bash

set -Eeuo pipefail

usage() {
  printf '%s\n' \
    "Usage: scripts/verify_esphome_packages.sh [--config-only]" \
    "" \
    "Validates every package consumer fixture, reports merged includes," \
    "checks every variant's header parity with both reference profiles, and compiles" \
    "every fixture" \
    "unless --config-only is supplied." \
    "" \
    "Logs and resolved configurations: build/package-verification/" \
    "Set ESPHOME_BIN to use an ESPHome executable other than 'esphome'." \
    "Set PYTHON to a Python 3 with PyYAML (for example ESPHome's own) if python3 lacks it."
}

compile=true
case "${1:-}" in
  "") ;;
  --config-only) compile=false ;;
  -h|--help)
    usage
    exit 0
    ;;
  *)
    usage >&2
    exit 64
    ;;
esac

if (($# > 1)); then
  usage >&2
  exit 64
fi

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd -- "${script_dir}/.." && pwd)"
esphome_bin="${ESPHOME_BIN:-esphome}"
python_bin="${PYTHON:-python3}"

if ! command -v "${esphome_bin}" >/dev/null 2>&1; then
  printf 'ERROR: ESPHome executable not found: %s\n' "${esphome_bin}" >&2
  exit 127
fi

profiles=(minimal demo diagnostic battery web-ui web-ui-diagnostic)

cd -- "${repo_root}"
log_dir="${repo_root}/build/package-verification"
mkdir -p -- "${log_dir}"
phase=setup
profile=none
active_log=none
trap 'result=$?; printf "\n[result] status=failed phase=%s profile=%s exit=%s log=%s\n" "$phase" "$profile" "$result" "$active_log" >&2; exit "$result"' ERR

# ESPHome's resolved YAML and the reference profiles both use this indentation.
# Read only esphome.includes; never mistake packages.!include for C++ headers.
headers() {
  awk '
    /^esphome:/ { in_esphome=1; next }
    in_esphome && /^[^ #]/ { exit }
    in_esphome && /^  includes:/ { in_includes=1; next }
    in_includes && /^  [^ ]/ { exit }
    in_includes && /^    - / {
      sub(/^    - /, ""); gsub(/"/, ""); print
    }
  ' "$1" | LC_ALL=C sort
}

printf 'ESPHome package verification\n'
printf '  executable=%s\n' "${esphome_bin}"
printf '  repository=%s\n' "${repo_root}"
printf '  compile=%s\n' "${compile}"

phase=generated_profile_check
active_log="${repo_root}/scripts/generate_esphome_profiles.py"
"${python_bin}" scripts/generate_esphome_profiles.py --check --esphome-bin "${esphome_bin}"

for profile in "${profiles[@]}"; do
  phase=validate
  config="examples/${profile}.yaml"
  active_log="${log_dir}/${profile}.config.yaml"
  printf '\n[validate] profile=%s config=%s\n' "${profile}" "${config}"
  # Validation failures are printed to stdout by ESPHome. Keep that evidence
  # and show it on failure instead of hiding the reason behind /dev/null.
  if "${esphome_bin}" config "${config}" >"${active_log}"; then
    :
  else
    result=$?
    cat -- "${active_log}" >&2
    printf '[result] status=failed phase=validate profile=%s exit=%s log=%s\n' \
      "${profile}" "${result}" "${active_log}" >&2
    exit "${result}"
  fi
  printf '[includes] profile=%s\n' "${profile}"
  headers "${active_log}"
  printf '[validate] profile=%s result=ok\n' "${profile}"
done

phase=header_parity
for profile in "${profiles[@]}"; do
  active_log="${log_dir}/${profile}.config.yaml"
  resolved_headers="$(headers "${active_log}")"
  for reference in ESPHome/WaveshareESP32S3PhotoPainter73e6-example.yaml \
                   ESPHome/WaveshareESP32S3PhotoPainter73e6-diag.yaml; do
    reference_headers="$(headers "${reference}")"
    if [[ -z "${reference_headers}" || "${resolved_headers}" != "${reference_headers}" ]]; then
      printf '[result] status=failed phase=header_parity profile=%s reference=%s\n' \
        "${profile}" "${reference}" >&2
      printf 'Expected reference headers:\n%s\nResolved headers:\n%s\n' \
        "${reference_headers}" "${resolved_headers}" >&2
      exit 1
    fi
  done
  printf '[includes] profile=%s reference_parity=ok\n' "${profile}"
done

if [[ "${compile}" == true ]]; then
  for profile in "${profiles[@]}"; do
    phase=compile
    config="examples/${profile}.yaml"
    active_log="${log_dir}/${profile}.compile.log"
    printf '\n[compile] profile=%s config=%s\n' "${profile}" "${config}"
    "${esphome_bin}" compile "${config}" 2>&1 | tee "${active_log}"
    printf '[compile] profile=%s result=ok\n' "${profile}"
  done
fi

printf '\n[result] status=ok profiles=%u compiled=%s\n' \
  "${#profiles[@]}" "${compile}"
