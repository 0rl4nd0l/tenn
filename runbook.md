# Financial Extraction Hardening Runbook

## Lightweight Phase Flow

Before running commands, update `STATE.md` and use `docs/phase_checklist.md` for phase gates.
Keep `STATE.md` current as you execute each phase so handoffs remain reproducible.

## Environment

Use project venv python:

```bash
/workspace/financial-engine_v2/.venv/bin/python --version
```

Optional OCR dependency:

```bash
sudo apt update && sudo apt install -y tesseract-ocr tesseract-ocr-eng poppler-utils
```

## Core Commands

### 1) Ingest ticker

```bash
/workspace/financial-engine_v2/.venv/bin/python financial-engine_v2/scripts/ingest_ticker.py \
  --ticker BHP \
  --years 5 \
  --process-documents
```

### 2) Extract one document

```bash
/workspace/financial-engine_v2/.venv/bin/python financial-engine_v2/scripts/extract_doc.py \
  --document-id <doc_uuid>
```

### 3) Rebuild ticker dataset

```bash
/workspace/financial-engine_v2/.venv/bin/python financial-engine_v2/scripts/rebuild_ticker_dataset.py \
  --ticker BHP
```

### 4) Section capture hardening run

```bash
/workspace/financial-engine_v2/.venv/bin/python section_capture_layer.py \
  --pdf-dir financial-engine_v2/data/asx/docs/BHP/financial_performance \
  --canonical reports/stress_reference_BHP/run_20260224_175451_stage2_fix4_dedupe/canonical.csv \
  --out-dir reports/stress_reference_BHP/run_$(date +%Y%m%d_%H%M%S)_hardening \
  --force-section-pass \
  --audit-cashflow-pre-scope 1
```

### 5) Validate ticker + optional gold score

```bash
/workspace/financial-engine_v2/.venv/bin/python financial-engine_v2/scripts/validate_ticker.py \
  --ticker BHP \
  --with-gold gold/BHP
```

## Gold Harness

### Bootstrap templates

```bash
/workspace/financial-engine_v2/.venv/bin/python scripts/bootstrap_gold_templates.py \
  --canonical-csv reports/stress_reference_BHP/run_20260225_210900_codex_patch2/canonical_section_capture.csv \
  --out-dir gold \
  --tickers BHP,CBA,RIO \
  --docs-per-ticker 12
```

### Score run

```bash
/workspace/financial-engine_v2/.venv/bin/python scripts/score_gold_set.py \
  --gold-dir gold \
  --canonical-csv reports/stress_reference_BHP/run_20260225_210900_codex_patch2/canonical_section_capture.csv \
  --out-dir reports/score_runs/run_$(date +%Y%m%d_%H%M%S)
```

### Lint gold labels

```bash
/workspace/financial-engine_v2/.venv/bin/python scripts/gold_lint.py \
  --gold-dir gold
```

## Cross-Ticker Command Matrix

Set a run timestamp once:

```bash
RUN_TS="$(date +%Y%m%d_%H%M%S)"
```

### Baseline extraction (strict table-first)

```bash
/workspace/financial-engine_v2/.venv/bin/python scripts/extract_financial_metrics.py \
  --pdf-dir /workspace/financial-engine_v2/data/asx/docs/CBA/financial_performance \
  --out-csv /workspace/reports/stress_reference_CBA/run_${RUN_TS}_CBA_baseline/canonical_baseline.csv \
  --out-json /workspace/reports/stress_reference_CBA/run_${RUN_TS}_CBA_baseline/canonical_baseline.json
```

```bash
/workspace/financial-engine_v2/.venv/bin/python scripts/extract_financial_metrics.py \
  --pdf-dir /workspace/financial-engine_v2/data/asx/docs/RIO/financial_performance \
  --out-csv /workspace/reports/stress_reference_RIO/run_${RUN_TS}_RIO_baseline/canonical_baseline.csv \
  --out-json /workspace/reports/stress_reference_RIO/run_${RUN_TS}_RIO_baseline/canonical_baseline.json
```

### Hardened section capture

```bash
/workspace/financial-engine_v2/.venv/bin/python /workspace/section_capture_layer.py \
  --pdf-dir /workspace/financial-engine_v2/data/asx/docs/CBA/financial_performance \
  --canonical /workspace/reports/stress_reference_CBA/run_${RUN_TS}_CBA_baseline/canonical_baseline.csv \
  --out-dir /workspace/reports/stress_reference_CBA/run_${RUN_TS}_CBA_hardening \
  --force-section-pass \
  --audit-cashflow-pre-scope 1
```

```bash
/workspace/financial-engine_v2/.venv/bin/python /workspace/section_capture_layer.py \
  --pdf-dir /workspace/financial-engine_v2/data/asx/docs/RIO/financial_performance \
  --canonical /workspace/reports/stress_reference_RIO/run_${RUN_TS}_RIO_baseline/canonical_baseline.csv \
  --out-dir /workspace/reports/stress_reference_RIO/run_${RUN_TS}_RIO_hardening \
  --force-section-pass \
  --audit-cashflow-pre-scope 1
```

