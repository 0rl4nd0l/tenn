---
job_id: memory_dirty_work_and_route_validation_closeout_20260513
lane: Memory
owner: Codex
allowed_files:
  - docs/agent_tasks/memory_dirty_work_and_route_validation_closeout_20260513.md
  - cockpit-ui/app/memory/page.tsx
  - cockpit-ui/components/cockpit/memory/memory-screen.tsx
  - cockpit-ui/tests/memory.spec.ts
  - docs/agent_tasks/cockpit_route_validation_pass_v1_20260513.md
  - reports/agent_jobs/cockpit_route_validation_pass_v1_20260513/**
  - reports/agent_jobs/memory_dirty_work_and_route_validation_closeout_20260513/**
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/memory_dirty_work_and_route_validation_closeout_20260513
mutation_mode: safe_extension
production_data_access: false
---

# Task

Coordinate the unrelated dirty Memory page/UI/test files that blocked the Cockpit route validation report commit.

This task has two separate outcomes:

1. Memory dirty-work outcome:
   - classify the dirty Memory files
   - if safe and validated, commit them as a separate Memory-lane commit
   - if unsafe or ambiguous, stop and report BLOCKED without reverting or deleting them

2. Reporting closeout outcome:
   - after Memory dirty work is clean or safely preserved, commit only the Cockpit route validation task/report artifacts as a separate Reporting docs commit

Do not mix Memory source/test changes and Reporting report artifacts in one commit.

# Hard boundaries

Do not touch:
- any file outside allowed_files
- backend code
- runtime configs
- package files
- data stores
- migrations
- Qdrant/Redis/Postgres/SQLite data
- extraction/gold labels
- marketplace scan/sync code
- unrelated cockpit-ui files

Do not run:
- memory writes against product stores
- thesis proposal apply/confirm/reject
- extraction jobs
- ingestion/backfill/Qdrant sync
- migrations
- model load/restart
- marketplace scans/syncs
- mutating UI/browser actions

Do not revert, delete, or discard the dirty Memory changes unless explicitly instructed by the user. If they are unsafe, leave them untouched and report exactly why.

# Required preflight

Run and record:

- date -Iseconds
- pwd
- git rev-parse --show-toplevel
- git branch --show-current
- git rev-parse HEAD
- git rev-parse --short=12 HEAD
- git status --short --untracked-files=all
- git diff --name-status
- git diff --cached --name-status
- git worktree list
- python3 scripts/agent_job_contract.py validate docs/agent_tasks/memory_dirty_work_and_route_validation_closeout_20260513.md
- python3 scripts/agent_job_registry.py list-active
- python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/memory_dirty_work_and_route_validation_closeout_20260513.md
- python3 scripts/agent_job_registry.py claim docs/agent_tasks/memory_dirty_work_and_route_validation_closeout_20260513.md

Stop if:
- task card validation fails
- active registry conflict exists
- dirty/staged files outside allowed_files exist
- any source file outside the three Memory files is needed

# Index hygiene before committing

If Cockpit route-validation report artifacts are already staged, do not accidentally include them in the Memory commit.

Before committing Memory source/test changes:
- inspect `git diff --cached --name-status`
- if route-validation task/report artifacts are staged, unstage them with `git restore --staged <paths>` or equivalent index-only operation
- do not modify their file contents
- commit Memory files separately only after the staged set contains only:
  - cockpit-ui/app/memory/page.tsx
  - cockpit-ui/components/cockpit/memory/memory-screen.tsx
  - cockpit-ui/tests/memory.spec.ts
  - this task card/report artifacts only if the task-card/report commit is intentionally separate

# Phase A - classify Memory dirty changes

Inspect diffs for:

- cockpit-ui/app/memory/page.tsx
- cockpit-ui/components/cockpit/memory/memory-screen.tsx
- cockpit-ui/tests/memory.spec.ts

Classify each change:

- INTENTIONAL_SAFE_EXTENSION
- TEST_ONLY_ALIGNMENT
- BUG_FIX
- UNKNOWN_OWNER
- UNSAFE_OR_SCOPE_DRIFT
- DATA_MISSING

Determine:
- What behavior changed?
- Is this a Memory UI feature/fix/test alignment?
- Is it related to deep-linking, tab routing, unavailable states, source labels, confirmation gates, or visual layout?
- Does it mutate product memory or only UI/read behavior?
- Are tests added/updated to cover the behavior?
- Does it overlap the route-validation task or belong to separate Memory work?

# Phase B - validate Memory changes

Run only targeted safe checks. Prefer:

- pnpm -C cockpit-ui exec vitest run tests/memory.spec.ts
- pnpm -C cockpit-ui exec vitest run <specific unit/component test for memory-screen if present>
- pnpm -C cockpit-ui exec tsc --noEmit only if cheap and already standard; otherwise record not run
- git diff --check
- explicit path allowlist check

Do not run Playwright if it may click mutating controls unless the spec is clearly read-only and already mocked. If unsure, skip and report recommended validation.

If tests fail:
- do not patch broadly
- inspect whether failure is due current dirty change or stale expectation
- make minimal edits only within the three allowed Memory files if the fix is clearly in-scope
- otherwise stop BLOCKED

# Phase C - commit Memory changes only if safe

Commit Memory source/test changes only if all are true:

- dirty Memory files are classified as safe/intentional
- no unrelated files staged
- targeted validation passes or failures are explained and non-blocking only if test was unsuitable/stale
- git diff --check passes
- task report explains the behavior and validation

Stage only:
- cockpit-ui/app/memory/page.tsx
- cockpit-ui/components/cockpit/memory/memory-screen.tsx
- cockpit-ui/tests/memory.spec.ts
- docs/agent_tasks/memory_dirty_work_and_route_validation_closeout_20260513.md
- reports/agent_jobs/memory_dirty_work_and_route_validation_closeout_20260513/**

Suggested commit message if behavior is confirmed:
fix(memory): preserve memory screen navigation state

If that message is inaccurate, choose a precise commit message based on the actual diff, but keep it Memory-lane only.

If not safe:
- do not commit
- leave files as-is
- write report
- release registry claim
- final response BLOCKED with exact next action

# Phase D - commit Cockpit route-validation report artifacts separately

Only after Memory dirty files are clean or safely committed:

1. Stage only:
   - docs/agent_tasks/cockpit_route_validation_pass_v1_20260513.md
   - reports/agent_jobs/cockpit_route_validation_pass_v1_20260513/**

2. Validate:
   - git diff --cached --name-status
   - explicit allowlist:
     git diff --cached --name-only | rg -v '^(docs/agent_tasks/cockpit_route_validation_pass_v1_20260513\.md|reports/agent_jobs/cockpit_route_validation_pass_v1_20260513/)'
   - allowlist check must produce no output
   - python3 -m json.tool reports/agent_jobs/cockpit_route_validation_pass_v1_20260513/status.json >/dev/null
   - python3 -m json.tool reports/agent_jobs/cockpit_route_validation_pass_v1_20260513/diff-check.json >/dev/null || true
   - git diff --check
   - python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/cockpit_route_validation_pass_v1_20260513.md || document known report-glob limitation only if all rejected files are under the allowed report directory and no unrelated source files remain

3. Commit only if no application code is staged.

Commit message:
docs(reporting): record cockpit route validation pass

# Required report files

Write:

reports/agent_jobs/memory_dirty_work_and_route_validation_closeout_20260513/README.md
reports/agent_jobs/memory_dirty_work_and_route_validation_closeout_20260513/memory_dirty_file_classification.md
reports/agent_jobs/memory_dirty_work_and_route_validation_closeout_20260513/status.json

# README.md structure

1. Executive summary
   - what dirty files appeared
   - whether they were safe/unsafe
   - Memory commit result
   - route-validation report commit result
   - remaining blockers

2. Preflight
   - branch / HEAD
   - git status
   - staged files at start
   - registry claim
   - Chorus used/not used

3. Memory dirty-file classification
   Table:
   - file
   - classification
   - behavior changed
   - evidence
   - validation
   - action taken

4. Validation
   - exact commands
   - exact results
   - what each proves
   - what each does not prove

5. Commit separation
   - Memory commit files
   - Reporting commit files
   - proof that commits were not mixed

6. Route-validation closeout
   - whether task/report artifacts committed
   - check-diff result
   - report-glob limitation if applicable
   - final route-validation status

7. Risks / DATA_MISSING
   - any unknown owner
   - any failing tests
   - any dirty files remaining
   - any skipped tests

8. Next safe step
   - route smoke follow-up
   - UI test drift fixes
   - chat/news provenance smoke
   - extraction runtime audit

9. Project Memory save recommendation
   - SAVE_RECOMMENDED / CONSOLIDATE_EXISTING if commits land
   - SAVE_OPTIONAL if blocked without durable state

10. Final state
   - final git status
   - active jobs
   - registry release
   - commit hashes

# status.json structure

{
  "job_id": "memory_dirty_work_and_route_validation_closeout_20260513",
  "branch": "...",
  "start_head": "...",
  "end_head": "...",
  "mode": "audit_first_safe_extension",
  "collision_risk": "...",
  "chorus_used": true/false,
  "registry_claim": "acquired/failed/not_supported",
  "registry_release": "released/not_acquired/not_supported",
  "memory_files_classified": 3,
  "memory_commit_created": true/false,
  "memory_commit": "... or null",
  "route_validation_commit_created": true/false,
  "route_validation_commit": "... or null",
  "mutating_routes_probed": 0,
  "tests_run": [],
  "tests_passed": [],
  "tests_failed": [],
  "remaining_blockers": [],
  "next_safe_steps": []
}

# Final validation

Before finishing:

- git status --short --untracked-files=all
- python3 scripts/agent_job_registry.py list-active
- python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/cockpit_route_validation_pass_v1_20260513.md
- python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/cockpit_route_validation_pass_v1_20260513.md || explain report-glob limitation if applicable
- python3 -m json.tool reports/agent_jobs/memory_dirty_work_and_route_validation_closeout_20260513/status.json >/dev/null
- git diff --check

Release registry claim if acquired.
