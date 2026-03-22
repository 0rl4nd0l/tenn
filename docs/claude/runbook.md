# Runbook (Consolidated)

## Source Trace
- `docs/ops/quickstart.md` (Confirmed — incident router)
- `docs/ops/README.md` (Confirmed — execution order, ownership)
- `docs/ops/openclaw_ops_loop.md` (Confirmed — standard ops loop)
- `docs/validation_baseline.md` (Confirmed — validated command sequence)
- `docs/setup/troubleshooting.md` (Confirmed — common issues)
- `docs/entrypoints.md` (Confirmed — agent boot sequence)

---

## Quick Start

```bash
# 1. Start system (canonical)
bash scripts/start_system.sh

# 2. Validate
bash scripts/validate_system.sh

# 3. Health check
curl -sS http://127.0.0.1:8000/api/health
```

If `start_system.sh` fails: see **Incident Router** below.

---

## Standard Ops Loop (from openclaw_ops_loop.md)

For any Tenn task in OpenClaw:
1. **Check** — health check, verify services, review logs
2. **Fix** — targeted change in smallest scope
3. **Verify** — re-run health check, run affected tests, confirm gate passes

Preferred local inference path: **llama.cpp** (not Ollama) for agent/coding workflows.

---

## Incident Router

| Symptom | Go To |
|---------|-------|
| NVML / GPU driver errors | `docs/ops/01_nvml_host_stabilization_runbook.md` |
| Ollama CUDA / M40 errors | `docs/ops/02_ollama_m40_validation_and_mitigation.md` |
| Model tier / VRAM / OOM | `docs/ops/03_model_tiering_m40_24gb.md` |
| Celery / batch pipeline failures | `docs/ops/04_batch_pipeline_architecture_fastapi_celery.md` |
| Compose / Docker startup issues | `docs/ops/05_compose_phase1_host_gpu_blueprint.md` |
| Production gate failures | `docs/ops/06_production_hardening_acceptance_suite.md` |
| OpenClaw/llama.cpp NO_REPLY | `docs/ops/08_openclaw_llamacpp_no_reply_incident_2026-03-08.md` |
| Port conflict | See Troubleshooting below |
| Auth errors | See Troubleshooting below |
| Missing Qdrant collections | See Troubleshooting below |

Full incident quickstart: `docs/ops/quickstart.md`.

---

## Full Validation Sequence (2026-03-19 baseline)

```bash
bash scripts/start_system.sh
bash scripts/validate_system.sh
python -m ruff check autodev financial-engine_v2/backend scripts
pytest autodev/tests
pytest financial-engine_v2/backend/tests
pytest scripts
bash scripts/run_canonical_dataset_checks.sh
python scripts/check_canonical_regression.py \
  --baseline reports/baselines/canonical_eval_baseline_latest.json \
  --news-report reports/news_eval_report.json \
  --company-report reports/company_eval_report_v2.json \
  --reference-report reports/eval_queries_report.json
python scripts/validate_financial_metrics_gates.py \
  reports/financial_metrics.json \
  --out-json reports/financial_metrics.gates.json
python scripts/validate_financial_coverage_gates.py \
  reports/financial_metrics.json \
  --out-json reports/financial_metrics.coverage_gates.json
```

Required fixtures for canonical regression:
- `reports/baselines/canonical_eval_baseline_latest.json`
- `reports/news_eval_queries.json`
- `reports/company_eval_queries.json`
- `reports/eval_queries.json`

---

## System Diagnostics

```bash
bash scripts/cockpit_doctor.sh
```

Checks: Docker, Compose, health, ports, URLs.

---

## Common Issues (from docs/setup/troubleshooting.md)

**Auth errors on API calls**
- Verify `LLM_API_KEY` is set in `.env` or `.env.local`
- Default value: `local-openai-key`

**Missing Qdrant collections**
- Check Qdrant is running: `curl http://127.0.0.1:6333/collections`
- Verify `QDRANT_URL` in env
- Collection for chat: `commentary_chunks` (not `asx_docs`)

**Port conflicts**
- Check occupied ports: `ss -tlnp | grep -E '8000|8001|6333|6379'`
- Kill conflicting process or override port via env var

**DATA_ROOT / path issues**
- Local launcher forces `DATA_ROOT` to repo `data/` unless shell env overrides it
- Docker paths (`/data/...`) indicate shell env not set; set `DATA_ROOT` explicitly

**venv / dependency issues**
- Use isolated venv at `/workspace/.venv` or repo root `.venv`
- Install: `pip install -r requirements.txt && pip install -r financial-engine_v2/backend/requirements.txt`

**Restricted socket environment**
- `SKIP due restricted environment` from health/smoke checks is expected and non-fatal

---

## Service Start Order

From `docs/setup/runtime.md`:
1. Postgres (if Docker mode)
2. Redis
3. Qdrant
4. Ollama / llama.cpp (host services)
5. Backend (`run_local_backend.sh`)
6. Worker (if async tasks needed)

---

## Ops Pack Runbook Sequence

For host stabilization or new infrastructure setup, follow in order:
1. `docs/ops/01_nvml_host_stabilization_runbook.md`
2. `docs/ops/02_ollama_m40_validation_and_mitigation.md`
3. `docs/ops/03_model_tiering_m40_24gb.md`
4. `docs/ops/04_batch_pipeline_architecture_fastapi_celery.md`
5. `docs/ops/05_compose_phase1_host_gpu_blueprint.md`
6. `docs/ops/06_production_hardening_acceptance_suite.md`

---

## Cloud Worktree (for isolated review)

```bash
bash scripts/prepare_cloud_worktree.sh
```

Creates a clean sibling worktree from current HEAD. Use for Cloud tasks or isolated PR review. Full rules: `docs/cloud_workflow.md`.

---

## Failure Model

Source: `docs/architecture/10_failure_model.md` (Confirmed)

| Behavior | When Used | Examples |
|----------|-----------|---------|
| **Fail-fast** | Misconfiguration, invariant violations, startup validation | Dimension mismatch, distance mismatch, embedding model mismatch, Qdrant/primary embedding endpoint or DB unreachable at startup, OpenBB empty payload |
| **Retry** | Transient service unavailability (request or task time) | Primary embedding endpoint/Qdrant/DB transiently unavailable; Celery task retry |
| **Skip** | Per-item failures in batch jobs | One PDF corrupt/missing in backfill; duplicate `source_url` (skip insert) |

No silent degradation. Fail fast on config errors.

**Startup fail-fast conditions:**
- Embedding endpoint (LLAMACPP/OLLAMA/OpenAI) unreachable or returns empty → startup raises, does not start
- Qdrant unreachable or collection validation fails → startup raises (503 at request time)
- Dimension mismatch (collection ≠ embedding model) → `RuntimeError`
- Distance mismatch (must be COSINE) → `RuntimeError`
- Embedding model mismatch (config ≠ `reports/runtime_embedding_model.txt`) → startup raises

**Remediation for dimension/distance/model mismatch:** rebuild the Qdrant collection; do not run with mismatch. See `docs/architecture/11_rebuild_and_recovery.md`.

---

## Weekly Maintenance

```bash
bash scripts/check_markdown_hygiene.sh
```

Fix broken links before merge. Review `docs/legacy_runtime_index.md` for intentionally retained historical references.
