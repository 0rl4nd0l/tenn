---
job_id: strategy_lab_consolidation_save_plan_phase3f_v1_20260521
lane: Provenance
owner: Codex
mutation_mode: audit_only
approval_required: false
allow_audit_code_changes: true
production_data_access: false
timeout_seconds: 7200
output_dir: reports/agent_jobs/strategy_lab_consolidation_save_plan_phase3f_v1_20260521

allowed_files:
  - docs/agent_tasks/strategy_lab_consolidation_save_plan_phase3f_v1_20260521.md
  - reports/agent_jobs/strategy_lab_consolidation_save_plan_phase3f_v1_20260521/
  - reports/agent_jobs/strategy_lab_consolidation_save_plan_phase3f_v1_20260521/README.md
  - reports/agent_jobs/strategy_lab_consolidation_save_plan_phase3f_v1_20260521/preflight.md
  - reports/agent_jobs/strategy_lab_consolidation_save_plan_phase3f_v1_20260521/input_inventory.md
  - reports/agent_jobs/strategy_lab_consolidation_save_plan_phase3f_v1_20260521/worktree_file_classification.md
  - reports/agent_jobs/strategy_lab_consolidation_save_plan_phase3f_v1_20260521/preservation_model.md
  - reports/agent_jobs/strategy_lab_consolidation_save_plan_phase3f_v1_20260521/future_action_matrix.md
  - reports/agent_jobs/strategy_lab_consolidation_save_plan_phase3f_v1_20260521/phase3g_recommendation.md
  - reports/agent_jobs/strategy_lab_consolidation_save_plan_phase3f_v1_20260521/status.json
  - reports/agent_jobs/strategy_lab_consolidation_save_plan_phase3f_v1_20260521/diff-check.json
---

# Strategy Lab Consolidation Save Plan Phase 3F

## Objective

Run Phase 3F Strategy Lab consolidation/save planning for QuantDinger/Tenn.
Use the completed Phase 3E implementation-plan-only report and the Phase
2/2B/3A/3B/3C/3D worktrees as candidate evidence. Produce a
consolidation/save decision report only.

## Scope

This task may read Phase 3E report outputs, Phase 3D report outputs, and Phase
2/2B/3A/3B/3C worktree docs, tests, task cards, reports, git state, and file
metadata. It may write only this task card and the Phase 3F report bundle.

## Architecture Boundary

- Tenn is the research brain and evidence/provenance authority.
- QuantDinger is a replaceable external read/backtest sidecar/comparator only.
- QuantDinger outputs become Strategy Lab artifacts, never canonical financial
  truth.
- Strategy Lab artifacts default to `PENDING_REVIEW`.
- `strategy_lab_artifact_v1` remains authoritative.
- `strategy_lab_sidecar_artifact_v1` remains pending-review pre-envelope
  evidence only.
- Tenn code must own tool execution policy, schema validation, permissions,
  logging, raw-output quarantine, and artifact review boundaries.
- Codex is a dev/test/review/planning agent only, not the runtime path.

## Required Boundaries

- Do not merge, cherry-pick, commit, copy, stage, unstage, clean, stash, reset,
  remove, or edit Phase 2/2B/3A/3B/3C/3D/3E files.
- Do not implement code, edit `docs/strategy_lab/**`, edit
  `tests/strategy_lab/**`, edit Tenn runtime/backend/product code, or edit
  Cockpit UI/backend code.
- Do not touch DB, Qdrant, news, memory, financial-truth stores,
  parser/extraction/gold-label files, source-registry files, dependency files,
  lockfiles, Docker/systemd/env/secrets files, QuantDinger/MCP runtime
  directories, MCP adapter/client implementation, artifact store
  implementation, real API clients, broker/exchange/paper/live execution
  configs, scheduled jobs, autonomous loops, tokens, or production data.
- Do not start QuantDinger, MCP, Docker, Tenn runtime services, Cockpit, paper
  execution, live execution, or trading execution.
- If consolidation planning requires actual file movement, committing, staging,
  or edits outside the allowed files, stop and report the needed future task
  card instead of performing the action.

## Required Preflight

- Print current working directory, repo root, branch, HEAD, git status, worktree
  list, and recent commits.
- Verify `/home/l4nd0/tenn` symlink resolution and current canonical repo path.
- Verify current task-card and registry command help.
- Validate this task card if supported.
- Run registry `list-active` and `check-overlap` if supported.
- Claim the registry job only if no active job or dirty file overlaps this
  task-card/report surface.
- Inspect dirty, untracked, deleted, and staged files in the current checkout.
- Stop if active jobs or dirty files overlap the allowed report/task-card
  surfaces.

## Required Inventory

Inventory Phase 2, Phase 2B, Phase 3A, Phase 3B, Phase 3C, Phase 3D, and Phase
3E sources and report:

