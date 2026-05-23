---
job_id: strategy_lab_offline_implementation_plan_phase3e_v1_20260521
lane: Query Orchestration
owner: Codex
mutation_mode: audit_only
approval_required: false
allow_audit_code_changes: true
production_data_access: false
timeout_seconds: 7200
output_dir: reports/agent_jobs/strategy_lab_offline_implementation_plan_phase3e_v1_20260521

allowed_files:
  - docs/agent_tasks/strategy_lab_offline_implementation_plan_phase3e_v1_20260521.md
  - reports/agent_jobs/strategy_lab_offline_implementation_plan_phase3e_v1_20260521/
  - reports/agent_jobs/strategy_lab_offline_implementation_plan_phase3e_v1_20260521/README.md
  - reports/agent_jobs/strategy_lab_offline_implementation_plan_phase3e_v1_20260521/preflight.md
  - reports/agent_jobs/strategy_lab_offline_implementation_plan_phase3e_v1_20260521/input_inventory.md
  - reports/agent_jobs/strategy_lab_offline_implementation_plan_phase3e_v1_20260521/worktree_consolidation_readiness.md
  - reports/agent_jobs/strategy_lab_offline_implementation_plan_phase3e_v1_20260521/offline_implementation_plan.md
  - reports/agent_jobs/strategy_lab_offline_implementation_plan_phase3e_v1_20260521/future_phase_map.md
  - reports/agent_jobs/strategy_lab_offline_implementation_plan_phase3e_v1_20260521/risk_and_hard_stops.md
  - reports/agent_jobs/strategy_lab_offline_implementation_plan_phase3e_v1_20260521/go_no_go_next.md
  - reports/agent_jobs/strategy_lab_offline_implementation_plan_phase3e_v1_20260521/status.json
  - reports/agent_jobs/strategy_lab_offline_implementation_plan_phase3e_v1_20260521/diff-check.json
---

# Strategy Lab Offline Implementation Plan Phase 3E

## Objective

Run Phase 3E Strategy Lab offline implementation-plan-only work for
QuantDinger/Tenn, starting with a consolidation/readiness checkpoint for the
Phase 2, Phase 3A, Phase 3B, and Phase 3C worktrees. Produce a plan and
decision report only.

## Scope

This task may read Phase 3D report outputs, Phase 2/3A/3B/3C worktree docs,
tests, and reports, and the Phase 2B helper candidate. It may write only this
task card and the approved Phase 3E report bundle.

## Required Boundaries

- Do not merge, cherry-pick, commit, copy, stage, clean, stash, reset, remove,
  or unstage Phase 2/3A/3B/3C files or unrelated dirty files.
- Do not implement code, edit `docs/strategy_lab/**`, edit
  `tests/strategy_lab/**`, edit Tenn runtime/backend/product code, or edit
  Cockpit UI/backend code.
- Do not touch DB, Qdrant, news, memory, financial-truth stores,
  parser/extraction/gold-label files, source-registry files, dependency files,
  lockfiles, Docker/systemd/env/secrets files, QuantDinger/MCP runtime
  directories, adapter/client implementation, artifact store implementation,
  real API clients, broker/exchange/paper/live execution configs, scheduled
  jobs, autonomous loops, tokens, or production data.
- Do not start QuantDinger, MCP, Docker, Tenn runtime services, Cockpit, paper
  execution, live execution, or trading execution.
- Treat Tenn as the research brain, evidence/provenance authority, schema
  validator, permission gate, artifact boundary, and review owner.
- Treat QuantDinger as a replaceable external read/backtest sidecar/comparator
  only.
- Treat Strategy Lab artifacts as `PENDING_REVIEW` by default.
- Preserve `strategy_lab_artifact_v1` as authoritative and
  `strategy_lab_sidecar_artifact_v1` as pending-review pre-envelope evidence
  only.

## Required Preflight

- Print current working directory, repo root, branch, HEAD, git status, worktree
  list, and recent commits.
- Verify whether `/home/l4nd0/tenn` resolves to the NVMe checkout and whether
  any symlink target is unavailable.
- Verify task-card and registry command help.
- Validate this task card if supported.
- Run registry `list-active` and `check-overlap` if supported.
- Claim the registry job only if no active job or dirty file overlaps this
  task-card/report surface.
- Inspect dirty, untracked, deleted, and staged files in the current checkout.
- Stop if active jobs or dirty files overlap the allowed report/task-card
  surfaces.

## Required Inventory

Inventory Phase 2, Phase 3A, Phase 3B, and Phase 3C worktrees and classify:

