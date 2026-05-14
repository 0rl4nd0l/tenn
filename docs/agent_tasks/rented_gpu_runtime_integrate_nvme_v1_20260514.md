---
job_id: rented_gpu_runtime_integrate_nvme_v1_20260514
lane: Query Orchestration
owner: Codex
mutation_mode: safe_extension
approval_required: true
approval_id: USER_APPROVED_RENTED_GPU_RUNTIME_INTEGRATE_NVME_20260514_GPT
production_data_access: false
timeout_seconds: 7200
output_dir: reports/agent_jobs/rented_gpu_runtime_integrate_nvme_v1_20260514
allowed_files:
  - docs/agent_tasks/rented_gpu_runtime_integrate_nvme_v1_20260514.md
  - financial-engine_v2/backend/app/services/cockpit_service.py
  - financial-engine_v2/backend/app/routes/cockpit_api.py
  - cockpit-ui/lib/cockpit-types.ts
  - cockpit-ui/lib/cockpit-store.ts
  - cockpit-ui/lib/api-client.ts
  - cockpit-ui/components/cockpit/cockpit-layout.tsx
  - cockpit-ui/components/cockpit/chat/chat-screen.tsx
  - cockpit-ui/components/cockpit/settings/settings-screen.tsx
  - cockpit-ui/lib/marketplace-assistant.ts
  - cockpit-ui/components/cockpit/cockpit-sidebar.test.tsx
  - reports/agent_jobs/rented_gpu_runtime_integrate_nvme_v1_20260514/README.md
  - reports/agent_jobs/rented_gpu_runtime_integrate_nvme_v1_20260514/status.json
  - reports/agent_jobs/rented_gpu_runtime_integrate_nvme_v1_20260514/diff-check.json
---

# Task

Integrate the clean rented-GPU runtime-target port into the active NVMe branch, then run no-remote validation only.

Primary lane: Query Orchestration
Supporting lanes: Runtime / Reporting / Evaluation
Mode: SAFE EXTENSION
Expected collision risk: HIGH by surface, controlled by clean active worktree, tight allowlist, and no live remote call.

# Context

The clean rented-GPU port was completed in an isolated worktree:

- source branch: `safe/rented-gpu-runtime-port-v1-20260514`
- source worktree: `/home/l4nd0/tenn-rented-gpu-runtime-port-v1-20260514`
- source commit: `5da86ab3eaba`
- commit subject: `milestone(query): add rented gpu runtime target`

The clean port changed exactly the 10 classified rented-GPU feature files plus task/report artifacts. Validation passed there:
- backend py_compile
- frontend tsc --noEmit
- focused Vitest: 3 files / 7 tests
- git diff --check
- task-card check-diff
- no-remote fail-fast resolver smoke

Goal:
Bring the 10 rented-GPU feature changes into the active NVMe branch:

`/home/l4nd0/tenn-fast-dev-storage-v1`

Do not run a live rented-GPU call in this task.

# Required preflight

Run from:

`/home/l4nd0/tenn-fast-dev-storage-v1`

Commands:

- date -Iseconds
- pwd
- git rev-parse --show-toplevel
- git branch --show-current
- git rev-parse --short=12 HEAD
- git status --short --untracked-files=all
- git worktree list
- python3 scripts/agent_job_contract.py validate docs/agent_tasks/rented_gpu_runtime_integrate_nvme_v1_20260514.md
- python3 scripts/agent_job_registry.py list-active
- python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/rented_gpu_runtime_integrate_nvme_v1_20260514.md
- claim task if safe
- verify source commit exists:
  - `git show --stat --oneline --decorate --no-renames 5da86ab3eaba`

# Required runtime status check

Do not restart runtime.

Run only:

- `curl -m 5 -sS http://127.0.0.1:8000/api/health || true`
- `curl -m 5 -sS http://127.0.0.1:8001/health || true`
- `curl -m 5 -sS http://127.0.0.1:8081/api/cockpit/health || true`

If any are down, record it. Do not fix runtime in this task.

# Integration method

Preferred:

1. Use a controlled no-commit cherry-pick:

   `git cherry-pick --no-commit 5da86ab3eaba`

2. Immediately inspect the resulting diff.

3. Keep only the 10 rented-GPU feature files in this integration commit, plus this integration task card/report artifacts.

4. Do not bring across the old source branch task card/report artifacts unless already staged by cherry-pick and required for traceability. Prefer excluding prior task-card/report artifacts from the integration commit and documenting the source commit in this task report.

If cherry-pick with `--no-commit` is not clean:
- stop and report if conflicts touch files outside the 10 rented-GPU feature files.
- do not resolve conflicts broadly.

