#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-$ROOT_DIR/financial-engine_v2/.venv/bin/python}"
ST_DEVICE="${ST_DEVICE:-cuda}"
REQUIRE_CUDA="${REQUIRE_CUDA:-1}"
CHECK_BASELINE="${CHECK_BASELINE:-0}"
BASELINE_PATH="${BASELINE_PATH:-$ROOT_DIR/reports/baselines/canonical_eval_baseline_latest.json}"
MRR_TOLERANCE="${MRR_TOLERANCE:-0.0}"
RANK_SLACK="${RANK_SLACK:-0}"

if [ ! -x "$PYTHON_BIN" ]; then
  echo "Python not found or not executable: $PYTHON_BIN" >&2
  exit 2
fi

if [ "$ST_DEVICE" = "cuda" ] && [ "$REQUIRE_CUDA" = "1" ]; then
  if ! "$PYTHON_BIN" - <<'PY'
import sys
import torch
ok = torch.cuda.is_available() and torch.cuda.device_count() > 0
print(f"[cuda-check] available={torch.cuda.is_available()} device_count={torch.cuda.device_count()}")
sys.exit(0 if ok else 1)
PY
  then
    echo "[cuda-check] CUDA is required but no GPU is visible to PyTorch." >&2
    echo "[cuda-check] Set REQUIRE_CUDA=0 to allow CPU fallback, or fix host CUDA/NVML visibility first." >&2
    exit 3
  fi
fi

if [ "$ST_DEVICE" = "cuda" ] && [ "$REQUIRE_CUDA" != "1" ]; then
  if ! "$PYTHON_BIN" - <<'PY'
import sys
import torch
ok = torch.cuda.is_available() and torch.cuda.device_count() > 0
sys.exit(0 if ok else 1)
PY
  then
    echo "[cuda-check] CUDA not visible; switching ST_DEVICE=cpu because REQUIRE_CUDA=0."
    ST_DEVICE="cpu"
  fi
fi

run_eval() {
  local name="$1"
  shift
  echo "[run] $name"
  "$PYTHON_BIN" "$ROOT_DIR/scripts/eval_context_retrieval.py" "$@"
}

run_eval "news-eval (hash on fixture db)" \
  --eval-file "$ROOT_DIR/reports/news_eval_queries.json" \
  --embed-backend hash \
  --out-json "$ROOT_DIR/reports/news_eval_report.json"

run_eval "company-eval (bge on company db)" \
  --eval-file "$ROOT_DIR/reports/company_eval_queries.json" \
  --embed-backend sentence-transformers \
  --embed-model BAAI/bge-large-en-v1.5 \
  --st-device "$ST_DEVICE" \
  --out-json "$ROOT_DIR/reports/company_eval_report_v2.json"

run_eval "reference-eval (hash on reference db)" \
  --eval-file "$ROOT_DIR/reports/eval_queries.json" \
  --embed-backend hash \
  --out-json "$ROOT_DIR/reports/eval_queries_report.json"

if [ "$CHECK_BASELINE" = "1" ]; then
  echo "[run] canonical-regression-gate"
  "$PYTHON_BIN" "$ROOT_DIR/scripts/check_canonical_regression.py" \
    --baseline "$BASELINE_PATH" \
    --news-report "$ROOT_DIR/reports/news_eval_report.json" \
    --company-report "$ROOT_DIR/reports/company_eval_report_v2.json" \
    --reference-report "$ROOT_DIR/reports/eval_queries_report.json" \
    --mrr-tolerance "$MRR_TOLERANCE" \
    --rank-slack "$RANK_SLACK"
fi

echo "[ok] Canonical dataset checks completed"
