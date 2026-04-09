#!/usr/bin/env bash
# gpu_process_guard.sh — Detect and manage rogue llama-server processes.
#
# Authorised ports (from SYSTEM_CONTRACT.md):
#   :8001 — canonical local llama.cpp/router service
#   :8002 — extraction/debug server when intentionally used
#
# Any independently spawned llama-server process on a port not in {8001, 8002}
# is rogue. Router-mode child workers on ephemeral localhost ports inherit
# authorisation from the canonical router on 8001.
set -euo pipefail

AUTHORISED_PORTS="8001 8002"
VRAM_TOTAL_MB=24576
VRAM_CRITICAL_FREE_MB=256

is_authorised_port() {
  local port="$1"
  for p in ${AUTHORISED_PORTS}; do
    [[ "${port}" == "${p}" ]] && return 0
  done
  return 1
}

extract_port() {
  local cmdline="$1"
  local port
  port=$(printf '%s' "${cmdline}" | sed -n 's/.*--port \([0-9][0-9]*\).*/\1/p' | head -1)
  printf '%s' "${port:-unknown}"
}

extract_model() {
  local cmdline="$1"
  local model
  model=$(printf '%s' "${cmdline}" | sed -n 's/.*-m \([^ ]*\).*/\1/p' | head -1)
  if [[ -z "${model}" ]]; then
    model=$(printf '%s' "${cmdline}" | sed -n 's/.*--model \([^ ]*\).*/\1/p' | head -1)
  fi
  if [[ -z "${model}" ]]; then
    if [[ "${cmdline}" == *"--models-dir"* ]]; then
      printf 'router-mode'
      return
    fi
    printf 'unknown'
    return
  fi
  printf '%s' "${model}"
}

parent_pid() {
  local pid="$1"
  awk '/^PPid:/ {print $2}' "/proc/${pid}/status" 2>/dev/null || true
}

cmdline_for_pid() {
  local pid="$1"
  local path="/proc/${pid}/cmdline"
  [[ -r "${path}" ]] || return 0
  tr '\0' ' ' < "${path}" 2>/dev/null || true
}

is_router_child_process() {
  local pid="$1"
  local current parent depth cmdline port
  current="${pid}"
  depth=0

  while [[ -n "${current}" && "${current}" != "0" && ${depth} -lt 6 ]]; do
    parent=$(parent_pid "${current}")
    [[ -n "${parent}" && "${parent}" != "0" ]] || return 1
    cmdline=$(cmdline_for_pid "${parent}")
    [[ "${cmdline}" == *"llama-server"* ]] || return 1

    port=$(extract_port "${cmdline}")
    if is_authorised_port "${port}" && [[ "${cmdline}" == *"--models-dir"* ]]; then
      return 0
    fi

    current="${parent}"
    depth=$((depth + 1))
  done

  return 1
}

gpu_memory_used_mb() {
  local line
  line=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits 2>/dev/null | head -1 || true)
  line=$(printf '%s' "${line}" | tr -cd '0-9')
  printf '%s' "${line:-0}"
}

gpu_memory_free_mb() {
  local used
  used=$(gpu_memory_used_mb)
  printf '%s' "$((VRAM_TOTAL_MB - used))"
}

process_vram_mb() {
  local pid="$1"
  local vram
  vram=$(nvidia-smi --query-compute-apps=pid,used_memory --format=csv,noheader,nounits 2>/dev/null | awk -F', ' -v pid="${pid}" '$1 == pid {print $2; exit}')
  printf '%s' "${vram:-0}"
}

survey() {
  local pids cmdline port model vram status
  pids=$(pgrep -f "llama-server" 2>/dev/null | grep -v "$$" || true)
  [[ -z "${pids}" ]] && return

  for pid in ${pids}; do
    cmdline=$(cmdline_for_pid "${pid}")
    [[ "${cmdline}" == *"llama-server"* ]] || continue

    port=$(extract_port "${cmdline}")
    model=$(extract_model "${cmdline}")
    vram=$(process_vram_mb "${pid}")

    if is_authorised_port "${port}" || is_router_child_process "${pid}"; then
      status="AUTHORISED"
    else
      status="ROGUE"
    fi

    printf '%s\t%s\t%s\t%s\t%s\n' "${pid}" "${port}" "${model}" "${vram}" "${status}"
  done
}