### Bootstrap and score gold by ticker

```bash
/workspace/financial-engine_v2/.venv/bin/python scripts/bootstrap_gold_templates.py \
  --canonical-csv /workspace/reports/stress_reference_BHP/run_20260225_231600_hardening_phase4/canonical_section_capture.csv \
  --out-dir /workspace/gold \
  --tickers BHP \
  --docs-per-ticker 12
```

```bash
/workspace/financial-engine_v2/.venv/bin/python scripts/bootstrap_gold_templates.py \
  --canonical-csv /workspace/reports/stress_reference_CBA/run_${RUN_TS}_CBA_hardening/canonical_section_capture.csv \
  --out-dir /workspace/gold \
  --tickers CBA \
  --docs-per-ticker 12
```

```bash
/workspace/financial-engine_v2/.venv/bin/python scripts/bootstrap_gold_templates.py \
  --canonical-csv /workspace/reports/stress_reference_RIO/run_${RUN_TS}_RIO_hardening/canonical_section_capture.csv \
  --out-dir /workspace/gold \
  --tickers RIO \
  --docs-per-ticker 12
```

```bash
/workspace/financial-engine_v2/.venv/bin/python scripts/score_gold_set.py \
  --gold-dir /workspace/gold/BHP \
  --canonical-csv /workspace/reports/stress_reference_BHP/run_20260225_231600_hardening_phase4/canonical_section_capture.csv \
  --out-dir /workspace/reports/score_runs/run_${RUN_TS}_BHP
```

```bash
/workspace/financial-engine_v2/.venv/bin/python scripts/score_gold_set.py \
  --gold-dir /workspace/gold/CBA \
  --canonical-csv /workspace/reports/stress_reference_CBA/run_${RUN_TS}_CBA_hardening/canonical_section_capture.csv \
  --out-dir /workspace/reports/score_runs/run_${RUN_TS}_CBA
```

```bash
/workspace/financial-engine_v2/.venv/bin/python scripts/score_gold_set.py \
  --gold-dir /workspace/gold/RIO \
  --canonical-csv /workspace/reports/stress_reference_RIO/run_${RUN_TS}_RIO_hardening/canonical_section_capture.csv \
  --out-dir /workspace/reports/score_runs/run_${RUN_TS}_RIO
```

### Aggregate cross-ticker scorecards

```bash
/workspace/financial-engine_v2/.venv/bin/python scripts/score_gold_run_matrix.py \
  --scorecard /workspace/reports/score_runs/run_${RUN_TS}_BHP/scorecard.json \
  --scorecard /workspace/reports/score_runs/run_${RUN_TS}_CBA/scorecard.json \
  --scorecard /workspace/reports/score_runs/run_${RUN_TS}_RIO/scorecard.json \
  --out-dir /workspace/reports/score_runs/run_${RUN_TS}_asx_hardening_phase2
```

### OCR A/B safety check (report-first)

Run one subset with default OCR behavior and one with OCR forcibly skipped by setting `SECTION_CAPTURE_DISABLE_OCR=1`:

```bash
SECTION_CAPTURE_DISABLE_OCR=1 /workspace/financial-engine_v2/.venv/bin/python /workspace/section_capture_layer.py \
  --pdf-dir /workspace/financial-engine_v2/data/asx/docs/CBA/financial_performance \
  --canonical /workspace/reports/stress_reference_CBA/run_${RUN_TS}_CBA_baseline/canonical_baseline.csv \
  --out-dir /workspace/reports/stress_reference_CBA/run_${RUN_TS}_CBA_hardening_noocr \
  --force-section-pass \
  --audit-cashflow-pre-scope 1
```

```bash
/workspace/financial-engine_v2/.venv/bin/python /workspace/section_capture_layer.py \
  --pdf-dir /workspace/financial-engine_v2/data/asx/docs/CBA/financial_performance \
  --canonical /workspace/reports/stress_reference_CBA/run_${RUN_TS}_CBA_baseline/canonical_baseline.csv \
  --out-dir /workspace/reports/stress_reference_CBA/run_${RUN_TS}_CBA_hardening_ocr \
  --force-section-pass \
  --audit-cashflow-pre-scope 1
```

## Test Commands

```bash
/workspace/financial-engine_v2/.venv/bin/python scripts/test_provenance_contract.py
/workspace/financial-engine_v2/.venv/bin/python scripts/test_extract_pass_orchestrator.py
/workspace/financial-engine_v2/.venv/bin/python scripts/test_ocr_last_resort.py
/workspace/financial-engine_v2/.venv/bin/python scripts/test_validation_gates.py
/workspace/financial-engine_v2/.venv/bin/python scripts/test_score_gold_set.py
/workspace/financial-engine_v2/.venv/bin/python scripts/test_score_gold_run_matrix.py
/workspace/financial-engine_v2/.venv/bin/python scripts/test_gold_lint.py
/workspace/financial-engine_v2/.venv/bin/python scripts/test_bootstrap_gold_templates.py
/workspace/financial-engine_v2/.venv/bin/python scripts/test_section_capture_layer.py
```
