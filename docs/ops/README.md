# Host Stabilization + LLM Ops v2

This folder is the production-safe operations pack for the Tesla M40 + GT1030 host.

Scope:
- Preferred local agent/runtime path: llama.cpp via OpenClaw and the checked-in Tenn launcher.
- Host NVML stabilization (headless, Ubuntu package path only by default)
- Optional Ollama GPU validation and Maxwell-specific mitigation for backend/legacy workloads that still depend on it
- Model tiering for 24GB VRAM / 32GB RAM / SATA disk
- Batch-first architecture for FastAPI + Celery + Postgres + Qdrant
- Phase-1 Docker blueprint keeping Ollama on host as a legacy compatibility path while llama.cpp stays local
- Production acceptance gates before scaling

Scope note:
- Ollama guidance in this pack applies to the financial-engine backend, Cockpit, and other subsystems that still depend on it.
- It does not override the current local preference for llama.cpp in OpenClaw/coding workflows.

## Execution Order
1. `01_nvml_host_stabilization_runbook.md`
2. `02_ollama_m40_validation_and_mitigation.md`
3. `03_model_tiering_m40_24gb.md`
4. `04_batch_pipeline_architecture_fastapi_celery.md`
5. `05_compose_phase1_host_gpu_blueprint.md`
6. `06_production_hardening_acceptance_suite.md`

## Cockpit / control plane

- `cockpit_operator_observability.md` — link-only table: API liveness, `/api/cockpit/health`, extraction activity, GPU guard, RAG stability, embed/baseline pointers (with `LOCAL_BACKEND_PROFILE` note).

## Commentary / RAG ops

- `commentary_staging_to_qdrant.md` — staged hot-source transcripts: approve/reject, CLI promotion, definition of done for indexing.
- `youtube_channel_watch_verification.md` — verify YouTube channel watch registration, transcript polling/staging, Qdrant approval, and commentary use in chat.

## Incident Notes

- `08_openclaw_llamacpp_no_reply_incident_2026-03-08.md` - OpenClaw local/TUI `NO_REPLY` suppression incident, fix, and upgrade risk notes.
- `09_llama_server_m40_model_load_runbook.md` - M40 `llama-server` load stalls (mmap vs `--no-mmap`), router vs single-model checks, fair extraction eval prerequisites.
- `openclaw_ops_loop.md` - Standard check/fix/verify loop for TENN tasks in OpenClaw.

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

## Maintenance Cadence

- Weekly doc hygiene:
  - From repo root, run `bash scripts/check_markdown_hygiene.sh`.
- Open and verify `docs/legacy_runtime_index.md` for intentionally retained historical references.
- If the script reports broken links, fix links before merge.
- Route repository audit tasks through:
  - `.cursor/agents/repository_audit.md` (local audit contract)
  - `.codex/skills/repository-audit/SKILL.md` (repo-local Codex skill source)
- Sync repo-local Codex skills into the active Codex registry:
  - `bash scripts/sync_codex_skills.sh`
- Repo-local Codex ports now also include:
  - `architecture-check`
  - `architecture-cleanup-steward`
  - `code-reviewer`
  - `code-fixer`
  - `function-quality`
  - `intelligence-pack-review`
  - `performance-check`
  - `prompt-crafter`
  - `prompt-structure-reference`
  - `rag-stability-eval`
  - `ingest-ticker`
  - `embedding-change-checklist`
  - `migration-reviewer`
- System-only Codex skills continue to live under `$CODEX_HOME/skills/.system/`.
