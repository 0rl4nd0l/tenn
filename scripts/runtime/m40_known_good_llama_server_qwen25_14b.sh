#!/usr/bin/env bash
set -euo pipefail

# Conservative Tesla M40 recovery/smoke config for llama.cpp.
# This is a known-good minimal server path, not the final production :8001 config.
# It is intentionally small: one slot, small context, no prompt cache, fit disabled.
#
# Device-order warning:
# Manual llama.cpp testing observed:
#   Device 0: Tesla M40 24GB
#   Device 1: GT 1030
# Recheck with the installed llama.cpp --list-devices output after any hardware,
# driver, CUDA_VISIBLE_DEVICES, or motherboard-slot change. NVIDIA-SMI indices can
# differ from llama.cpp's visible CUDA device order in this environment.

LLAMA_SERVER="/home/l4nd0/.local/bin/llama-server"
MODEL="/mnt/hdd-data/home/l4nd0/tenn/models/qwen2.5-14b-instruct-q4_k_m.gguf"
HOST="127.0.0.1"
PORT="18001"

if ss -ltnp | grep -qE ":${PORT}\\b"; then
  echo "Port ${PORT} is already bound; not starting another llama-server." >&2
  ss -ltnp | grep -E ":${PORT}\\b" >&2 || true
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
