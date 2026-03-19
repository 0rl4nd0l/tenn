# Ops Pack Changelog

All notable changes to `docs/ops/` should be recorded in this file.

## [2026-03-11] - OpenClaw Live Endpoint Correction

Changed:
- `docs/ops/openclaw_ops_loop.md`
  - Split the checked-in llama.cpp launcher default (`8000`) from the live host override and OpenClaw provider endpoint (`8001` on this machine).
  - Updated smoke-check guidance to prefer the live host endpoint from `~/.openclaw/openclaw.json`.
- `docs/ops/08_openclaw_llamacpp_no_reply_incident_2026-03-08.md`
  - Corrected the current-profile note so it no longer describes `8000` as the live host endpoint when the override file and OpenClaw config are pinned to `8001`.

## [2026-03-11] - llama.cpp Preference Clarification

Changed:
- `docs/ops/README.md`
  - Clarified that llama.cpp is the preferred local OpenClaw/coding runtime.
  - Scoped existing Ollama guidance to backend/Cockpit paths that still require it.
- `docs/ops/openclaw_ops_loop.md`
  - Added an explicit preference note that local assistant work in Tenn should use llama.cpp over Ollama unless a subsystem still requires Ollama.
- `docs/ops/known_good_baseline_profiles.md`
  - Added a scope note explaining that the profile examples remain backend/Cockpit-oriented even though the preferred local coding runtime is now llama.cpp.

## [2026-03-09] - llama.cpp Default Server Profile Alignment

Changed:
- `docs/ops/openclaw_ops_loop.md`
  - Added the checked-in llama.cpp service/launcher source of truth.
  - Documented the new default local endpoint `http://127.0.0.1:8000/v1`.
  - Added host-override guidance for cases where another local service already occupies `8000`.
  - Clarified that Tenn now relies on default `mmap` prefetch behavior instead of `--mlock`.
- `docs/ops/08_openclaw_llamacpp_no_reply_incident_2026-03-08.md`
  - Added a current-profile note pointing operators at the new checked-in launcher and service files.
  - Updated the ongoing direct endpoint smoke check to `127.0.0.1:8000`.

## [2026-03-08] - News Pipeline Ops Docs Refresh

Changed:
- `docs/ops/known_good_baseline_profiles.md`
  - Documented current EODHD behavior: live fallback auto-enables when captures are missing and `EODHD_API_KEY` is present.
  - Added stale-run auto-heal defaults and CLI controls (`--sweep-stale-runs-hours`, `--no-sweep-stale-runs`).
- `docs/ops/system_functionality_limits.md`
  - Updated news pipeline limitation table for current EODHD fallback semantics.
  - Added stale-run sweep controls as operational risk factors.
- `docs/ops/news_sparsity_investigation.md`
  - Added 2026-03-08 status update describing applied mitigations and current network/DNS blocker.
  - Updated historical recommendations so EODHD live fallback guidance is accurate for current code.

Added:
- New stale-run cleanup command reference: `scripts/sweep_stale_news_runs.py` in ops narrative docs.

## [2026-03-08] - OpenClaw + llama.cpp NO_REPLY Incident Documentation

Added:
- `08_openclaw_llamacpp_no_reply_incident_2026-03-08.md` capturing:
  - Symptoms (`NO`/`NO_REPLY` in local/TUI sessions)
  - Root cause (full prompt mode silent-reply behavior)
  - Fixes applied (session lock cleanup, workspace prompt hardening, local runtime patch)
  - Future impact and post-update validation requirements

Changed:
- `docs/ops/README.md` updated with an Incident Notes section linking the new incident doc.

## [2026-03-04] - Financial Extraction Status + Canonical Tiering Docs Update

Changed:
- Updated extraction status and issue history in docs to reflect current BHP follow-up state.
- Documented canonical provenance tiering and promotion metadata:
  - `canonical_tier`
  - `canonical_promotion_reason`
  - `promoted_to_canonical_tier`
- Documented upstream period/cadence metadata fields:
  - `period_type`, `period_scope`, `period_length_months`, `period_inference_source`
  - `reporting_cadence`, `reporting_period_months`, `reporting_cadence_inference_source`

Issues captured in docs:
- Parent ticker contamination from subsidiary disclosures (29M/EMR Golden Grove case).
- Synthetic OCR table headers (`0 1 2` style) generating low-quality rows.
- Need to separate strict canonical statements from promoted reconciliation-table facts for reproducible panel construction.

Current guidance:
- Default downstream paneling should prioritize `primary_metric_value=true` with `canonical_tier=strict`.
- Review `table_promoted` rows as an auditable secondary tier, not as an unqualified replacement for strict rows.

## [2026-03-03] - Financial Extraction Hardening (BHP/29M follow-up)

Changed:
- `scripts/extract_financial_metrics.py` now applies cross-document deduplication for UUID-variant PDF copies (default on via `--dedupe-variant-docs` / `--no-dedupe-variant-docs`).
- Added contextual/group-based money scaling repair for under-scaled canonical rows (for example `US$2.6 bn` being parsed as `2.6`).
- Added canonical guard to demote unresolved under-scaled rows to context (`context_reason = under_scaled_amount_candidate`).

Impact:
- Prevents duplicate metric inflation when the same announcement/report exists under multiple UUID filenames.
- Reduces high-confidence false positives caused by missing table unit hints.
- Applies to future extractions across all companies by default.

## [2026-02-23] - Initial Ops v2 Pack

Added:
- `README.md` as the canonical ops index and execution order.
- `01_nvml_host_stabilization_runbook.md` for production-safe NVML recovery.
- `02_ollama_m40_validation_and_mitigation.md` for M40 GPU usage validation and mitigation.
- `03_model_tiering_m40_24gb.md` for Tier A/B/C/D routing and memory policy.
- `04_batch_pipeline_architecture_fastapi_celery.md` for queue/provenance architecture.
- `05_compose_phase1_host_gpu_blueprint.md` for host-first Ollama compose strategy.
- `05.compose.phase1.yml` additive compose blueprint.
- `05.env.template` env template for Phase-1 stack.
- `06_production_hardening_acceptance_suite.md` for rollout gates.
- `quickstart.md` incident router for operators.

Changed:
- Root `README.md` now links to the ops pack.
- `financial-engine_v2/README.md` now links to the ops pack.

Notes:
- This changelog tracks documentation and ops artifact changes only.
- Runtime code/API behavior is intentionally unchanged by this pack.
