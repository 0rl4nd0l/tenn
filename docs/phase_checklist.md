# Pragmatic Phase Checklist

Use this with `STATE.md` as a lightweight replacement for full workflow orchestration.

## P0 Scope and Baseline
- [ ] Define target ticker(s), time window, and output path.
- [ ] Capture baseline `git status --short`.
- [ ] Set run timestamp: `RUN_TS="$(date +%Y%m%d_%H%M%S)"`.
- [ ] Record success criteria in `STATE.md`.

Exit gate:
- [ ] Scope, success criteria, and run id are written in `STATE.md`.

## P1 Ingest and Dataset Build
- [ ] Run ticker ingestion (`financial-engine_v2/scripts/ingest_ticker.py`).
- [ ] Run dataset rebuild (`financial-engine_v2/scripts/rebuild_ticker_dataset.py`).
- [ ] Confirm expected docs and dataset files exist.

Exit gate:
- [ ] Inputs are available and no critical ingestion errors remain.

## P2 Extraction and Hardening
- [ ] Run extraction (`scripts/extract_financial_metrics.py` and/or `financial-engine_v2/scripts/extract_doc.py`).
- [ ] Run section hardening pass (`section_capture_layer.py`) where needed.
- [ ] Save output paths in `STATE.md`.

Exit gate:
- [ ] Canonical outputs are generated and parsable.

## P3 Validation and Scoring
- [ ] Run ticker validation (`financial-engine_v2/scripts/validate_ticker.py`).
- [ ] Run relevant tests from `runbook.md` test command block.
- [ ] Run gold scoring when applicable (`scripts/score_gold_set.py`).

Exit gate:
- [ ] Validation outcomes and score summary are recorded in `STATE.md`.

## P4 Review and Regression Check
- [ ] Compare with prior known-good report/run.
- [ ] Spot-check high-risk metrics and citation/provenance fields.
- [ ] Record regressions, deltas, and confidence in `STATE.md`.

Exit gate:
- [ ] Regressions are either fixed or explicitly accepted with rationale.

## P5 Closeout and Handoff
- [ ] Update `STATE.md` decisions log and handoff section.
- [ ] List final artifacts and command history needed to reproduce.
- [ ] Define next cycle's first command and owner.

Exit gate:
- [ ] Another operator can continue from `STATE.md` without extra context.
