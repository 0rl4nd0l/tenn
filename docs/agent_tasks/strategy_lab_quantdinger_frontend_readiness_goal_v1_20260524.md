---
job_id: strategy_lab_quantdinger_frontend_readiness_goal_v1_20260524
lane: Reporting
owner: Codex
supporting_lanes:
  - Query Orchestration
  - Provenance
  - Evaluation
mutation_mode: safe_extension
approval_required: false
allow_unapproved_safe_extension: true
production_data_access: false
timeout_seconds: 7200
output_dir: reports/agent_jobs/strategy_lab_quantdinger_frontend_readiness_goal_v1_20260524
allowed_files:
  - docs/agent_tasks/strategy_lab_quantdinger_frontend_readiness_goal_v1_20260524.md
  - reports/agent_jobs/strategy_lab_quantdinger_frontend_readiness_goal_v1_20260524/README.md
  - reports/agent_jobs/strategy_lab_quantdinger_frontend_readiness_goal_v1_20260524/status.json
  - reports/agent_jobs/strategy_lab_quantdinger_frontend_readiness_goal_v1_20260524/diff-check.json
  - cockpit-ui/app/api/cockpit/strategy-lab/status/route.ts
  - cockpit-ui/components/cockpit/home/home-page.tsx
  - cockpit-ui/components/cockpit/home/cards/strategy-lab-status-card.tsx
  - cockpit-ui/components/cockpit/home/cards/strategy-lab-status-card.test.tsx
  - cockpit-ui/lib/strategy-lab-status.ts
  - cockpit-ui/lib/strategy-lab-status-server.ts
  - cockpit-ui/lib/strategy-lab-status.test.ts
---

# Strategy Lab / QuantDinger Frontend Readiness Goal v1

## Objective

Determine whether QuantDinger / Strategy Lab is live or functional in the Cockpit frontend. If it is not live, make the smallest safe read-only Cockpit-facing Strategy Lab / QuantDinger status surface possible using existing baseline artifacts and contracts.

## Preconditions

- Confirm `/home/l4nd0/tenn` and its symlink target before relying on repo state.
- Report branch, HEAD, `git status --short --untracked-files=all`, and `git worktree list`.
- Validate this task card before inspecting or editing implementation files.
- Run registry `list-active` and `check-overlap` before any implementation.
- Confirm whether `e170f6b255ca4229462d4167861775e82ea3df34` is an ancestor of `HEAD`.
- Stop at audit-only reporting if the task card is invalid, registry overlap is active, HIGH collision appears, unrelated dirty work is present, or ownership is unclear.

## Scope

Audit Strategy Lab / QuantDinger frontend, BFF/API, docs, tests, reports, sidecar artifacts, mock transport, artifact schema, Cockpit routes, tabs, and cards. Classify evidence as Confirmed, Inferred, or DATA_MISSING.

If preflight is clean, implement one minimal read-only Cockpit-facing vertical slice that honestly reports pending-review state, available artifacts, what is and is not live, and next safe actions. The surface must not create trading functionality, broker integration, runtime execution, canonical financial truth, or any production data writes.

## Forbidden Surfaces

- No trading, broker, paper/live execution, token issuance, real market orders, or portfolio mutation.
- No Tenn DB, Qdrant, news, memory, financial-truth, parser-routing, extraction, canonical metric, gold-label, runtime/model/GPU config, or service startup changes.
- No dependency installation.
- No broad Cockpit redesign.
- No deletion or cleanup of unrelated dirty work.
- No claims that mock artifacts are live functionality.

## Allowed Files

- `docs/agent_tasks/strategy_lab_quantdinger_frontend_readiness_goal_v1_20260524.md`
- `reports/agent_jobs/strategy_lab_quantdinger_frontend_readiness_goal_v1_20260524/README.md`
- `reports/agent_jobs/strategy_lab_quantdinger_frontend_readiness_goal_v1_20260524/status.json`
- `reports/agent_jobs/strategy_lab_quantdinger_frontend_readiness_goal_v1_20260524/diff-check.json`
- `cockpit-ui/app/api/cockpit/strategy-lab/status/route.ts`
- `cockpit-ui/components/cockpit/home/home-page.tsx`
- `cockpit-ui/components/cockpit/home/cards/strategy-lab-status-card.tsx`
- `cockpit-ui/components/cockpit/home/cards/strategy-lab-status-card.test.tsx`
- `cockpit-ui/lib/strategy-lab-status.ts`
- `cockpit-ui/lib/strategy-lab-status-server.ts`
- `cockpit-ui/lib/strategy-lab-status.test.ts`

These implementation files were added after audit found no Cockpit UI entrypoint for Strategy Lab / QuantDinger and identified a minimal read-only Home status card plus status route/test surface. Re-run task-card validation and registry overlap checks after this allowlist expansion and before editing implementation files.

## Validation

- Validate this task card.
- Run registry `check-overlap`.
- Run `git diff --check`.
- Run task-card `check-diff` if supported.
- Run focused frontend TypeScript, ESLint, and/or Vitest checks if Cockpit frontend files change and the commands are available without starting prohibited services.
- Run focused backend/BFF unit tests if backend/BFF files change.
- Validate report/status JSON artifacts.
- Report DATA_MISSING for unavailable checks with the reason.

## Deliverables

- `reports/agent_jobs/strategy_lab_quantdinger_frontend_readiness_goal_v1_20260524/README.md`
- `reports/agent_jobs/strategy_lab_quantdinger_frontend_readiness_goal_v1_20260524/status.json`

Both deliverables must include branch/HEAD before and after, task-card validation, registry state, files inspected, files changed, frontend live/functioning verdict, implementation summary if any, tests/checks with exact results, DATA_MISSING, forbidden surfaces not touched, remaining risks, next safe tasks, git status, and save recommendation.
