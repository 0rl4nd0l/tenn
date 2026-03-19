#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

PDF_DIR="${PDF_DIR:-$ROOT_DIR/reports/review_input_source_gated_v2_canonical}"
REVIEW_DIR="${REVIEW_DIR:-$ROOT_DIR/reports/pdf_metric_review_source_gated_v2_canonical}"
RUN_ROOT="${RUN_ROOT:-$ROOT_DIR/reports/prod_hardening_runs}"
EXTRACTOR_A="${EXTRACTOR_A:-pdftotext}"
EXTRACTOR_B="${EXTRACTOR_B:-}"
MAX_SAMPLES="${MAX_SAMPLES:-200}"
DPI="${DPI:-200}"
REVIEW_SCOPE="${REVIEW_SCOPE:-canonical}"
REVIEW_INCLUDE_METRICS="${REVIEW_INCLUDE_METRICS:-}"
REVIEW_EXCLUDE_METRICS="${REVIEW_EXCLUDE_METRICS:-}"
BALANCE_BY_METRIC="${BALANCE_BY_METRIC:-0}"
MAX_PER_METRIC="${MAX_PER_METRIC:-0}"
RISK_PROFILE="${RISK_PROFILE:-institutional}"
STRICT_INTEGRITY="${STRICT_INTEGRITY:-0}"

RUN_TS="$(date +%Y%m%d_%H%M%S)"

echo "[info] running quality cycle(s) with extractors:"
echo "  EXTRACTOR_A=${EXTRACTOR_A}"
if [[ -n "$EXTRACTOR_B" ]]; then
  echo "  EXTRACTOR_B=${EXTRACTOR_B}"
fi

for EXTRACTOR in "$EXTRACTOR_A" ${EXTRACTOR_B:+$EXTRACTOR_B}; do
  if [[ -z "$EXTRACTOR" ]]; then
    continue
  fi

  RUN_DIR="$RUN_ROOT/run_${EXTRACTOR}_${RUN_TS}"
  mkdir -p "$RUN_DIR"

  echo "[step][$EXTRACTOR] extract canonical/context rows"
  python3 "$ROOT_DIR/scripts/extract_financial_metrics.py" \
    --pdf-dir "$PDF_DIR" \
    --out-csv "$RUN_DIR/canonical.csv" \
    --out-json "$RUN_DIR/canonical.json" \
    --out-context-csv "$RUN_DIR/context.csv" \
    --out-context-json "$RUN_DIR/context.json" \
    --out-rejected-json "$RUN_DIR/rejected.json" \
    --out-blocks-json "$RUN_DIR/blocks.json" \
    --out-high-csv "$RUN_DIR/high.csv" \
    --out-high-json "$RUN_DIR/high.json" \
    --out-sqlite "$RUN_DIR/metrics.sqlite" \
    --extractor "$EXTRACTOR"

  echo "[step][$EXTRACTOR] quality audit"
  python3 "$ROOT_DIR/scripts/audit_financial_metric_quality.py" \
    --canonical-json "$RUN_DIR/canonical.json" \
    --out-json "$RUN_DIR/quality_audit.json"

  echo "[step][$EXTRACTOR] derive metrics"
  derive_cmd=(
    python3 "$ROOT_DIR/scripts/derived_metrics.py"
    --canonical-json "$RUN_DIR/canonical.json"
    --out-json "$RUN_DIR/derived_metrics.json"
    --out-csv "$RUN_DIR/derived_metrics.csv"
    --out-sqlite "$RUN_DIR/metrics.sqlite"
    --integrity-sqlite "$RUN_DIR/metrics.sqlite"
  )
  if [[ "$STRICT_INTEGRITY" == "1" ]]; then
    derive_cmd+=(--strict-integrity)
  fi
  "${derive_cmd[@]}"

  echo "[step][$EXTRACTOR] risk signals"
  risk_cmd=(
    python3 "$ROOT_DIR/scripts/risk_signals.py"
    --sqlite "$RUN_DIR/metrics.sqlite"
    --out-json "$RUN_DIR/risk_signals.json"
    --out-csv "$RUN_DIR/risk_signals.csv"
    --risk-profile "$RISK_PROFILE"
  )
  if [[ "$STRICT_INTEGRITY" == "1" ]]; then
    risk_cmd+=(--strict-integrity)
  fi
  "${risk_cmd[@]}"

  echo "[step][$EXTRACTOR] coverage report"
  python3 "$ROOT_DIR/scripts/metric_coverage_report.py" \
    --canonical-json "$RUN_DIR/canonical.json" \
    --sqlite "$RUN_DIR/metrics.sqlite" \
    --out-json "$RUN_DIR/coverage.json" \
    --out-csv "$RUN_DIR/coverage.csv" \
    --out-period-csv "$RUN_DIR/coverage_periods.csv"

  echo "[step][$EXTRACTOR] source_mode summary"
  python3 "$ROOT_DIR/scripts/report_financial_metrics_source_modes.py" \
    --canonical-json "$RUN_DIR/canonical.json" \
    --out-json "$RUN_DIR/source_mode_report.json"

  echo
  echo "[ok] quality cycle complete for extractor=$EXTRACTOR"
  echo "run_dir: $RUN_DIR"
done

echo
echo "manifest: $REVIEW_DIR/manifest.json"
echo "review:   cd $ROOT_DIR && REVIEW_SCOPE=$REVIEW_SCOPE ./scripts/run_review_with_retrain.sh"
