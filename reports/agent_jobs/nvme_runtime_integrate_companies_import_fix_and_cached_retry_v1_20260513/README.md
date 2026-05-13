# NVMe Runtime Companies Import Fix And Cached Retry

## Verdict

partial

The committed `app.models.companies` import fix was integrated into the active NVMe runtime source tree and the focused import/test validation passed. The cached backend startup retry was blocked because `docker compose up -d` attempted to build/download the `gpu_worker` image, violating the no-build cached-start constraint.

## Branch / HEAD / Worktree

- Worktree: `/home/l4nd0/tenn-fast-dev-storage-v1`
- Branch: `fast/dev-storage-v1-20260513-170304`
- Starting HEAD: `7916e685e57b`
- Integration HEAD: `7d1b8cef0b0a`
- Source commit integrated: `2cc0f7180767`
- Integration method: cherry-pick

## Files Changed

Cherry-picked from `2cc0f7180767`:

- `docs/agent_tasks/backend_models_companies_import_validity_v1_20260513.md`
- `financial-engine_v2/backend/app/models/companies.py`
- `financial-engine_v2/backend/tests/test_models_import_contract.py`
- `reports/agent_jobs/backend_models_companies_import_validity_v1_20260513/README.md`

Created for this job:

- `docs/agent_tasks/nvme_runtime_integrate_companies_import_fix_and_cached_retry_v1_20260513.md`
- `reports/agent_jobs/nvme_runtime_integrate_companies_import_fix_and_cached_retry_v1_20260513/README.md`

Generated but not committed because `check-diff` flags these JSON artifacts despite the report-directory glob:

- `reports/agent_jobs/nvme_runtime_integrate_companies_import_fix_and_cached_retry_v1_20260513/status.json`
- `reports/agent_jobs/nvme_runtime_integrate_companies_import_fix_and_cached_retry_v1_20260513/diff-check.json`

Intentionally not touched:

- `docs/agent_tasks/runtime_topology_nvme_backend_cockpit_cached_start_v1_20260513.md`
- Runtime launch/config files
- Dockerfiles and compose files
- QueryOrchestrator, chat routes, source/provenance logic, Cockpit feature code, marketplace code
- Extraction prompts/parsers/gold labels
- Company memory, Qdrant, Postgres, news stores, model weights/config/presets

## Preflight Evidence

- `date -Iseconds`: `2026-05-13T20:13:15+10:00`
- `pwd`: `/home/l4nd0/tenn-fast-dev-storage-v1`
- `git rev-parse --show-toplevel`: `/home/l4nd0/tenn-fast-dev-storage-v1`
- Branch: `fast/dev-storage-v1-20260513-170304`
- Starting HEAD: `7916e685e57b`
- Initial NVMe status:
  - `?? docs/agent_tasks/nvme_runtime_integrate_companies_import_fix_and_cached_retry_v1_20260513.md`
  - `?? docs/agent_tasks/runtime_topology_nvme_backend_cockpit_cached_start_v1_20260513.md`
- Task-card validation: ok, no issues
- Active registry before claim: `active_jobs: []`
- Overlap check: ok, no issues
- Claim: ok, registry scope `shared`
- Initial listeners: only `:8001` listening, `llama-server` PID `3601291`
- Initial `:8001 /health`: `{"status":"ok"}`
- `git show --stat 2cc0f7180767`: 4 files changed, 334 insertions

## Validation Run

Interpreter note: the NVMe tree had no local `.venv`, and system Python failed with `ModuleNotFoundError: No module named 'sqlalchemy'`. I did not create a venv or install dependencies. I used the existing repo venv at `/mnt/hdd-data/home/l4nd0/tenn/financial-engine_v2/.venv/bin/*` with `PYTHONPATH` pointed at the active NVMe source tree.

- Backend import smoke:
  - Command imported `app.models` and `app.main`
  - Result: `backend_import_ok`
- `financial-engine_v2/backend/tests/test_models_import_contract.py -q`
  - Result: `3 passed, 6 warnings in 2.73s`
- `financial-engine_v2/backend/tests/test_pipeline_stages.py -q`
  - Result: `23 passed, 1 warning in 20.82s`
- Targeted Ruff:
  - `financial-engine_v2/backend/app/models/companies.py`
  - `financial-engine_v2/backend/tests/test_models_import_contract.py`
  - Result: `All checks passed!`
- `git diff --check`
  - Result: passed with no output

## Guardrail Status

`financial-engine_v2/backend/tests/test_rag_payload_guardrails.py -q` was run only to confirm status.

Result: `3 failed, 8 passed, 1 warning in 1.91s`

The failing test names are the same three `process_document` cases noted as a separate blocker:

- `test_process_document_deletes_existing_points_before_upsert`
- `test_process_document_skips_invalid_chunk_payloads`
- `test_process_document_upserts_financial_rows_for_ok_low_confidence`

In this NVMe tree, the immediate failure was `PermissionError: [Errno 13] Permission denied: '/home/l4nd0/tenn-fast-dev-storage-v1/financial-engine_v2/data/reports/extraction_review'`. Current evidence: `financial-engine_v2/data/reports` exists and is owned by `root:root`; `financial-engine_v2/data/reports/extraction_review` does not exist. This was not fixed because it is outside the requested import integration and `process_document` behavior was explicitly forbidden to change.