report() {
  local data free_mb used_mb has_rogue
  data=$(survey)
  if [[ -z "${data}" ]]; then
    printf 'No llama-server processes found.\n'
    return
  fi

  free_mb=$(gpu_memory_free_mb)
  used_mb=$(gpu_memory_used_mb)
  has_rogue=false

  printf '=== GPU Process Topology ===\n\n'
  while IFS=$'\t' read -r pid port model vram status; do
    if [[ "${status}" == "AUTHORISED" ]]; then
      printf '  [OK]    PID %-8s port=%-6s model=%-40s VRAM=%sMB\n' "${pid}" "${port}" "${model}" "${vram}"
    else
      printf '  [ROGUE] PID %-8s port=%-6s model=%-40s VRAM=%sMB\n' "${pid}" "${port}" "${model}" "${vram}"
      has_rogue=true
    fi
  done <<< "${data}"

  printf '\nVRAM: %s/%s MB used (%s MB free)\n' "${used_mb}" "${VRAM_TOTAL_MB}" "${free_mb}"
  if (( free_mb < VRAM_CRITICAL_FREE_MB )); then
    printf 'STATUS: CRITICAL\n'
  elif [[ "${has_rogue}" == "true" ]]; then
    printf 'STATUS: ROGUES DETECTED\n'
  else
    printf 'STATUS: CLEAN\n'
  fi
}

check() {
  local data free_mb
  data=$(survey)
  free_mb=$(gpu_memory_free_mb)

  if (( free_mb < VRAM_CRITICAL_FREE_MB )); then
    exit 2
  fi

  if [[ -n "${data}" ]]; then
    while IFS=$'\t' read -r pid port model vram status; do
      if [[ "${status}" == "ROGUE" ]]; then
        exit 1
      fi
    done <<< "${data}"
  fi

  exit 0
}

kill_rogues() {
  local data killed
  data=$(survey)
  killed=0
  [[ -n "${data}" ]] || {
    printf 'No llama-server processes found.\n'
    return
  }

  while IFS=$'\t' read -r pid port model vram status; do
    if [[ "${status}" == "ROGUE" ]]; then
      printf 'Killing rogue PID %s (port=%s, VRAM=%sMB)...\n' "${pid}" "${port}" "${vram}"
      kill "${pid}" 2>/dev/null || true
      killed=$((killed + 1))
    fi
  done <<< "${data}"

  if (( killed == 0 )); then
    printf 'No rogue processes found.\n'
    return
  fi

  sleep 5
  while IFS=$'\t' read -r pid port model vram status; do
    if [[ "${status}" == "ROGUE" ]] && kill -0 "${pid}" 2>/dev/null; then
      printf 'Force-killing PID %s...\n' "${pid}"
      kill -9 "${pid}" 2>/dev/null || true
    fi
  done <<< "${data}"
  printf 'Killed %s rogue process(es).\n' "${killed}"
}

json_output() {
  local data free_mb used_mb first
  data=$(survey)
  free_mb=$(gpu_memory_free_mb)
  used_mb=$(gpu_memory_used_mb)
  first=true

  printf '{\n'
  printf '  "vram_total_mb": %s,\n' "${VRAM_TOTAL_MB}"
  printf '  "vram_used_mb": %s,\n' "${used_mb}"
  printf '  "vram_free_mb": %s,\n' "${free_mb}"
  if (( free_mb < VRAM_CRITICAL_FREE_MB )); then
    printf '  "vram_critical": 1,\n'
  else
    printf '  "vram_critical": 0,\n'
  fi
  printf '  "processes": ['

  if [[ -n "${data}" ]]; then
    while IFS=$'\t' read -r pid port model vram status; do
      if [[ "${first}" == "true" ]]; then
        printf '\n'
      else
        printf ',\n'
      fi
      printf '    {"pid": %s, "port": "%s", "model": "%s", "vram_mb": %s, "status": "%s"}' "${pid}" "${port}" "${model}" "${vram:-0}" "${status}"
      first=false
    done <<< "${data}"
  fi

  printf '\n  ]\n}\n'
}

case "${1:-}" in
  --check) check ;;
  --kill-rogues) kill_rogues ;;
  --json) json_output ;;
  *) report ;;
esac
