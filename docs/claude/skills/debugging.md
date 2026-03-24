# Debugging Skill

## Source Trace
- `docs/ops/quickstart.md` (Confirmed — incident router)
- `docs/setup/troubleshooting.md` (Confirmed — common issues)
- `docs/ops/openclaw_ops_loop.md` (Confirmed — ops loop)
- `docs/ops/08_openclaw_llamacpp_no_reply_incident_2026-03-08.md` (Confirmed — incident example)
- `docs/architecture/10_failure_model.md` (Confirmed — referenced)

---

## Debugging Process

Follow the standard ops loop:
1. **Check** — gather evidence (logs, health, service state)
2. **Identify** — narrow to one subsystem
3. **Fix** — targeted minimal change
4. **Verify** — re-run health check + affected tests + relevant gate

Do not apply fixes in parallel until you have isolated the cause.

---

## Initial Triage

```bash
# Health check
curl -sS http://127.0.0.1:8000/api/health

# Full diagnostics
bash scripts/cockpit_doctor.sh

# Service ports
ss -tlnp | grep -E '8000|8001|8081|6333|6379|11434|5432'
```

---

## Per-Subsystem Debugging

### Backend API (FastAPI, port 8000)

1. Check process is running: `ss -tlnp | grep 8000`
2. Check startup logs: look for uvicorn output in the terminal running `run_local_backend.sh`
3. Verify env: `DATA_ROOT`, `LLM_URL`, `QDRANT_URL` are set correctly
4. Check `LOCAL_BACKEND_PROFILE` — `isolated` disables embeddings/Qdrant/extraction
5. Try: `curl -sS http://127.0.0.1:8000/api/health`

### Qdrant / RAG (port 6333)

1. Check Qdrant is running: `curl http://127.0.0.1:6333/collections`
2. Verify `QDRANT_URL` in env
3. Confirm collection exists: `commentary_chunks` (not `asx_docs`)
4. Check `commentary_chunks_v2` if primary has no data

### LLM / Inference (llama.cpp :8001, Ollama :11434)

1. Check llama.cpp: `curl http://127.0.0.1:8001/v1/models`
2. Check Ollama: `curl http://127.0.0.1:11434/api/tags`
3. For M40/Maxwell CUDA issues: see `docs/ops/02_ollama_m40_validation_and_mitigation.md`
4. For NO_REPLY in OpenClaw sessions: see `docs/ops/08_openclaw_llamacpp_no_reply_incident_2026-03-08.md`
5. Check `LLM_URL` vs `LLAMACPP_URL` — local launcher may override

### Celery / Worker

1. Check Redis is running: `redis-cli ping`
2. Check worker process is running
3. Verify `CELERY_BROKER_URL` and `CELERY_RESULT_BACKEND` in env
4. For batch pipeline failures: see `docs/ops/04_batch_pipeline_architecture_fastapi_celery.md`

### GPU / NVML

1. Check NVML: `nvidia-smi`
2. For driver errors: see `docs/ops/01_nvml_host_stabilization_runbook.md`
3. For model OOM: see `docs/ops/03_model_tiering_m40_24gb.md`

### Tests Failing

1. Run targeted: `pytest financial-engine_v2/backend/tests -x -v`
2. Check pythonpath: `pytest.ini` includes `.`, `financial-engine_v2/backend`, `scripts`
3. Check lint first: `python -m ruff check financial-engine_v2/backend`
4. Fixture missing: ensure `reports/baselines/canonical_eval_baseline_latest.json` exists for regression tests

---

## Common Failure Patterns

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| `/chat` returns 500 | Profile is `full` but Qdrant empty or llama.cpp not running | Switch to `isolated` or start dependencies |
| `/chat` returns degraded | Profile is `isolated` — expected | Switch to `full` if end-to-end needed |
| Auth error on API | `LLM_API_KEY` not set | Set in `.env.local` or shell env |
| `DATA_ROOT` → `/data/...` | Shell env not set; Docker path leaking | Set `DATA_ROOT` explicitly in shell |
| `SKIP due restricted environment` | Restricted socket environment | Non-fatal; continue |
| `no module named X` | venv not activated or deps not installed | Activate venv; run `pip install -r requirements.txt` |
| Ruff failure | Lint error in modified file | Run `python -m ruff check <file> --fix` |
| Canonical regression failure | Output drift from baseline | Investigate which metric drifted; do not modify thresholds to pass |

---

## What NOT to Do

- Do not modify financial gate thresholds to make failing gates pass.
- Do not restart services without identifying the root cause.
- Do not assume `SKIP` messages are errors — restricted socket environments produce these normally.
- Do not use `--no-verify` to bypass pre-commit hooks.