If the source commit is not reachable:
- manually copy/reconstruct only the 10 feature-file changes from `/home/l4nd0/tenn-rented-gpu-runtime-port-v1-20260514`.
- stop if manual porting requires files outside allowlist.

# Feature behavior that must be present after integration

- `local | rented_gpu | auto` chat runtime target.
- runtime target persisted in Cockpit preferences without wiping unrelated preferences.
- explicit `rented_gpu` selection fails fast if `TENN_RENTED_GPU_LLAMACPP_URL` is unset.
- chat requests send `runtime_target`.
- rented GPU model discovery appears in Settings.
- rented GPU turns use runtime-scoped `LlamaCppClient` through `/local` against remote OpenAI-compatible llama.cpp endpoint.
- `auto` uses rented GPU only when configured and the turn is heavy: long prompt, attached sources, or strategy mode.
- Settings exposes runtime toggle plus rented GPU endpoint/health display.
- local remains default.

# Explicitly forbidden

Do not modify:

- runtime scripts
- Docker/compose files
- model lifecycle scripts
- extraction scripts
- embeddings/vector config
- Qdrant/Postgres/news/company-memory data
- Financial Truth/extraction paths
- source-label/provenance implementation files
- Home body-shape guard files
- marketplace behavior outside the already-allowed marketplace assistant type/runtime propagation

Do not:

- start/stop/restart runtime
- run Docker build
- mutate DBs
- run live rented GPU calls
- open or depend on an SSH tunnel
- commit dirty preserve worktree changes
- include unrelated forced-Anthropic/runtime/launcher/secrets changes from `/mnt/hdd-data/home/l4nd0/tenn`

# Hard stops

Stop and report if:

- active NVMe worktree is not clean before integration
- registry claim fails
- source commit cannot be found
- cherry-pick conflicts outside allowlist
- diff includes files outside the allowed 10 feature files plus this task card/report
- local-first default is not preserved
- missing endpoint silently falls back in a misleading way
- `auto` routes normal/simple turns remotely without heavy-turn criteria
- TypeScript/backend checks fail in a way requiring broad redesign
- source-label/provenance semantics become ambiguous
- validation requires dependency installation

# Required validation

Backend:

- `PYTHONPYCACHEPREFIX=/tmp/tenn_pycache python3 -m py_compile financial-engine_v2/backend/app/services/cockpit_service.py financial-engine_v2/backend/app/routes/cockpit_api.py`

Frontend:

- `pnpm --dir cockpit-ui exec tsc --noEmit`
- `pnpm --dir cockpit-ui exec vitest run components/cockpit/cockpit-sidebar.test.tsx components/cockpit/settings/settings-screen.test.tsx lib/api-client.test.ts`

No-remote smoke:

- Verify explicit `rented_gpu` with `TENN_RENTED_GPU_LLAMACPP_URL` unset returns a clear missing endpoint/config error.
- Verify `auto` with no endpoint keeps light/simple context local, or returns the expected `local:auto_rented_gpu_not_configured` style metadata.
- Do not call a live remote endpoint.

Static checks:

- `git diff --check`
- `git diff --name-status`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/rented_gpu_runtime_integrate_nvme_v1_20260514.md`

# Commit rules

Commit only if:

- changed files are exactly within the allowed files
- validation passes
- no live rented GPU call was required
- no unrelated dirty work is included

Suggested commit:

`milestone(query): integrate rented gpu runtime target`

Commit body should include:

- source commit: `5da86ab3eaba`
- local/rented_gpu/auto behavior
- endpoint env var: `TENN_RENTED_GPU_LLAMACPP_URL`
- no live remote smoke test performed
- validations run
- explicit exclusions

# Final report

Write:

`reports/agent_jobs/rented_gpu_runtime_integrate_nvme_v1_20260514/README.md`

Include:

- verdict: completed / partial / blocked
- branch / HEAD / worktree
- source commit and source worktree
- whether cherry-pick or manual port was used
- files changed
- validation results
- local-first/default behavior status
- fail-fast missing endpoint status
- auto routing rule status
- marketplace assistant impact
- source-label/provenance impact
- live rented GPU smoke gap
- exact tunnel/env setup needed for future smoke:
  - `export TENN_RENTED_GPU_LLAMACPP_URL=http://127.0.0.1:18001`
  - `ssh -i ~/.ssh/id_ed25519 -p <VAST_SSH_PORT> -L18001:localhost:8001 root@<VAST_SSH_HOST>`
- future live smoke-test recommendation
- DATA_MISSING
- final git status
- registry release/list-active status
- Project Memory save recommendation
