---
job_id: home_body_shape_timing_guard_v1_20260514
lane: Reporting
owner: Codex
mutation_mode: safe_extension
approval_required: true
approval_id: USER_APPROVED_HOME_BODY_SHAPE_TIMING_GUARD_20260514_GPT
production_data_access: false
timeout_seconds: 3600
output_dir: reports/agent_jobs/home_body_shape_timing_guard_v1_20260514
allowed_files:
  - docs/agent_tasks/home_body_shape_timing_guard_v1_20260514.md
  - cockpit-ui/lib/cockpit-home-api.test.ts
  - cockpit-ui/lib/cockpit-home-contract.test.ts
  - cockpit-ui/lib/cockpit-home-live-shape.test.ts
  - reports/agent_jobs/home_body_shape_timing_guard_v1_20260514/README.md
  - reports/agent_jobs/home_body_shape_timing_guard_v1_20260514/status.json
  - reports/agent_jobs/home_body_shape_timing_guard_v1_20260514/diff-check.json
---

# Task

Add or validate a bounded Home body-shape and timing guard for `/api/cockpit/home`.

Primary lane: Reporting
Supporting lanes: Evaluation / Provenance
Mode: SAFE EXTENSION
Expected collision risk: MEDIUM

# Context

Current runtime is healthy from the NVMe worktree:

- worktree: `/home/l4nd0/tenn-fast-dev-storage-v1`
- branch: `fast/dev-storage-v1-20260513-170304`
- latest runtime check reported clean git status and active registry jobs empty
- `:8000/api/health` returned ok
- `:8001/health` returned ok
- `:8081/api/cockpit/health` returned healthy
- `/api/cockpit/home` returned HTTP 200 in about `0.073s`
- Home payload was `ok:true`, `data_state:"PARTIAL"`, `degraded:false`
- missing/partial sections include recent commentary, market-update signals, and narrative producers

Goal:
Create a guard that proves Home is reachable, fast enough, structurally stable, and honest about partial/missing data before any Home UI/product implementation continues.

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
- python3 scripts/agent_job_contract.py validate docs/agent_tasks/home_body_shape_timing_guard_v1_20260514.md
- python3 scripts/agent_job_registry.py list-active
- python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/home_body_shape_timing_guard_v1_20260514.md
- claim task if safe
- runtime health:
  - `curl -m 5 -sS http://127.0.0.1:8000/api/health`
  - `curl -m 5 -sS http://127.0.0.1:8001/health`
  - `curl -m 5 -sS http://127.0.0.1:8081/api/cockpit/health`

# Inspect first

Inspect:

- `cockpit-ui/lib/cockpit-home-api.ts`
- `cockpit-ui/lib/cockpit-home-contract.ts`
- existing tests:
  - `cockpit-ui/lib/cockpit-home-api.test.ts`
  - `cockpit-ui/lib/cockpit-home-contract.test.ts`
- route handler:
  - `cockpit-ui/app/api/cockpit/home/route.ts`
- latest runtime closeout report:
  - `reports/agent_jobs/nvme_runtime_migration_closeout_v1_20260513/README.md`
- any prior Overview/Home audit report if present:
  - `reports/agent_jobs/overview_home_wiring_completion_audit_v1_20260513/README.md`

# Guard requirements

The guard should cover:

1. HTTP status and timing
   - `/api/cockpit/home` must return HTTP 200.
   - Measure latency with a bounded timeout.
   - Record pass/fail threshold recommendation.
   - Do not fail the task solely because live data is PARTIAL if payload honestly reports it.

2. Required body shape
   Verify that the response contains expected top-level fields such as:
   - `ok`
   - `generated_at`
   - `source_label_taxonomy_version`
   - `data_state`
   - `degraded`
   - `data_missing`
   - core Home sections currently expected by contract

3. Trust/data honesty
   Verify:
   - `data_state:"PARTIAL"` is allowed only when missing sections are explicitly represented.
   - `degraded:false` must not hide missing data.
   - source/trust labels do not imply complete financial-truth support for local/partial/demo/operational data.
   - local portfolio/holdings must remain local-personal-data labelled where applicable.
   - missing narrative/commentary/market-update sections must not be silently rendered as complete.

4. Known missing sections
   Record observed status for:
   - recent commentary
   - market-update signals
   - narrative producers
   - attention queue
   - portfolio/holdings
   - market session/data health
   - source labels / source drawer inputs if present

5. Regression guard
   Add or update focused tests only if they are already part of the Home contract layer and can run without new dependency installs.
   Prefer focused tests over UI/browser tests for this task.

# Allowed work

You may:

- add or update focused Home contract/API tests;
- add a live-shape test only if it can be safely skipped when runtime is down or clearly marked as live optional;
- write the report artifacts;
- capture live response summary and timing in the report.

# Explicitly forbidden

Do not:

- change Home product/UI implementation
- change backend route behavior
- change BFF behavior except tests
- change QueryOrchestrator
- change source-label/provenance logic
- change memory cleanup
- touch company_memory.sqlite
- touch Qdrant/Postgres/news/extraction/model data
- run Docker build
- restart runtime unless health is down at preflight, then stop and ask/report
- run browser automation unless explicitly needed and already available
- add external dependencies
- hide missing data or relax trust semantics
- convert PARTIAL into READY unless evidence supports it

# Hard stops

Stop and report if:

- registry claim fails
- active runtime health is down on :8000, :8001, or :8081
- Home endpoint is unreachable
- required body shape is missing in a way that suggests product regression
- any required fix would touch product code or backend behavior
- tests require dependency installation
- UI/source-label/trust semantics look misleading and cannot be addressed by tests/report only

# Validation required

Run what is available without installing dependencies:

- `curl -m 30 -sS -w '\nHTTP %{http_code} time %{time_total}\n' http://127.0.0.1:8081/api/cockpit/home`
- existing focused tests:
  - `pnpm -C cockpit-ui exec vitest run lib/cockpit-home-api.test.ts lib/cockpit-home-contract.test.ts`
- any new/updated focused test file
- `pnpm -C cockpit-ui exec tsc --noEmit`
- git diff --check
- python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/home_body_shape_timing_guard_v1_20260514.md
- python3 scripts/agent_job_registry.py release home_body_shape_timing_guard_v1_20260514
- python3 scripts/agent_job_registry.py list-active
- final git status --short --untracked-files=all

# Commit rules

Commit only if:

- changes are limited to task card, focused tests, and report artifacts;
- no product implementation files are changed;
- tests/checks pass or live-only checks are clearly environment-marked.

Suggested commit message:

`milestone(reporting): guard cockpit home body shape`

Commit body should include:

- Home endpoint HTTP/timing result
- observed `data_state`
- observed `degraded`
- known missing sections
- tests run
- whether any live optional test was added/skipped

# Final report

Write:

reports/agent_jobs/home_body_shape_timing_guard_v1_20260514/README.md

Include:

- verdict:
  - passed / passed with caveats / blocked / failed
- branch / HEAD / worktree
- runtime quick health
- Home endpoint timing
- body-shape check summary
- observed `data_state`
- observed `degraded`
- missing sections
- trust/source-label observations
- tests added/updated
- validation results
- files changed
- final git status
- active registry state
- whether Home implementation/polish may proceed
- recommended next task
- Project Memory save recommendation