## Runtime Retry

Backend `:8000`: blocked.

Attempted from `/home/l4nd0/tenn-fast-dev-storage-v1/financial-engine_v2`:

```bash
docker compose up -d
```

Result: blocked by no-build constraint. Compose immediately attempted to build `gpu_worker`, including Dockerfile load, base image metadata, cached build steps, and then `RUN pip install -r /app/requirements.txt` with a large `torch` download. I killed the compose process before the build completed. The command exited `130` and the build step was `CANCELED`.

Rollback actions:

- Killed compose PIDs `3810304` and `3810332`.
- No containers remained running under this compose project after the abort.

Cockpit `:8081`: not started after the backend hard stop. Dependencies were present (`node_modules_present`), but the task requires stopping and reporting when cached backend startup requires a build.

`:8001` remained healthy.

## Runtime Validation

Listeners after retry:

- `:8000`: not listening
- `:8001`: listening, `llama-server` PID `3601291`
- `:8081`: not listening
- `:8002`: not listening

Process CWD/root evidence:

- `llama-server` PID `3601291` CWD: `/home/l4nd0/tenn-fast-dev-storage-v1`
- `llama-server` command: `/mnt/hdd-data/home/l4nd0/tenn/tools/llama.cpp/build-cuda/bin/llama-server --main-gpu 0 --threads 4 --host 0.0.0.0 --port 8001 --spec-type ngram-simple --models-dir /mnt/nvme/tenn/models --models-max 1 --models-preset /home/l4nd0/.config/tenn/llamacpp-presets.ini --api-key local-openai-key --parallel 1`
- Backend process CWD/root: DATA_MISSING; backend did not start.
- Cockpit process CWD/root: DATA_MISSING; no `:8081` Cockpit process was started. A separate `next-server` PID `1942939` exists at `127.0.0.1:5050` with CWD `/home/l4nd0/.nvm/versions/node/v22.22.0/lib/node_modules/chorus-codes`, unrelated to this NVMe Cockpit target.

Health probes:

- `http://127.0.0.1:8000/api/health`: connection refused, `http_code=000`, `time_total=0.000132`
- `http://127.0.0.1:8001/health`: `{"status":"ok"}`, `http_code=200`, `time_total=0.000245`
- `http://127.0.0.1:8001/v1/models`: `http_code=200`, `time_total=0.001087`
- `http://127.0.0.1:8081/api/cockpit/health`: connection refused, `http_code=000`, `time_total=0.000125`
- `http://127.0.0.1:8081/api/cockpit/home`: connection refused, `http_code=000`, `time_total=0.000165`; no `data_state` available

Docker compose:

- Pre-retry `docker compose ps`: no services running
- Post-abort `docker compose ps`: no services running
- Compose declared volumes: `fe_qdrant`, `fe_pgdata`
- Existing Docker volumes observed: `financial-engine_v2_fe_pgdata`, `financial-engine_v2_fe_qdrant`
- No `docker compose down`, volume removal, or destructive volume command was run.

## Final Git Status

NVMe status before committing this report:

- `?? docs/agent_tasks/nvme_runtime_integrate_companies_import_fix_and_cached_retry_v1_20260513.md`
- `?? docs/agent_tasks/runtime_topology_nvme_backend_cockpit_cached_start_v1_20260513.md`

Preserve worktree status:

- `?? docs/agent_tasks/current_state_collision_runtime_remediation_audit_v1_20260513.md`
- `?? docs/agent_tasks/nvme_hot_dev_base_sync_v1_20260513.md`
- `?? docs/agent_tasks/overview_home_audit_closeout_blocker_classification_v1_20260513.md`
- `?? docs/agent_tasks/overview_home_wiring_completion_audit_v1_20260513.md`
- `?? docs/agent_tasks/runtime_topology_nvme_backend_cockpit_cached_start_v1_20260513.md`
- `?? docs/agent_tasks/runtime_topology_nvme_enablement_v1_20260513.md`

## DATA_MISSING

- Backend `:8000` runtime CWD/root evidence is unavailable because backend did not start under the cached no-build constraint.
- Cockpit `:8081` runtime CWD/root evidence is unavailable because Cockpit was not started after the backend hard stop.
- The expected `process_document` assertion-level guardrail failure was not reached in this NVMe tree because the three tests failed earlier on root-owned report directory permissions.

## Next Safe Step

Create a separate Runtime/Evaluation task to make cached compose startup possible without building `gpu_worker`, or explicitly approve a build-capable runtime refresh. Separately, handle the root-owned `financial-engine_v2/data/reports` permission issue or rerun the guardrail test in an environment where the extraction review report path is writable before comparing the original `process_document` assertions.

## Project Memory Save Recommendation

Save that the active NVMe runtime tree now contains the `app.models.companies` import fix at `7d1b8cef0b0a`, but cached compose startup remains blocked because `docker compose up -d` attempts a `gpu_worker` build/download under the current image/cache state. Also save that `test_rag_payload_guardrails.py` in the NVMe tree fails the same three `process_document` test names earlier on root-owned `financial-engine_v2/data/reports` permissions.
