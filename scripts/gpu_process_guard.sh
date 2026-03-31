#!/usr/bin/env bash
# gpu_process_guard.sh — Detect and manage rogue llama-server processes.
#
# Authorised ports (from SYSTEM_CONTRACT.md §9.4):
#   :8001 — Single llama-server in router mode (chat + extraction via model selection)
#   :8002 — Legacy extraction server (manual debugging only; deprecated)
#
# Any independently spawned llama-server process on a port not in {8001, 8002}
# is ROGUE. Router-mode child workers on ephemeral localhost ports inherit
# authorisation from the canonical router on 8001.
#
# Usage:
#   gpu_process_guard.sh              # Report topology (human-readable)
#   gpu_process_guard.sh --check      # Exit 0=clean, 1=rogues, 2=VRAM critical
#   gpu_process_guard.sh --kill-rogues # Terminate unauthorised instances
#   gpu_process_guard.sh --json       # Machine-readable JSON output
set -euo pipefail

AUTHORISED_PORTS="8001 8002"
VRAM_TOTAL_MB=24576       # Tesla M40 24GB
VRAM_CRITICAL_FREE_MB=256  # 256MB minimum (single-instance router mode, KV cache uses remaining VRAM)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_is_authorised_port() {
  local port="$1"
  for p in ${AUTHORISED_PORTS}; do
    [[ "${port}" == "${p}" ]] && return 0
  done
  return 1
}

_extract_port() {
  # Extract --port value from a cmdline string
  local cmdline="$1"
  echo "${cmdline}" | sed -n 's/.*--port \([0-9]*\).*/\1/p' | head -1
  [[ ${PIPESTATUS[0]} -eq 0 ]] || echo "unknown"
}

_extract_model() {
  # Extract -m or --model value from cmdline; router mode has no -m flag
  local cmdline="$1"
  local model
  # Try -m first, then --model
  model=$(echo "${cmdline}" | sed -n 's/.*-m \([^ ]*\).*/\1/p' | head -1)
  if [[ -z "${model}" ]]; then
    model=$(echo "${cmdline}" | sed -n 's/.*--model \([^ ]*\).*/\1/p' | head -1)
  fi
  if [[ -z "${model}" ]]; then
    if echo "${cmdline}" | grep -q -- "--models-dir"; then
      echo "router-mode"
      return
    fi
    echo "unknown"
  else
    echo "${model}"
  fi
}

_parent_pid() {
  local pid="$1"
  awk '/^PPid:/ {print $2}' "/proc/${pid}/status" 2>/dev/null || echo ""
}

_cmdline_for_pid() {
  local pid="$1"
  local path="/proc/${pid}/cmdline"
  [[ -r "${path}" ]] || return 0
  tr '\0' ' ' < "${path}" 2>/dev/null || true
}

_is_router_child_process() {
  local pid="$1"
  local current parent depth cmdline port
  current="${pid}"
  depth=0

  while [[ -n "${current}" && "${current}" != "0" && ${depth} -lt 6 ]]; do
    parent=$(_parent_pid "${current}")
    [[ -n "${parent}" && "${parent}" != "0" ]] || return 1
    cmdline=$(_cmdline_for_pid "${parent}")
    [[ "${cmdline}" == *"llama-server"* ]] || return 1

    port=$(_extract_port "${cmdline}")
    if _is_authorised_port "${port}" && echo "${cmdline}" | grep -q -- "--models-dir"; then
      return 0
    fi

    current="${parent}"
    depth=$((depth + 1))
  done

  return 1
}

_gpu_memory_used_mb() {
  # nounits should return digits only; strip defensively for set -u + arithmetic.
  local line
  line=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits 2>/dev/null | head -1 || true)
  line=$(echo "${line}" | tr -cd '0-9')
  echo "${line:-0}"
}

_gpu_memory_free_mb() {
  local used
  used=$(_gpu_memory_used_mb)
  echo $(( VRAM_TOTAL_MB - used ))
}

_process_vram_mb() {
  local pid="$1"
  local vram
  vram=$(nvidia-smi --query-compute-apps=pid,used_memory --format=csv,noheader,nounits 2>/dev/null \
    | awk -F', ' -v pid="${pid}" '$1 == pid {print $2; exit}')
  echo "${vram:-0}"
}

# ---------------------------------------------------------------------------
# Survey
# ---------------------------------------------------------------------------

survey() {
  # Returns tab-separated lines: PID\tPORT\tMODEL\tVRAM_MB\tSTATUS
  local pids
  pids=$(pgrep -f "llama-server" 2>/dev/null | grep -v "$$" || true)
  [[ -z "${pids}" ]] && return

  for pid in ${pids}; do
    # Skip non-llama-server matches (e.g., this script via pgrep)
    local cmdline
    cmdline=$(_cmdline_for_pid "${pid}")
    [[ "${cmdline}" == *"llama-server"* ]] || continue

    local port model vram status
    port=$(_extract_port "${cmdline}")
    model=$(_extract_model "${cmdline}")
    vram=$(_process_vram_mb "${pid}")

    if _is_authorised_port "${port}" || _is_router_child_process "${pid}"; then
      status="AUTHORISED"
    else
      status="ROGUE"
    fi

    printf '%s\t%s\t%s\t%s\t%s\n' "${pid}" "${port}" "${model}" "${vram}" "${status}"
  done
}

