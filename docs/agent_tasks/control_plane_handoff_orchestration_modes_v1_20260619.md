---
job_id: control_plane_handoff_orchestration_modes_v1_20260619
lane: Reporting
supporting_lanes:
  - Repo Hygiene
owner: Codex
approval_required: false
allow_unapproved_safe_extension: true
allow_audit_code_changes: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/control_plane_handoff_orchestration_modes_v1_20260619
mutation_mode: safe_extension
production_data_access: false
allowed_files:
  - docs/agent_tasks/control_plane_handoff_orchestration_modes_v1_20260619.md
  - .agents/skills/tenn-handoff/SKILL.md
  - .agents/skills/tenn-fix/SKILL.md
  - .agents/skills/tenn-explain/SKILL.md
  - .agents/skills/tenn-review-board/SKILL.md
  - docs/dev_flow/SKILLS_SURFACE.md
  - docs/dev_flow/templates/HANDOFF.md
  - docs/dev_flow/templates/HANDOFF_NEXT_GOAL.md
  - docs/dev_flow/templates/NEXT_GOAL.md
  - docs/dev_flow/templates/WORKER_TASK.md
  - docs/dev_flow/templates/WORKER_RESULT.md
  - docs/dev_flow/templates/BOARD.md
  - docs/dev_flow/templates/BOARD_DECISION.json
  - docs/dev_flow/templates/EXPLAIN.md
  - docs/dev_flow/worker_bridge/README.md
  - scripts/opencode_worker_bridge.py
  - tests/test_opencode_worker_bridge.py
  - reports/agent_jobs/control_plane_handoff_orchestration_modes_v1_20260619/DESIGN.md
  - reports/agent_jobs/control_plane_handoff_orchestration_modes_v1_20260619/README.md
  - reports/agent_jobs/control_plane_handoff_orchestration_modes_v1_20260619/STATE.md
  - reports/agent_jobs/control_plane_handoff_orchestration_modes_v1_20260619/DECISIONS.md
  - reports/agent_jobs/control_plane_handoff_orchestration_modes_v1_20260619/VALIDATION.md
  - reports/agent_jobs/control_plane_handoff_orchestration_modes_v1_20260619/PR_REVIEW.md
  - reports/agent_jobs/control_plane_handoff_orchestration_modes_v1_20260619/git_guard.json
  - reports/agent_jobs/control_plane_handoff_orchestration_modes_v1_20260619/visible_skill_count_before.txt
  - reports/agent_jobs/control_plane_handoff_orchestration_modes_v1_20260619/visible_skill_count_after.txt
  - reports/agent_jobs/control_plane_handoff_orchestration_modes_v1_20260619/validation.json
  - reports/agent_jobs/control_plane_handoff_orchestration_modes_v1_20260619/diff-check.json
  - reports/agent_jobs/control_plane_handoff_orchestration_modes_v1_20260619/ledger_entry.json
  - reports/agent_jobs/control_plane_handoff_orchestration_modes_v1_20260619/handoff/HANDOFF.md
  - reports/agent_jobs/control_plane_handoff_orchestration_modes_v1_20260619/handoff/NEXT_GOAL.md
---

# Control Plane Handoff Orchestration Modes V1

## Objective

Improve Tenn control-plane handoff and orchestration behavior so a fresh Codex
session can continue as an agent orchestrator with minimal context loss. Start
from current canonical `origin/migration/clean-runtime-baseline-reconstruct-v1`
after PR #375 and PR #378, and preserve the reduced visible skill surface.

## Scope

- Refine repo-native `tenn-handoff` and handoff templates so fresh sessions get
  linked artifacts, risks, next-first action, do-not-touch boundaries, and a
  short orchestrator-oriented `NEXT_GOAL.md`.
- Add an explicit orchestrator continuation mode to `tenn-fix` and worker
  templates instead of creating a new visible skill.
- Add zoom-out / contrarian mode to `tenn-explain` and `tenn-review-board`
  instead of creating a new visible skill.
