#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${OLLAMA_URL:-http://127.0.0.1:11434}"
MODEL_FAST="${HEALTHCHECK_FAST_MODEL:-llama3:latest}"
MODEL_DEEP="${HEALTHCHECK_DEEP_MODEL:-qwen2.5:32b}"

log() { echo "[health] $*"; }

log "timestamp: $(date -Iseconds)"
log "ollama url: ${BASE_URL}"

log "1/5 ollama tags"
curl -fsS "${BASE_URL}/api/tags" >/tmp/ollama_tags.json
rg -n '"name"' /tmp/ollama_tags.json | head -n 10 || true

log "2/5 gpu status"
nvidia-smi --query-gpu=index,name,memory.used,memory.total,utilization.gpu --format=csv,noheader

log "3/5 fast model smoke (${MODEL_FAST})"
curl -fsS "${BASE_URL}/api/generate" \
  -d "{\"model\":\"${MODEL_FAST}\",\"prompt\":\"Reply exactly OK\",\"stream\":false,\"options\":{\"num_ctx\":4096,\"num_predict\":8}}" \
  | tee /tmp/ollama_fast_generate.json >/dev/null
rg -n '"response"\s*:\s*"OK"' /tmp/ollama_fast_generate.json >/dev/null

log "4/5 deep model smoke (${MODEL_DEEP})"
curl -fsS "${BASE_URL}/api/generate" \
  -d "{\"model\":\"${MODEL_DEEP}\",\"prompt\":\"Reply exactly OK\",\"stream\":false,\"options\":{\"num_ctx\":8192,\"num_predict\":8}}" \
  | tee /tmp/ollama_deep_generate.json >/dev/null
rg -n '"response"\s*:\s*"OK"' /tmp/ollama_deep_generate.json >/dev/null

log "5/5 post-run gpu usage"
nvidia-smi --query-gpu=index,name,memory.used,memory.total,utilization.gpu --format=csv,noheader

log "PASS"