# ---------------------------------------------------------------------------
# Actions
# ---------------------------------------------------------------------------

do_report() {
  local data
  data=$(survey)

  if [[ -z "${data}" ]]; then
    echo "No llama-server processes found."
    return
  fi

  local free_mb
  free_mb=$(_gpu_memory_free_mb)
  local used_mb
  used_mb=$(_gpu_memory_used_mb)

  echo "=== GPU Process Topology ==="
  echo ""

  local has_rogue=false
  while IFS=$'\t' read -r pid port model vram status; do
    local model_short
    model_short=$(basename "${model}" 2>/dev/null || echo "${model}")
    if [[ "${status}" == "AUTHORISED" ]]; then
      printf "  [OK]    PID %-8s port=%-6s model=%-40s VRAM=%sMB\n" "${pid}" "${port}" "${model_short}" "${vram}"
    else
      printf "  [ROGUE] PID %-8s port=%-6s model=%-40s VRAM=%sMB\n" "${pid}" "${port}" "${model_short}" "${vram}"
      has_rogue=true
    fi
  done <<< "${data}"

  echo ""
  echo "VRAM: ${used_mb}/${VRAM_TOTAL_MB} MB used (${free_mb} MB free)"

  if (( free_mb < VRAM_CRITICAL_FREE_MB )); then
    echo "STATUS: CRITICAL — free VRAM below ${VRAM_CRITICAL_FREE_MB}MB threshold"
  elif [[ "${has_rogue}" == "true" ]]; then
    echo "STATUS: ROGUES DETECTED — run with --kill-rogues to clean up"
  else
    echo "STATUS: CLEAN"
  fi
}

do_check() {
  local data
  data=$(survey)
  local has_rogue=false
  local free_mb
  free_mb=$(_gpu_memory_free_mb)

  if [[ -n "${data}" ]]; then
    while IFS=$'\t' read -r pid port model vram status; do
      if [[ "${status}" == "ROGUE" ]]; then
        has_rogue=true
        break
      fi
    done <<< "${data}"
  fi

  if (( free_mb < VRAM_CRITICAL_FREE_MB )); then
    exit 2  # VRAM critical
  elif [[ "${has_rogue}" == "true" ]]; then
    exit 1  # rogues detected
  else
    exit 0  # clean
  fi
}

do_kill_rogues() {
  local data
  data=$(survey)
  local killed=0

  if [[ -z "${data}" ]]; then
    echo "No llama-server processes found."
    return
  fi

  while IFS=$'\t' read -r pid port model vram status; do
    if [[ "${status}" == "ROGUE" ]]; then
      echo "Killing rogue PID ${pid} (port=${port}, VRAM=${vram}MB)..."
      kill "${pid}" 2>/dev/null || true
      killed=$((killed + 1))
    fi
  done <<< "${data}"

  if (( killed > 0 )); then
    echo "Waiting 5s for processes to exit..."
    sleep 5
    # Force-kill any survivors
    while IFS=$'\t' read -r pid port model vram status; do
      if [[ "${status}" == "ROGUE" ]] && kill -0 "${pid}" 2>/dev/null; then
        echo "Force-killing PID ${pid}..."
        kill -9 "${pid}" 2>/dev/null || true
      fi
    done <<< "${data}"
    echo "Killed ${killed} rogue process(es)."
  else
    echo "No rogue processes found."
  fi
}

do_json() {
  local data
  data=$(survey)
  local free_mb used_mb
  free_mb=$(_gpu_memory_free_mb)
  used_mb=$(_gpu_memory_used_mb)

  echo "{"
  echo "  \"vram_total_mb\": ${VRAM_TOTAL_MB},"
  echo "  \"vram_used_mb\": ${used_mb},"
  echo "  \"vram_free_mb\": ${free_mb},"
  echo "  \"vram_critical\": $(( free_mb < VRAM_CRITICAL_FREE_MB ? 1 : 0 )),"
  echo "  \"processes\": ["

  local first=true
  if [[ -n "${data}" ]]; then
    while IFS=$'\t' read -r pid port model vram status; do
      local model_short
      model_short=$(basename "${model}" 2>/dev/null || echo "${model}")
      [[ "${first}" == "true" ]] || echo ","
      printf '    {"pid": %s, "port": "%s", "model": "%s", "vram_mb": %s, "status": "%s"}' \
        "${pid}" "${port}" "${model_short}" "${vram:-0}" "${status}"
      first=false
    done <<< "${data}"
  fi

  echo ""
  echo "  ]"
  echo "}"
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

case "${1:-}" in
  --check)      do_check ;;
  --kill-rogues) do_kill_rogues ;;
  --json)       do_json ;;
  *)            do_report ;;
esac