- Update `docs/dev_flow/SKILLS_SURFACE.md` to document the mode-based surface
  and prevent skill-bloat regression.
- Produce a report bundle with a design note, validation record, review record,
  handoff, and ledger entry.
- Apply PR #380 review fixes only for the shared `NEXT_GOAL.md` contract,
  handoff-specific next-goal guidance, worker stop-condition bridge validation,
  exact `stop_condition_hit` allowed-value validation, focused bridge tests,
  and skill-surface freshness metadata.

## Hard Boundaries

- Do not touch Tenn product, backend, frontend, runtime, data, extraction,
  source-PDF, gold-label, prompt, schema, service, model, GPU, DB, Qdrant,
  Redis, news, memory, or count-24 paths.
- Do not mutate host-global Codex files under `/home/l4nd0/.codex`,
  `/home/l4nd0/.agents`, plugin cache directories, or home-directory skill
  roots.
- Do not undo PR #378's skill trim.
- Do not add a new visible skill unless the design report proves it is better
  than a mode in an existing core skill. This task expects no new visible skill.
- Do not triage or clean old dirty checkouts.
- Do not delete branches or worktrees.
- Do not merge, rebase, cherry-pick, reset, stash, prune, or force-push.
- Do not close, edit, label, or comment on GitHub issues or PRs. Pushing this
  branch and opening the focused PR is allowed by the owner request after
  validation.
- Do not start services, install project dependencies, or run product/runtime
  validation.

## Preflight Evidence Required

- Fresh worktree from `origin/migration/clean-runtime-baseline-reconstruct-v1`.
- Branch, HEAD, remote, upstream, dirty state, selected base, and merge base.
- Read-only active job registry state.
- Task ledger resolve, validate, and duplicate-work search.
- Read-only GitHub confirmation that PR #375 and PR #378 are merged.
- Current canonical control-plane skill, template, and skill-surface docs.
- Visible skill count before implementation.

## Required Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/control_plane_handoff_orchestration_modes_v1_20260619.md`
- `python3 scripts/agent_task_ledger.py --repo-root . validate`
- `python3 scripts/agent_job_registry.py list-active --read-only --repo-root .`
- Skill frontmatter/description check.
- Visible skill count check proving the count did not increase unexpectedly.
- Active removed-entrypoint reference check.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/control_plane_handoff_orchestration_modes_v1_20260619.md --repo-root .`
- `python3 scripts/agent_job_contract.py check-report-artifacts docs/agent_tasks/control_plane_handoff_orchestration_modes_v1_20260619.md --repo-root .`
- `git diff --check`
- `python3 -m py_compile scripts/opencode_worker_bridge.py tests/test_opencode_worker_bridge.py`
- `python3 -m unittest tests.test_opencode_worker_bridge`
- Forbidden product/runtime/data/extraction/count-24 path guard.
- Host-global guard.
- Final `git status --short --untracked-files=all`.

## Definition Of Done

- The handoff workflow and templates require durable linked context, next-first
  action, do-not-touch boundaries, risks, milestones, and a short orchestrator
  next-goal prompt.
- Orchestrator continuation behavior is added as a mode in an existing core
  skill, with worker delegation limits and integration discipline.
- Zoom-out / contrarian review behavior is added as a mode in existing core
  explanation/review skills, with financial extraction breadth guidance.
- `docs/dev_flow/SKILLS_SURFACE.md` records that orchestration and zoom-out are
  modes and that the visible skill surface stays intentionally small.
- Shared `NEXT_GOAL.md` remains generic for `tenn-issue`, `tenn-review-board`,
  and non-handoff producers.
- OpenCode bridge validation requires the worker stop-condition signal when the
  worker task template calls it required and accepts only exact
  `yes`/`no`/`DATA_MISSING` values.
- No product/runtime/extraction/data/count-24 or host-global mutation occurs.
- A local commit and focused PR are created after validation.
