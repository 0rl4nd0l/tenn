# Worker Runtime Provenance Audit

## Scope

- GitHub issue: #58.
- Lane: Reporting.
- Execution mode: AUDIT MODE.
- Target system layer: runtime identity, worker provenance, and report visibility only.
- Contract boundary: no source, config, service, runtime, Docker, data-store, model, GPU, or live worker changes.

## Findings

1. Compose backend receives git provenance env: `TENN_GIT_HEAD`, `TENN_GIT_HEAD_SHORT`, `TENN_GIT_BRANCH`, `TENN_GIT_DIRTY`, `TENN_GIT_STATUS_LINE_COUNT`, and `TENN_BUILD_TIME`. Evidence: `financial-engine_v2/docker-compose.yml:37-50`.
2. Compose `worker`, `gpu_worker`, and `fe_beat` do not receive matching `TENN_GIT_*` env in the current compose file. They receive only a narrower environment block. Evidence: `financial-engine_v2/docker-compose.yml:77-122`, `135-158`.
3. A prior runtime topology report independently records the same gap: `fe_worker` and `fe_gpu_worker` do not expose `TENN_GIT_*` provenance env and only backend wires those vars. Evidence: `reports/agent_jobs/runtime_topology_reconciliation_impl_v1_20260524/README.md:50-55`.
4. `scripts/start_full_stack.sh` computes and exports git provenance env, but its log message calls it backend git provenance and Compose only consumes those env keys where they are listed.
5. Backend startup logs and capability status resolve LLM, extraction, and embedding runtime model/url identity. Evidence: `financial-engine_v2/backend/app/main.py:1179-1208`, `1758-1765`.
6. `confirmed_metric_coverage_review.py` has a robust artifact-level git provenance helper that reads `TENN_GIT_*` env or falls back to git commands, but that is specific to confirmed metric coverage review artifacts.
7. `financial-engine_v2/scripts/run_worker.sh` launches a Celery worker after project/data-root setup but does not export git provenance, worker role, queue identity, runtime identity, or model identity.

## Classification

- Backend runtime provenance: partial, present for Compose backend and selected artifacts.
- Worker git provenance parity: confirmed gap.
- GPU worker git provenance parity: confirmed gap.
- Worker role/queue identity in reports: confirmed gap for generic task reports.
- Model/runtime references: present at backend startup/status level, incomplete at worker/task artifact level.
- Live runtime truth: DATA_MISSING, because this audit did not start, stop, inspect Docker processes, or query live worker services.

## Recommended Child Task

`worker_runtime_provenance_env_parity_safe_extension_v1_20260525`

Proposed safe-extension scope:

- Pass existing `TENN_GIT_*` and `TENN_BUILD_TIME` env to `worker`, `gpu_worker`, and `fe_beat`.
- Add explicit worker role env such as `TENN_WORKER_ROLE=worker|gpu_worker|beat` and queue names where applicable.
- Surface those fields in worker startup logs and any worker-produced task/report artifacts.
- Add a focused test or smoke fixture proving backend, worker, and GPU worker provenance fields are present and distinguishable.

Do not change model routing, GPU binding, worker concurrency, queue semantics, service startup behavior, or canonical financial truth in that child task.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/worker_gpu_worker_provenance_env_parity_audit_v1_20260525.md`: passed.
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/worker_gpu_worker_provenance_env_parity_audit_v1_20260525.md`: passed.
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/worker_gpu_worker_provenance_env_parity_audit_v1_20260525.md`: passed.
- `python3 scripts/agent_job_registry.py release worker_gpu_worker_provenance_env_parity_audit_v1_20260525`: passed.
- `python3 -m json.tool reports/agent_jobs/worker_gpu_worker_provenance_env_parity_audit_v1_20260525/worker_runtime_inventory.json`: passed.
- `python3 -m json.tool reports/agent_jobs/worker_gpu_worker_provenance_env_parity_audit_v1_20260525/provenance_gap_register.json`: passed.
- `python3 -m json.tool reports/agent_jobs/worker_gpu_worker_provenance_env_parity_audit_v1_20260525/status.json`: passed.
- `git diff --check`: passed.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/worker_gpu_worker_provenance_env_parity_audit_v1_20260525.md`: passed.