- worktree path
- branch
- HEAD
- git status category: clean, untracked, staged, modified, ignored reports, or
  pycache/generated
- report bundle presence
- files added or changed by category
- whether each file is active candidate input, report-only evidence,
  pending-review helper candidate, archive-only, duplicate/superseded,
  generated/exclude, or `DATA_MISSING`

## Required Decisions

Define the target preservation model and future action matrix without performing
the actions:

- active authoritative docs/schema/tests candidates
- report evidence to preserve
- helper candidate material to keep pending-review
- duplicate/superseded material to archive
- generated files to exclude
- ignored report bundles that need explicit preservation if desired
- task cards that should be preserved as task-history evidence

For each candidate group, choose one future action:

- `COMMIT_TO_BASELINE_CANDIDATE`
- `FORCE_ADD_REPORT_EVIDENCE_CANDIDATE`
- `ARCHIVE_ONLY`
- `EXCLUDE_GENERATED`
- `KEEP_PENDING_REVIEW`
- `SUPERSEDE_WITH_AUTHORITATIVE_SCHEMA`
- `DATA_MISSING_REVIEW_REQUIRED`

## Required Sequencing Recommendation

Recommend exactly what should happen before any production-module task card:

- whether a Phase 3G save/consolidation execution task is needed
- whether a Project Memory save block is needed
- whether Phase 3A staged additions need a separate unstage/commit/archive
  decision
- whether Phase 3D/3E task cards need preserving
- whether reports under ignored `reports/agent_jobs` need force-add or should
  remain external evidence
- whether generated pycache should be excluded

## Required Outputs

- `reports/agent_jobs/strategy_lab_consolidation_save_plan_phase3f_v1_20260521/README.md`
- `reports/agent_jobs/strategy_lab_consolidation_save_plan_phase3f_v1_20260521/preflight.md`
- `reports/agent_jobs/strategy_lab_consolidation_save_plan_phase3f_v1_20260521/input_inventory.md`
- `reports/agent_jobs/strategy_lab_consolidation_save_plan_phase3f_v1_20260521/worktree_file_classification.md`
- `reports/agent_jobs/strategy_lab_consolidation_save_plan_phase3f_v1_20260521/preservation_model.md`
- `reports/agent_jobs/strategy_lab_consolidation_save_plan_phase3f_v1_20260521/future_action_matrix.md`
- `reports/agent_jobs/strategy_lab_consolidation_save_plan_phase3f_v1_20260521/phase3g_recommendation.md`
- `reports/agent_jobs/strategy_lab_consolidation_save_plan_phase3f_v1_20260521/status.json`
- `reports/agent_jobs/strategy_lab_consolidation_save_plan_phase3f_v1_20260521/diff-check.json` if supported

## Required Classification

Recommend exactly one:

- `GO_PHASE3G_CONSOLIDATION_EXECUTION_TASK_CARD_DRAFT_ONLY`
- `GO_PROJECT_MEMORY_SAVE_BLOCK_ONLY`
- `DEFER_MANUAL_REVIEW_REQUIRED`
- `DEFER_MISSING_INPUTS`
- `REJECT_TOO_RISKY`

Phase 3G, if recommended, must still be task-card-draft-only unless the user
separately approves actual consolidation mutation.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/strategy_lab_consolidation_save_plan_phase3f_v1_20260521.md`
- `python3 scripts/agent_job_registry.py list-active --repo-root /home/l4nd0/tenn`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/strategy_lab_consolidation_save_plan_phase3f_v1_20260521.md --repo-root /home/l4nd0/tenn`
- Claim and later release the registry job if supported and safe.
- Markdown/document sanity check if the repo has one.
- `git diff --check`
- `git diff --cached --check` if staged files exist.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/strategy_lab_consolidation_save_plan_phase3f_v1_20260521.md --repo-root /home/l4nd0/tenn`
- Final `git status --short --untracked-files=all`.
- Prove all written files are inside this task card and the approved report
  bundle.
- Prove no `docs/strategy_lab/**`, `tests/strategy_lab/**`, runtime/product
  code, Cockpit, production data, Tenn stores, services, tokens, dependencies,
  Phase 2/2B/3A/3B/3C/3D/3E merge/copy/stage/unstage/clean/reset/remove action,
  or paper/live execution were touched.

## Definition of Done

- Phase 3F report bundle exists.
- Phase 2/2B/3A/3B/3C/3D/3E inputs have been inventoried or marked
  `DATA_MISSING`.
- Worktree/file classifications, preservation model, future action matrix, and
  next-phase recommendation are documented.
- Exactly one next-phase recommendation is made.
- No forbidden implementation, runtime, store, dependency, token, production
  data, merge/copy/stage/unstage/clean/reset/remove, or trading action
  happened.
