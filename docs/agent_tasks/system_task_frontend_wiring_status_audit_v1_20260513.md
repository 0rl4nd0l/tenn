---
job_id: system_task_frontend_wiring_status_audit_v1_20260513
lane: Reporting
owner: Codex
allowed_files:
  - docs/agent_tasks/system_task_frontend_wiring_status_audit_v1_20260513.md
  - reports/agent_jobs/system_task_frontend_wiring_status_audit_v1_20260513/**
approval_required: false
timeout_seconds: 7200
output_dir: reports/agent_jobs/system_task_frontend_wiring_status_audit_v1_20260513
mutation_mode: audit_only
production_data_access: false
---

# Task

Run a full current-state audit of Tenn's repo/system/task/frontend wiring status.

This is audit-only. The only permitted writes are this task card and report artifacts under:

reports/agent_jobs/system_task_frontend_wiring_status_audit_v1_20260513/

Do not modify, format, stage, commit, revert, delete, move, or "quick-fix" any application code, config, data, UI file, backend file, test file, task file outside this task card, or existing report artifact outside the approved output directory.

# Required preflight

1. Print date/time and working directory.
2. Print branch, HEAD, short HEAD, upstream if any.
3. Run:
   - git status --short --untracked-files=all
   - git worktree list
   - git log --oneline --decorate -20
   - git branch --show-current
4. Identify whether AGENTS.md, CLAUDE.md, task-card tooling, hooks, registry, and active task marker files exist.
5. Validate this task card if repo tooling supports it.
6. Run registry/list-active if available.
7. Run registry/check-overlap for this task card if available.
8. If registry supports audit-only claim, claim this audit only and release it at the end.
9. Stop and report only if:
   - task card is invalid,
   - output_dir is rejected,
   - registry shows overlapping active ownership of the report path,
   - repo tooling says audit-only report-writing is unsafe,
   - or HIGH collision risk is confirmed.

# Audit scope

Produce a current, evidence-backed map of:

## A. Repo and task state

- Current branch/HEAD/upstream.
- Worktrees and likely active worktrees.
- Active registry jobs/locks if available.
- Existing task cards under docs/agent_tasks.
- Recent reports under reports/agent_jobs.
- Unreviewed or apparently incomplete reports.
- Dirty, untracked, deleted, ignored-but-relevant, or generated files.
- Which dirty/untracked files appear to belong to which lane/workstream.
- Which files are blocking check-diff or safe future implementation.
- Whether there are stale task cards, stale locks, stale reports, or superseded prompts.
- Current next-safe-step queue inferred from task cards/reports, clearly labelled Confirmed / Inferred / DATA_MISSING.

## B. Frontend / Cockpit wiring

Inspect Cockpit frontend code read-only. Build a complete wiring map of:

- App/router structure.
- All pages/routes/tabs visible in Cockpit.
- Layout/sidebar/nav ownership.
- Components used by each page/tab.
- BFF/API route files under cockpit-ui/app/api or equivalent.
- Client-side service/lib files used by pages/components.
- Environment variables/config expected by frontend.
- Backend endpoints called by each frontend page/tab.
- Whether calls are direct backend, BFF/proxy, mocked/static, stale/dead, feature-flagged, or DATA_MISSING.
- Loading/error/empty/degraded states per page/tab where visible in code.
- Source/provenance drawer, source labels, chat, marketplace, watchlist, home, verification/extraction eval, memory/workbench, thesis/audit, news/commentary, portfolio/holdings, settings/status/debug pages if present.
- Any pages/components that are visually present but not live-wired.
- Any backend endpoints that exist but have no frontend consumer.
- Any frontend API calls to missing backend routes.
- Any duplicated or conflicting route definitions.
- Any obvious stale mock data, placeholder labels, hardcoded fixtures, or "TODO later" areas that could mislead the user.

## C. Backend route ownership relevant to frontend

Inspect backend route/service code read-only. Map:

- FastAPI routes or Flask routes currently exposed.
- Routes used by Cockpit frontend.
- Routes referenced by docs but not frontend.
- Legacy routes still reachable.
- Backend services behind major UI actions.
- Evidence/provenance/source-label route paths.
- Query/chat/orchestrator route paths.
- News/RAG/marketplace/watchlist/portfolio/extraction eval/memory-related route paths.
- Health/status/runtime endpoints.
- Any route contract mismatch between frontend types and backend response models.
- Any endpoint with missing tests, stale tests, or failing import/test collection risks.

## D. Runtime and validation status

Do not start heavy workloads. Do not mutate data.

If services are already running, you may perform read-only GET probes only against health/status endpoints. Do not POST unless the endpoint is clearly read-only and safe, and record why.

Audit:

- Known ports from code/docs/scripts.
- How Cockpit is started.
- How backend is started.
- How local LLM runtimes are configured.
- Whether frontend expects backend, backend expects LLM, and extraction expects separate runtime.
- Current test scripts and package scripts.
- Last known validation from recent reports.
- Which validations are fresh vs stale.
- Whether TypeScript/Vitest/Playwright/Python tests appear available.
- Whether running lightweight non-mutating checks is safe.

Permitted lightweight validation if safe and scoped:
- git diff --check
- task-card check-diff for this task
- static grep/ripgrep inventory
- package script listing
- pytest/vitest collection-only if it is known not to mutate
- typecheck/test commands only if clearly safe and not likely to trigger runtime/data jobs; otherwise list them as recommended next validation, not run

## E. Architecture and truth-boundary risks

Classify risks around:

- Frontend displaying mock/static data as live.
- Frontend bypassing backend ownership.
- Cockpit calling Qdrant/database/LLM directly if found.
- Query/chat routes bypassing QueryOrchestrator or evidence-envelope semantics.
- Source labels overstating verification.
- Holdings/local personal data being mixed with financial truth.
- News/RAG evidence gaps.
- Extraction verification UI disconnects from canonical truth.
- Memory/thesis contamination risks.
- Any UI route that suggests a capability Tenn cannot actually perform yet.

# Required inspection targets

Read-only inspect likely files/directories if present:

- AGENTS.md
- CLAUDE.md
- README.md
- HANDOFF.md
- docs/architecture/**
- docs/agent_tasks/**
- reports/agent_jobs/**
- scripts/agent_job_contract.py
- scripts/agent_job_registry.py
- .codex/**
- .claude/**
- cockpit-ui/**
- financial-engine_v2/backend/**
- backend/**
- scripts/**
- tests/**
- package.json
- pnpm-lock.yaml / package-lock.json if present
- docker-compose* if present
- Makefile / justfile / task scripts if present
- config/env/example files, without printing secrets

Do not print secrets or full env files. Redact tokens, API keys, credentials, cookies, database passwords, or personal data.

# Suggested read-only commands

Use judgment. Prefer targeted commands.

- pwd
- date -Iseconds
- git rev-parse --show-toplevel
- git rev-parse --abbrev-ref HEAD
- git rev-parse HEAD
- git rev-parse --short=12 HEAD
- git status --short --untracked-files=all
- git worktree list
- git log --oneline --decorate -20
- find docs/agent_tasks -maxdepth 1 -type f | sort
- find reports/agent_jobs -maxdepth 2 -type f | sort
- rg -n "TODO|FIXME|mock|placeholder|stub|not wired|source-backed|evidence_envelope|QueryOrchestrator|/api/|fetch\\(|axios|POST|GET" cockpit-ui financial-engine_v2/backend backend docs scripts tests
- find cockpit-ui -maxdepth 5 -type f | sort
- find financial-engine_v2/backend -maxdepth 6 -type f | sort
- cat package.json if present
- pnpm --version if present
- python3 --version
- python3 scripts/agent_job_contract.py validate docs/agent_tasks/system_task_frontend_wiring_status_audit_v1_20260513.md, if supported
- python3 scripts/agent_job_registry.py list-active, if supported
- python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/system_task_frontend_wiring_status_audit_v1_20260513.md, if supported
- git diff --check
- python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/system_task_frontend_wiring_status_audit_v1_20260513.md, if supported

# Hard boundaries

Do not:
- edit application code
- edit existing task cards other than creating this task card if absent
- edit existing reports outside the approved output dir
- stage or commit anything
- run migrations
- run ingestion/backfill/news sync/Qdrant sync
- run extraction jobs
- run parser/gold-label changes
- run data cleanup
- run browser automation that clicks mutating controls
- change environment variables
- change ports
- start/stop production-like services
- touch financial truth data
- touch company memory, market memory, thesis memory, holdings, user data, or local personal state
- make architecture changes
- decide implementation direction without marking it as recommendation only

# Report artifacts required

Write these report files:

1. reports/agent_jobs/system_task_frontend_wiring_status_audit_v1_20260513/README.md
   Main executive audit.

2. reports/agent_jobs/system_task_frontend_wiring_status_audit_v1_20260513/frontend_wiring_map.md
   Full frontend page/tab/component/BFF/backend endpoint map.

3. reports/agent_jobs/system_task_frontend_wiring_status_audit_v1_20260513/task_status_matrix.md
   Task-card/report/registry/dirty-work matrix.

4. reports/agent_jobs/system_task_frontend_wiring_status_audit_v1_20260513/risk_register.md
   Risks sorted P0/P1/P2/P3 with owner lane and next safe step.

5. reports/agent_jobs/system_task_frontend_wiring_status_audit_v1_20260513/validation_matrix.md
   Tests/checks discovered, last known result, run/not-run reason, freshness, what each proves/does not prove.

6. reports/agent_jobs/system_task_frontend_wiring_status_audit_v1_20260513/status.json
   Machine-readable summary with:
   - job_id
   - branch
   - head
   - mode
   - collision_risk
   - active_jobs_count_or_DATA_MISSING
   - dirty_files_count
   - frontend_routes_count
   - backend_routes_count
   - bff_routes_count
   - live_wired_routes_count
   - mock_or_static_routes_count
   - missing_backend_routes_count
   - validation_run_count
   - blockers
   - next_safe_steps

# README.md required structure

Use this exact structure:

1. Executive summary
   - Current repo status
   - Current task/agent status
   - Current frontend wiring status
   - Top blockers
   - Recommended next safe step

2. Evidence status legend
   - Confirmed
   - Inferred
   - Speculative
   - DATA_MISSING

3. Preflight evidence
   - branch / HEAD
   - worktrees
   - git status
   - registry/list-active result
   - task-card validation result
   - check-overlap result
   - final collision risk

4. Active / recent task status
   - table: job_id, lane, task card, report dir, status, evidence, reviewed?, next action

5. Dirty/untracked/deleted work classification
   - table: path, status, likely lane, owner/workstream, generated/intentional/stale/DATA_MISSING, blocks what?, recommended treatment, confidence

6. Frontend route/tab inventory
   - table: frontend route/tab, primary files, components, BFF/API calls, backend owner route, data mode live/mock/static/DATA_MISSING, tests, risks

7. BFF/API wiring inventory
   - table: BFF/frontend API route, backend endpoint, request/response contract evidence, status, mismatch risk

8. Backend route inventory relevant to Cockpit
   - table: backend route, service owner, frontend consumers, tests, provenance/source-label behavior, status

9. Page-by-page Cockpit UX/wiring notes
   For each visible page/tab:
   - intended purpose inferred from code/docs
   - actual wired data path
   - what appears live
   - what appears mocked/static/stale
   - loading/error/degraded states
   - missing tests
   - user-facing risk

10. Source/provenance/evidence behavior
   - evidence envelope paths
   - source drawer/source list paths
   - no-hit/degraded/local-personal-data handling if inspectable
   - overstatement risks

11. Runtime/dependency/port map
   - frontend
   - backend
   - LLM runtime(s)
   - extraction runtime(s)
   - Qdrant/DB/news/embeddings dependencies
   - what was actually verified vs inferred

12. Validation matrix summary
   - checks run with exact outputs
   - checks not run and why
   - stale validation evidence
   - recommended next validation pass

13. Risks and blockers
   Sort P0/P1/P2/P3.
   For each:
   - risk
   - evidence
   - impacted lane/surface
   - likely root cause or DATA_MISSING
   - next safe step
   - hard stop if any

14. Recommended next safe steps
   Provide a sequenced list:
   - audit-only follow-up(s)
   - safe-extension candidates
   - implementation candidates
   - cleanup/hygiene candidates
   Do not recommend broad implementation before dirty/task/registry risks are resolved.

15. Project Memory save recommendation
   Classify as SAVE_REQUIRED / SAVE_RECOMMENDED / SAVE_OPTIONAL / NO_SAVE / CONSOLIDATE_EXISTING.
   Name target categories:
   - Active Tasks / Todos
   - Open Risks / Blockers
   - Repo / GitHub / Codex Audit Notes
   - Validation Baselines
   - Milestones if applicable

16. Final state
   - final git status
   - files written by this audit
   - registry claim released or DATA_MISSING
   - task-card check-diff result
   - DATA_MISSING list

# Classification rules

Label every important claim as one of:
- Confirmed: directly observed in repo command output, file content, or report artifact.
- Inferred: likely based on multiple pieces of evidence, but not directly proven.
- Speculative: plausible but weak evidence.
- DATA_MISSING: not proven or not inspectable.

Do not present old Project Memory, comments, docs, or stale reports as current truth unless verified against current repo state.

# Definition of done

- Task card exists or is validated.
- Registry/list-active and check-overlap were attempted if tooling exists.
- No application code changed.
- No data/runtime mutation performed.
- Report files written only under approved output_dir.
- Frontend wiring map includes every discovered Cockpit page/tab/API/BFF route.
- Task status matrix includes active/recent task cards and reports.
- Dirty/untracked/deleted work classified.
- Backend route ownership relevant to frontend mapped.
- Validation status summarized with exact commands/results or not-run reasons.
- Risks sorted by severity with lane owner and next safe step.
- Final git status recorded.
- Registry claim released if one was created.
