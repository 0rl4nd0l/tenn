# Host Stabilization + LLM Ops v2

This folder is the production-safe operations pack for the Tesla M40 + GT1030 host.

Scope:
- Host NVML stabilization (headless, Ubuntu package path only by default)
- Ollama GPU validation and Maxwell-specific mitigation
- Model tiering for 24GB VRAM / 32GB RAM / SATA disk
- Batch-first architecture for FastAPI + Celery + Postgres + Qdrant
- Phase-1 Docker blueprint with Ollama kept on host
- Production acceptance gates before scaling

## Execution Order
1. `01_nvml_host_stabilization_runbook.md`
2. `02_ollama_m40_validation_and_mitigation.md`
3. `03_model_tiering_m40_24gb.md`
4. `04_batch_pipeline_architecture_fastapi_celery.md`
5. `05_compose_phase1_host_gpu_blueprint.md`
6. `06_production_hardening_acceptance_suite.md`

Artifacts:
- `05.compose.phase1.yml`
- `05.env.template`

## Ownership
- Primary owner: Platform/Ops (GPU + host runtime)
- Secondary owner: ML Infra (model policy + Ollama behavior)
- Consumers: Backend, Data Pipeline, Cockpit operators

## Change Control
- Keep this pack additive to existing runtime docs.
- Do not replace `financial-engine_v2/docker-compose.yml` in Phase 1.
- Update acceptance criteria before changing model tiers or queue concurrency.
