---
job_id: cockpit_route_validation_pass_v1_20260513
lane: Reporting
owner: Codex
allowed_files:
  - docs/agent_tasks/cockpit_route_validation_pass_v1_20260513.md
  - reports/agent_jobs/cockpit_route_validation_pass_v1_20260513/**
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/cockpit_route_validation_pass_v1_20260513
mutation_mode: safe_extension
production_data_access: false
---

# Task

Run a read-only Cockpit route validation pass and preserve the report artifacts.

Allowed writes:
- this task card
- reports under reports/agent_jobs/cockpit_route_validation_pass_v1_20260513/

Do not edit application code, tests, config, source files, package files, data stores, or runtime settings.

# Hard boundaries

Do not run or click:
- mutating POST routes unless explicitly proven to be harmless and approved by this task
- Operations restart
- model load/reload
- action execute
- extraction eval POST/background jobs
- Marketplace scan/sync/calibration/eBay refresh
- memory writes/add/expire
- thesis proposal apply/confirm
- feedback deploy/investigation spawn
- ingestion/backfill/Qdrant sync
- migrations
- parser/gold-label changes
- browser automation that may click mutating controls

Read-only GET probes are allowed for:
- health/status/config/model list where safe
- BFF GET routes
- backend GET health endpoints
- static route/page existence checks
- curl HEAD/GET against local Cockpit pages if already running
- selected unit tests that do not mutate runtime/data

# Required preflight

Run and record:

- date -Iseconds
- pwd
- git rev-parse --show-toplevel
- git branch --show-current
- git rev-parse HEAD
- git rev-parse --short=12 HEAD
- git status --short --untracked-files=all
- git worktree list
- git log --oneline --decorate -12
- python3 scripts/agent_job_contract.py validate docs/agent_tasks/cockpit_route_validation_pass_v1_20260513.md
- python3 scripts/agent_job_registry.py list-active
- python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/cockpit_route_validation_pass_v1_20260513.md
- python3 scripts/agent_job_registry.py claim docs/agent_tasks/cockpit_route_validation_pass_v1_20260513.md

Stop if:
- task card validation fails
- registry shows overlapping active work
- git status has unrelated dirty/untracked files
- claim cannot be acquired
- safe_extension would require application-code edits

# Inputs to inspect

Read, do not modify:

- reports/agent_jobs/system_task_frontend_wiring_status_audit_v1_20260513/README.md
- reports/agent_jobs/system_task_frontend_wiring_status_audit_v1_20260513/frontend_wiring_map.md
- reports/agent_jobs/system_task_frontend_wiring_status_audit_v1_20260513/risk_register.md
- reports/agent_jobs/system_task_frontend_wiring_status_audit_v1_20260513/validation_matrix.md
- cockpit-ui/app/**
- cockpit-ui/components/**
- cockpit-ui/lib/**
- cockpit-ui/next.config.mjs
- cockpit-ui/package.json
- financial-engine_v2/backend/app/routes/**
- financial-engine_v2/backend/app/services/**
- relevant backend tests only for discovery, not editing

# Validation focus

Validate these Cockpit surfaces read-only:

1. Overview/Home
   - page route exists
   - BFF route exists
   - GET /api/cockpit/home safe probe if running
   - verify degraded/DATA_MISSING handling from code/tests
   - no mock fallback presented as source-backed

2. Chat
   - page route exists
   - route ownership map for /api/cockpit/chat vs /chat vs /api/chat
   - do not run chat POST unless explicitly read-only and cheap; default is no POST
   - validate source/provenance contract from code/tests only

3. Watchlist/Holdings
   - page routes exist
   - GET/list routes only if safe
   - confirm holdings use local_personal_data semantics
   - do not mutate holdings/watchlist

4. Marketplace
   - page routes exist
   - read-only GET routes only
   - do not scan/sync/refresh/calibrate
   - classify which routes are mutating and should need explicit operator gate

5. News/RAG
   - page route exists
   - /rag/query wiring confirmed from code
   - avoid POST query unless explicitly judged safe; default no POST
   - classify DATA_MISSING for runtime response quality if not probed

6. Memory/Thesis Audit
   - page routes exist
   - BFF/context route ownership mapped
   - do not write memory or apply thesis proposals
   - classify confirmation-gate risks

7. Verification/Extraction Eval
   - page route exists
   - extraction eval endpoints mapped
   - no background eval POST
   - record 8001/8002 ambiguity as separate follow-up, not fixed here

8. Settings/Operations/Boot
   - page routes exist
   - health/config/model list GET only if safe
   - do not restart or load models
   - classify mutating controls and required future gate

# Test command policy

You may run selected non-mutating tests if safe:

Preferred:
- pnpm -C cockpit-ui exec vitest run <specific Home/contract/route test files if identifiable>
- selected backend pytest collection-only for route imports if safe
- curl GET local health/page routes only if services already running
- git diff --check
- JSON validation for report status

Do not run broad Playwright unless it is clearly read-only and cannot click mutating controls.
Do not run full backend test suite if it may start jobs or touch data.
If unsure, record recommended validation instead of running it.

# Required report files

Write:

reports/agent_jobs/cockpit_route_validation_pass_v1_20260513/README.md
reports/agent_jobs/cockpit_route_validation_pass_v1_20260513/route_validation_matrix.md
reports/agent_jobs/cockpit_route_validation_pass_v1_20260513/mutating_route_gate_list.md
reports/agent_jobs/cockpit_route_validation_pass_v1_20260513/status.json

# README.md required structure

1. Executive summary
   - what was validated
   - what passed
   - what was not run and why
   - top risks
   - next safe step

2. Preflight
   - branch / HEAD
   - git status
   - worktrees
   - registry claim
   - Chorus used/not used

3. Validation scope
   - pages/routes included
   - pages/routes excluded
   - why excluded

4. Route health summary
   Table:
   - surface
   - frontend page
   - BFF/API path
   - backend target
   - validation method
   - result
   - evidence
   - risk

5. Page-by-page findings
   For each surface:
   - route ownership
   - live/mock/static/DATA_MISSING
   - safe GET result if run
   - tests found/run
   - user-facing risk
   - next safe step

6. Mutating route gate list
   - route/control
   - owning surface
   - why mutating
   - future validation gate required
   - operator approval needed? yes/no

7. Source/provenance findings
   - source label semantics
   - degraded/no-hit/local_personal_data handling
   - DATA_MISSING if not runtime-probed

8. Validation commands
   - exact command
   - exact result
   - what it proves
   - what it does not prove

9. DATA_MISSING
   - unprobed POST routes
   - runtime-dependent behavior
   - stale tests
   - extraction runtime ambiguity
   - any incomplete route contract

10. Recommended next steps
   Split into:
   - immediate no-code validation
   - safe-extension candidates
   - implementation candidates
   - separate-lane follow-ups

11. Project Memory save recommendation
   Classify:
   - SAVE_RECOMMENDED / CONSOLIDATE_EXISTING unless no new durable state
   Target categories:
   - Validation Baselines
   - Open Risks / Blockers
   - Repo / GitHub / Codex Audit Notes
   - Active Tasks / Todos if follow-ups are created

12. Final state
   - files written
   - final git status
   - registry release status
   - commit hash if committed

# route_validation_matrix.md

Create a table with at least:

- Overview/Home
- Chat
- Watchlist
- Holdings
- Marketplace Missions
- Marketplace Matches
- Marketplace Alerts
- News
- Memory
- Thesis Audit
- Verification
- Operations
- Settings
- Boot
- Intel Pulse
- History

Columns:
- surface
- frontend route
- primary files
- BFF/API route
- backend route/service
- validation run
- result
- live/mock/static/DATA_MISSING
- mutating risk
- tests discovered
- follow-up

# mutating_route_gate_list.md

List all routes/controls discovered that should require explicit future operator approval before tests/probes.

# status.json

Use this structure:

{
  "job_id": "cockpit_route_validation_pass_v1_20260513",
  "branch": "...",
  "head": "...",
  "mode": "safe_extension_validation_only",
  "collision_risk": "...",
  "chorus_used": true/false,
  "registry_claim": "acquired/failed/not_supported",
  "registry_release": "released/not_acquired/not_supported",
  "surfaces_validated": number,
  "safe_get_probes_run": number,
  "test_commands_run": number,
  "mutating_routes_probed": 0,
  "routes_passing": number,
  "routes_data_missing": number,
  "routes_blocked_or_deferred": number,
  "commit_created": true/false,
  "commit": "... or null",
  "remaining_blockers": [],
  "next_safe_steps": []
}

# Commit policy

After writing reports:

1. Validate:
   - python3 -m json.tool reports/agent_jobs/cockpit_route_validation_pass_v1_20260513/status.json >/dev/null
   - git diff --check
   - git status --short --untracked-files=all

2. Stage only:
   - docs/agent_tasks/cockpit_route_validation_pass_v1_20260513.md
   - reports/agent_jobs/cockpit_route_validation_pass_v1_20260513/**

3. Validate staged set:
   - git diff --cached --name-status
   - explicit path allowlist check:
     git diff --cached --name-only | rg -v '^(docs/agent_tasks/cockpit_route_validation_pass_v1_20260513\.md|reports/agent_jobs/cockpit_route_validation_pass_v1_20260513/)'
   - the allowlist check must produce no output
   - python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/cockpit_route_validation_pass_v1_20260513.md || document known report-glob limitation if only report artifacts under allowed output_dir are rejected
   - git diff --check

4. Commit only if:
   - no application code is staged
   - staged files are only task/report artifacts
   - JSON is valid
   - git diff --check passes
   - any check-diff failure is only the known report-glob limitation and the explicit path allowlist passes

Commit message:
docs(reporting): record cockpit route validation pass

5. Release registry claim if acquired.

6. Post-commit validation:
   - git status --short --untracked-files=all
   - python3 scripts/agent_job_registry.py list-active
   - python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/cockpit_route_validation_pass_v1_20260513.md
   - python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/cockpit_route_validation_pass_v1_20260513.md || document report-glob limitation if applicable

# Definition of done

Done when:

- task card validates
- registry claim acquired or safe explanation if unavailable
- read-only validation pass completed
- no mutating routes probed
- report artifacts written
- task/report artifacts committed or safely blocked with explanation
- registry released if claimed
- final git status recorded
- next safe step is explicit
