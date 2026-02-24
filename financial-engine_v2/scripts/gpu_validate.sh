#!/usr/bin/env bash
set -euo pipefail

echo "[gpu] timestamp: $(date -Iseconds)"

echo "[gpu] nvidia-smi summary"
nvidia-smi --query-gpu=index,name,driver_version,pstate,persistence_mode,memory.used,memory.total,utilization.gpu --format=csv,noheader

echo "[gpu] ollama process on GPU"
nvidia-smi --query-compute-apps=pid,process_name,gpu_uuid,used_memory --format=csv,noheader || true

echo "[gpu] service state"
systemctl is-active ollama

echo "[gpu] recent ollama gpu lines"
journalctl -u ollama -n 120 --no-pager | rg -i "cuda|Device 0|Device 1|gpu memory|llama runner process has terminated|error" || true
