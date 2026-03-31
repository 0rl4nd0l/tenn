#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${LLM_URL:-${LLAMACPP_URL:-http://127.0.0.1:8001}}"
BASE_URL="${BASE_URL%/}"
if [[ "${BASE_URL}" == */v1 ]]; then
  BASE_URL="${BASE_URL%/v1}"
fi
MODEL_FAST="${HEALTHCHECK_FAST_MODEL:-qwen3-30b-a3b-instruct}"
EMBED_MODEL="${EMBED_MODEL:-sentence-transformers/all-MiniLM-L6-v2}"

log() { echo "[health] $*"; }

log "timestamp: $(date -Iseconds)"
log "llm url: ${BASE_URL}/v1"

log "1/5 llama.cpp models"
curl -fsS "${BASE_URL}/v1/models" >/tmp/llamacpp_models.json
rg -n '"id"' /tmp/llamacpp_models.json | head -n 10 || true

log "2/5 gpu status"
nvidia-smi --query-gpu=index,name,memory.used,memory.total,utilization.gpu --format=csv,noheader

log "3/5 llama.cpp chat smoke (${MODEL_FAST})"
curl -fsS "${BASE_URL}/v1/chat/completions" \
  -H 'Content-Type: application/json' \
  -d "{\"model\":\"${MODEL_FAST}\",\"messages\":[{\"role\":\"user\",\"content\":\"Reply exactly OK\"}],\"temperature\":0,\"max_tokens\":8}" \
  | tee /tmp/llamacpp_fast_generate.json >/dev/null
rg -n '"content"\s*:\s*"OK"' /tmp/llamacpp_fast_generate.json >/dev/null

log "4/5 sentence-transformers cpu smoke (${EMBED_MODEL})"
python -c 'from sentence_transformers import SentenceTransformer; import os; model = SentenceTransformer(os.environ["EMBED_MODEL"], device="cpu", local_files_only=True); vector = model.encode(["hello"], convert_to_numpy=True, normalize_embeddings=False)[0]; assert len(vector) > 0; print(len(vector))' >/tmp/sentence_transformers_probe.txt

log "5/5 post-run gpu usage"
nvidia-smi --query-gpu=index,name,memory.used,memory.total,utilization.gpu --format=csv,noheader

log "PASS"
