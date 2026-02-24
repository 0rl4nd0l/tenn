# Ops Pack Changelog

All notable changes to `docs/ops/` should be recorded in this file.

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
