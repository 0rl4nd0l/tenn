---
job_id: strategy_lab_artifact_review_value_layer_v1_20260524
lane: Reporting
owner: Codex
supporting_lanes:
  - Provenance
  - Query Orchestration
  - Evaluation
mutation_mode: safe_extension
approval_required: false
allow_unapproved_safe_extension: true
production_data_access: false
timeout_seconds: 7200
output_dir: reports/agent_jobs/strategy_lab_artifact_review_value_layer_v1_20260524
allowed_files:
  - docs/agent_tasks/strategy_lab_artifact_review_value_layer_v1_20260524.md
  - docs/agent_tasks/strategy_lab_quantdinger_sidecar_smoke_readonly_plan_v1_20260524.md
  - reports/agent_jobs/strategy_lab_artifact_review_value_layer_v1_20260524/README.md
  - reports/agent_jobs/strategy_lab_artifact_review_value_layer_v1_20260524/status.json
  - reports/agent_jobs/strategy_lab_artifact_review_value_layer_v1_20260524/validation.json
  - reports/agent_jobs/strategy_lab_artifact_review_value_layer_v1_20260524/diff-check.json
  - cockpit-ui/app/api/cockpit/strategy-lab/status/route.ts
  - cockpit-ui/app/api/cockpit/strategy-lab/artifacts/route.ts
  - cockpit-ui/components/cockpit/home/home-page.tsx
  - cockpit-ui/components/cockpit/home/cards/strategy-lab-status-card.tsx
  - cockpit-ui/components/cockpit/home/cards/strategy-lab-status-card.test.tsx
  - cockpit-ui/components/cockpit/home/cards/strategy-lab-artifacts-review-card.tsx
  - cockpit-ui/components/cockpit/home/cards/strategy-lab-artifacts-review-card.test.tsx
  - cockpit-ui/lib/strategy-lab-status.ts
  - cockpit-ui/lib/strategy-lab-status-server.ts
  - cockpit-ui/lib/strategy-lab-status.test.ts
  - cockpit-ui/lib/strategy-lab-artifacts.ts
  - cockpit-ui/lib/strategy-lab-artifacts-server.ts
  - cockpit-ui/lib/strategy-lab-artifacts.test.ts
  - tests/strategy_lab/test_strategy_lab_mocked_adapter_phase3b_reconciled.py
  - tests/strategy_lab/test_strategy_lab_offline_mock_transport_phase3c.py
---

# Strategy Lab Artifact Review Value Layer v1

## Objective

Make the Cockpit Strategy Lab / QuantDinger surface more useful without
presenting it as live trading, paper trading, real transport, canonical
financial truth, or a store-writing system.

## Preconditions

- Confirm `/home/l4nd0/tenn` symlink and realpath, branch, HEAD, `git status`,
  and worktrees.
- Validate this task card before implementation.
- Run registry `list-active` and `check-overlap`.
- Confirm `0211a5b46091cd4858e402d10e3499a1e96819ab` is an ancestor of `HEAD`.
- Treat `docs/agent_tasks/task_card_dirt_hygiene_v1_20260524.md` as separately
  handled and do not modify it.
- Stop or downgrade to report-only on HIGH collision, active overlapping
  registry job, invalid card, uncontained dirty files, forbidden-surface
  pressure, or unclear ownership.

## Phase 1 Audit

Inspect existing Strategy Lab / QuantDinger docs, artifacts, fixtures, reports,
Cockpit status card, status route, and tests. Classify:

- artifact files that can be read safely from repo fixtures/reports only
- `strategy_lab_artifact_v1` evidence versus helper or pre-envelope evidence
- metadata that can be shown honestly
- fields that must remain `DATA_MISSING`
- the smallest Cockpit surface for artifact review

## Phase 2 Wording Fix

If safe, update the landed Strategy Lab status card so visible labels include:

- `PENDING REVIEW`
- `READ ONLY`
- `NO LIVE TRADING`
- `NO PAPER TRADING`
- `NO REAL TRANSPORT`
- `NO CANONICAL FINANCIAL TRUTH`
- `NO STORE WRITES`
- `DATA_MISSING`

## Phase 3 Read-Only Artifact Review

If safe, add the smallest repo-only review surface for existing Strategy Lab
artifacts:

- a read-only `GET /api/cockpit/strategy-lab/artifacts` route or equivalent
- a small Cockpit section/list showing artifact type, review status,
  source/report path, what it proves, what it does not prove, and
  `DATA_MISSING`
- strict repo fixture/report reads only
- helper or pre-envelope evidence labeled as non-authoritative if shown

## Phase 4 Follow-Up Planning Only

If the artifact review slice validates cleanly, draft a separate approval-gated
non-mock QuantDinger sidecar smoke task card. Do not implement real transport
in this task.

## Forbidden

- No trading, broker, paper/live execution, token issuance, market orders, or
  portfolio mutation.
- No Tenn DB, Qdrant, news, memory, canonical financial truth, artifact-store,
  promotion, parser, extraction, gold-label, runtime, model, GPU, dependency, or
  service changes.
- No real QuantDinger transport/client unless a later task explicitly approves
  it.
- No cleanup of unrelated hygiene work.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/strategy_lab_artifact_review_value_layer_v1_20260524.md --write-report`
- `python3 scripts/agent_job_registry.py list-active`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/strategy_lab_artifact_review_value_layer_v1_20260524.md --repo-root .`
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/strategy_lab_artifact_review_value_layer_v1_20260524.md --repo-root .`
- status/report JSON parse
- focused Strategy Lab Vitest
- targeted ESLint
- `tsc --noEmit`
- existing Strategy Lab Python unittests
- browser smoke if safe without installs or store mutation

## Deliverables

- `reports/agent_jobs/strategy_lab_artifact_review_value_layer_v1_20260524/README.md`
- `reports/agent_jobs/strategy_lab_artifact_review_value_layer_v1_20260524/status.json`

The final report must include before/after branch and HEAD, files inspected and
changed, whether artifact review is user-visible, what remains mock/repo-only,
exact validation results, `DATA_MISSING`, forbidden surfaces not touched,
remaining risks, next safe tasks, git status, and save recommendation.