- branch
- HEAD
- clean, untracked, staged, modified, deleted, or ignored-report status
- files added or changed by category
- whether each relevant file is active candidate input, report-only evidence,
  pending-review helper candidate, archive-only, duplicate/superseded, or
  `DATA_MISSING`
- whether staged, uncommitted, or untracked files make the worktree unsafe to
  treat as a committed baseline

## Required Plan Topics

Produce an offline implementation plan covering:

- Tenn-owned `StrategyLabSidecarClient` boundary
- policy-before-dispatch contract
- mock-to-real transport transition criteria
- schema validation gate
- raw payload quarantine and persistence design topics
- artifact emission path to `PENDING_REVIEW` only
- audit logging requirements
- rate-limit and timeout planning
- sidecar unavailable behavior
- no-store-write invariants
- no-trading-scope invariants
- human review gates
- feature flags and disabled-by-default plan
- test plan required before implementation

## Future Phase Suggestions

Propose future phases as planning suggestions only:

- Phase 3F: consolidation/save or merge plan, if needed
- Phase 3G: production-code implementation task-card draft, if ever approved
- Phase 3H: offline mocked production-module tests
- Phase 3I: no-network adapter skeleton only
- Phase 3J: isolated real sidecar smoke, only if separately approved
- Phase 4: chat workflow design only
- Phase 5: Strategy Lab UI design only

## Required Outputs

- `reports/agent_jobs/strategy_lab_offline_implementation_plan_phase3e_v1_20260521/README.md`
- `reports/agent_jobs/strategy_lab_offline_implementation_plan_phase3e_v1_20260521/preflight.md`
- `reports/agent_jobs/strategy_lab_offline_implementation_plan_phase3e_v1_20260521/input_inventory.md`
- `reports/agent_jobs/strategy_lab_offline_implementation_plan_phase3e_v1_20260521/worktree_consolidation_readiness.md`
- `reports/agent_jobs/strategy_lab_offline_implementation_plan_phase3e_v1_20260521/offline_implementation_plan.md`
- `reports/agent_jobs/strategy_lab_offline_implementation_plan_phase3e_v1_20260521/future_phase_map.md`
- `reports/agent_jobs/strategy_lab_offline_implementation_plan_phase3e_v1_20260521/risk_and_hard_stops.md`
- `reports/agent_jobs/strategy_lab_offline_implementation_plan_phase3e_v1_20260521/go_no_go_next.md`
- `reports/agent_jobs/strategy_lab_offline_implementation_plan_phase3e_v1_20260521/status.json`
- `reports/agent_jobs/strategy_lab_offline_implementation_plan_phase3e_v1_20260521/diff-check.json` if supported

## Required Classification

Recommend exactly one:

- `GO_PHASE3F_CONSOLIDATION_SAVE_PLAN_ONLY`
- `GO_PHASE3G_OFFLINE_PRODUCTION_MODULE_TASK_CARD_DRAFT_ONLY`
- `DEFER_DIRTY_WORKTREE_CONSOLIDATION_REQUIRED`
- `DEFER_MISSING_INPUTS`
- `REJECT_TOO_RISKY`

Prefer consolidation/save planning before production-module task-card drafting
unless current evidence proves the relevant worktrees have already been
consolidated.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/strategy_lab_offline_implementation_plan_phase3e_v1_20260521.md`
- `python3 scripts/agent_job_registry.py list-active --repo-root /home/l4nd0/tenn`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/strategy_lab_offline_implementation_plan_phase3e_v1_20260521.md --repo-root /home/l4nd0/tenn`
- Claim and later release the registry job if supported and safe.
- Markdown/document sanity check if the repo has one.
- `git diff --check`
- `git diff --cached --check` if staged files exist.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/strategy_lab_offline_implementation_plan_phase3e_v1_20260521.md --repo-root /home/l4nd0/tenn`
- Final `git status --short --untracked-files=all`.
- Prove written files are limited to this task card and the approved report
  bundle.
- Prove no `docs/strategy_lab/**`, `tests/strategy_lab/**`, runtime/product
  code, Cockpit, production data, Tenn stores, services, tokens, dependencies,
  Phase 2/3A/3B/3C merge/copy/stage action, or paper/live execution were
  touched.

## Definition of Done

- Phase 3E report bundle exists.
- Phase 2/3A/3B/3C consolidation/readiness has been inventoried.
- Offline implementation plan, future phase map, risks, hard stops, and
  go/no-go decision are documented.
- Exactly one next-phase recommendation is made.
- No forbidden implementation, runtime, store, dependency, token, production
  data, merge/copy/stage, or trading action happened.
