#!/usr/bin/env bash
set -euo pipefail

# Conservative Tesla M40 restore candidate for the canonical llama.cpp :8001 port.
# This is Qwen2.5 conservative mode, not APEX/Qwen3.5 restored mode and not
# router-mode model switching. It intentionally mirrors the validated :18001
# smoke config while binding to the production llama.cpp port.
#
# Validated device-order warning:
#   CUDA0 was the Tesla M40 24GB in the validated environment.
#   CUDA1 must not be used unless a fresh llama.cpp device list proves CUDA1 is
#   the M40 after hardware, driver, CUDA_VISIBLE_DEVICES, or slot changes.
#
# Do not change --parallel, --cache-ram, --fit, --ctx-size, or --n-gpu-layers
# without rerunning the minimal CLI and conservative server smoke path first.

LLAMA_SERVER="/home/l4nd0/.local/bin/llama-server"
MODEL="/mnt/hdd-data/home/l4nd0/tenn/models/qwen2.5-14b-instruct-q4_k_m.gguf"
HOST="127.0.0.1"
PORT="8001"
SMOKE_PORT="18001"

if [[ "${M40_RESTORE_8001_CONFIRMED:-0}" != "1" ]]; then
  cat >&2 <<EOF
Refusing to start ${PORT} without explicit confirmation.
Set M40_RESTORE_8001_CONFIRMED=1 only after inspecting current listeners,
stopping any independent :18001 smoke server, and accepting Qwen2.5
conservative mode on the canonical llama.cpp port.
EOF
  exit 64
fi

if [[ ! -x "${LLAMA_SERVER}" ]]; then
  echo "llama-server not executable at ${LLAMA_SERVER}" >&2
  exit 1
fi

if [[ ! -f "${MODEL}" ]]; then
  echo "Model not found at ${MODEL}" >&2
  exit 1
fi

if ss -ltnp | grep -qE ":${PORT}\\b"; then
  echo "Port ${PORT} is already bound; not starting another llama-server." >&2
  ss -ltnp | grep -E ":${PORT}\\b" >&2 || true
  exit 1
fi

if ss -ltnp | grep -qE ":${SMOKE_PORT}\\b.*llama-server"; then
  echo "Known-good smoke server is still bound on ${SMOKE_PORT}; stop it before restoring ${PORT}." >&2
  ss -ltnp | grep -E ":${SMOKE_PORT}\\b" >&2 || true
  exit 1
fi

exec "${LLAMA_SERVER}" \
  --model "${MODEL}" \
  --host "${HOST}" \
  --port "${PORT}" \
  --n-gpu-layers 8 \
  --ctx-size 512 \
  --device CUDA0 \
  --split-mode none \
  --main-gpu 0 \
  --fit off \
  --parallel 1 \
  --cache-ram 0
