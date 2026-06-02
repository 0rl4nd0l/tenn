---
job_id: cockpit_strategy_lab_repo_artifact_route_guard_v1_20260602
lane: Reporting
owner: Codex
allowed_files:
  - docs/agent_tasks/cockpit_strategy_lab_repo_artifact_route_guard_v1_20260602.md
  - cockpit-ui/app/api/cockpit/strategy-lab/status/route.ts
  - cockpit-ui/app/api/cockpit/strategy-lab/artifacts/route.ts
  - cockpit-ui/components/cockpit/home/cards/strategy-lab-status-card.tsx
  - cockpit-ui/components/cockpit/home/cards/strategy-lab-artifacts-review-card.tsx
  - cockpit-ui/components/cockpit/home/cards/strategy-lab-status-card.test.tsx
  - cockpit-ui/components/cockpit/home/cards/strategy-lab-artifacts-review-card.test.tsx
  - cockpit-ui/lib/strategy-lab-status.test.ts
  - cockpit-ui/lib/strategy-lab-artifacts.test.ts
  - cockpit-ui/lib/cockpit-bff-auth.ts
  - cockpit-ui/lib/cockpit-api-headers.ts
  - reports/agent_jobs/cockpit_strategy_lab_repo_artifact_route_guard_v1_20260602/README.md
  - reports/agent_jobs/cockpit_strategy_lab_repo_artifact_route_guard_v1_20260602/status.json
  - reports/agent_jobs/cockpit_strategy_lab_repo_artifact_route_guard_v1_20260602/validation.json
  - reports/agent_jobs/cockpit_strategy_lab_repo_artifact_route_guard_v1_20260602/diff-check.json
approval_required: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/cockpit_strategy_lab_repo_artifact_route_guard_v1_20260602
mutation_mode: safe_extension
production_data_access: false
---

# Task

Gate Strategy Lab status and artifact-review BFF routes before exposing repo evidence.

# Context

GitHub issue #238 reports that `/api/cockpit/strategy-lab/status` and `/api/cockpit/strategy-lab/artifacts` read repo evidence and return Strategy Lab/QuantDinger proof metadata without checking the operator API key. This branch is stacked on PR #268 to reuse the focused Cockpit BFF auth and browser header helpers.

# Requirements

1. Validate this task card before implementation.
2. Inspect the shared active-job registry and open PR overlap before edits.
3. Claim this task if no unresolved overlap remains.
4. Require a configured Cockpit API key before `/api/cockpit/strategy-lab/status` returns repo-backed Strategy Lab status evidence.
5. Require a configured Cockpit API key before `/api/cockpit/strategy-lab/artifacts` reads repo artifacts or report evidence.
6. Preserve authenticated Cockpit Home card loading by sending the configured browser/operator key.
7. Keep Strategy Lab truth boundaries unchanged: `current_sidecar_available=false`, pending review, read-only, no trading, no canonical financial truth, no store writes.
8. Do not start/probe/mutate Strategy Lab or QuantDinger runtime.
9. Do not mutate repo artifacts, reports outside this task output, production DB, Qdrant, memory stores, canonical financial truth, parser prompts, gold labels, or runtime config.
10. Do not broaden into Home layout issue #42 or Strategy Lab workflow issue #76/#183.

# Validation

Run focused Cockpit UI route/component tests for Strategy Lab access guard and browser key propagation, then targeted ESLint and TypeScript for touched files.

# Required Output

Write a report to `reports/agent_jobs/cockpit_strategy_lab_repo_artifact_route_guard_v1_20260602/README.md` with:

- patch summary
- issue and PR/registry overlap evidence
- validation commands and results
- files intentionally not touched
- remaining blockers or follow-up work
