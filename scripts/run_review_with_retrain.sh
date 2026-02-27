#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

PDF_DIR="${PDF_DIR:-$ROOT_DIR/reports/review_input_source_gated_v2_canonical}"
REVIEW_DIR="${REVIEW_DIR:-$ROOT_DIR/reports/pdf_metric_review_source_gated_v2_canonical}"
MAX_SAMPLES="${MAX_SAMPLES:-200}"
DPI="${DPI:-200}"
IMAGE_WIDTH="${IMAGE_WIDTH:-110}"
INTERVAL_SEC="${INTERVAL_SEC:-15}"
RESET_LABELS="${RESET_LABELS:-0}"
REVIEW_SCOPE="${REVIEW_SCOPE:-canonical}"
REVIEW_INCLUDE_METRICS="${REVIEW_INCLUDE_METRICS:-}"
REVIEW_EXCLUDE_METRICS="${REVIEW_EXCLUDE_METRICS:-}"
BALANCE_BY_METRIC="${BALANCE_BY_METRIC:-0}"
MAX_PER_METRIC="${MAX_PER_METRIC:-0}"

MANIFEST_PATH="$REVIEW_DIR/manifest.json"
LABELS_PATH="$REVIEW_DIR/labels.jsonl"
RUN_DIR="$ROOT_DIR/reports/review_live_$(date +%Y%m%d_%H%M%S)"
RETRAIN_PID=""

cleanup() {
  if [[ -n "$RETRAIN_PID" ]] && kill -0 "$RETRAIN_PID" 2>/dev/null; then
    echo "[cleanup] stopping retrain loop pid=$RETRAIN_PID"
    kill "$RETRAIN_PID" 2>/dev/null || true
    wait "$RETRAIN_PID" 2>/dev/null || true
  fi
}

trap cleanup EXIT INT TERM

mkdir -p "$RUN_DIR" "$REVIEW_DIR"

if [[ "$RESET_LABELS" == "1" ]]; then
  rm -f "$LABELS_PATH"
fi

build_cmd=(
  python3 "$ROOT_DIR/scripts/build_pdf_metric_review_set.py"
  --pdf-dir "$PDF_DIR"
  --out-dir "$REVIEW_DIR"
  --max-samples "$MAX_SAMPLES"
  --dpi "$DPI"
  --review-scope "$REVIEW_SCOPE"
)
if [[ -n "$REVIEW_INCLUDE_METRICS" ]]; then
  build_cmd+=(--include-metrics "$REVIEW_INCLUDE_METRICS")
fi
if [[ -n "$REVIEW_EXCLUDE_METRICS" ]]; then
  build_cmd+=(--exclude-metrics "$REVIEW_EXCLUDE_METRICS")
fi
if [[ "$BALANCE_BY_METRIC" == "1" ]]; then
  build_cmd+=(--balance-by-metric)
fi
if [[ "$MAX_PER_METRIC" != "0" ]]; then
  build_cmd+=(--max-per-metric "$MAX_PER_METRIC")
fi
"${build_cmd[@]}"

python3 "$ROOT_DIR/scripts/auto_retrain_eval_loop.py" \
  --labels "$LABELS_PATH" \
  --passes 0 \
  --interval-sec "$INTERVAL_SEC" \
  </dev/null >"$RUN_DIR/retrain.log" 2>&1 &
RETRAIN_PID="$!"
echo "[start] retrain pid=$RETRAIN_PID log=$RUN_DIR/retrain.log"

python3 "$ROOT_DIR/scripts/review_pdf_metric_terminal.py" \
  --manifest "$MANIFEST_PATH" \
  --labels-out "$LABELS_PATH" \
  --only-unlabeled \
  --show-image \
  --image-width "$IMAGE_WIDTH"
