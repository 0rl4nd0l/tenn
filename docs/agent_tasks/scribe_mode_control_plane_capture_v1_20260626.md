---
job_id: scribe_mode_control_plane_capture_v1_20260626
lane: Reporting
supporting_lanes:
  - Repo Hygiene
owner: Codex
approval_required: false
allow_unapproved_safe_extension: true
allow_audit_code_changes: false
timeout_seconds: 7200
output_dir: reports/agent_jobs/scribe_mode_control_plane_capture_v1_20260626
mutation_mode: safe_extension
production_data_access: false
closeout_scope: control_plane_only
allowed_files:
  - docs/agent_tasks/scribe_mode_control_plane_capture_v1_20260626.md
  - .agents/skills/tenn-goal-report/SKILL.md
  - .agents/skills/tenn-fix/SKILL.md
  - docs/dev_flow/templates/OPERATOR_NOTES.md
  - docs/dev_flow/templates/DECISIONS.md
  - docs/dev_flow/templates/STATE.md
  - docs/dev_flow/SKILLS_SURFACE.md
  - reports/agent_jobs/scribe_mode_control_plane_capture_v1_20260626/README.md
  - reports/agent_jobs/scribe_mode_control_plane_capture_v1_20260626/STATE.md
  - reports/agent_jobs/scribe_mode_control_plane_capture_v1_20260626/DECISIONS.md
  - reports/agent_jobs/scribe_mode_control_plane_capture_v1_20260626/VALIDATION.md
  - reports/agent_jobs/scribe_mode_control_plane_capture_v1_20260626/PR_REVIEW.md
  - reports/agent_jobs/scribe_mode_control_plane_capture_v1_20260626/diff-check.json
  - reports/agent_jobs/scribe_mode_control_plane_capture_v1_20260626/guard_portable.json
  - reports/agent_jobs/scribe_mode_control_plane_capture_v1_20260626/guard_repo.json
  - reports/agent_jobs/scribe_mode_control_plane_capture_v1_20260626/registry_readonly.json
  - reports/agent_jobs/scribe_mode_control_plane_capture_v1_20260626/ledger_validate.json
  - reports/agent_jobs/scribe_mode_control_plane_capture_v1_20260626/ledger_search_scribe.json
  - reports/agent_jobs/scribe_mode_control_plane_capture_v1_20260626/scribe_grep_current.txt
  - reports/agent_jobs/scribe_mode_control_plane_capture_v1_20260626/ledger_entry_claimed.json
  - reports/agent_jobs/scribe_mode_control_plane_capture_v1_20260626/ledger_entry_done.json
github_writes_allowed:
  - push branch safe/scribe-mode-control-plane-v1-20260626
  - open draft PR against migration/clean-runtime-baseline-reconstruct-v1
---

# Scribe Mode Control Plane Capture V1

## Objective

Implement Scribe as a compact control-plane mode inside existing Tenn operator
surfaces, not as a new visible repo-backed skill.

## Scope

- Define Scribe mode in `tenn-goal-report` for long `/goal` and frame-mode runs.
- Update `tenn-fix` so long or risky implementation runs capture user steering,
  corrections, hard constraints, conflicts, and owner decisions in report-local
  artifacts.
- Update `OPERATOR_NOTES.md`, `DECISIONS.md`, and `STATE.md` templates with
  compact Scribe fields or update triggers.
- Update `SKILLS_SURFACE.md` only for routing text needed to show Scribe as a
  mode of existing commands.
- Preserve the repo-visible skill count and keep legacy `.codex/skills`
  absent.
- Write report-local validation and review evidence.

## Hard Boundaries

- Do not touch product, runtime, backend, extraction, parser, prompt, evaluator,
  source PDF, gold-label, schema, migration, service, model, GPU, DB, Qdrant,
  Redis, news, memory, source-document, or production-data behavior.
- Do not touch host-global Codex, agent, plugin, shell, service, or runtime
  configuration.
- Do not create `.agents/skills/scribe/SKILL.md`, `.codex/skills/scribe`, or
  any other new visible Scribe skill.
- Do not mutate GitHub issues, PRs, labels, comments, or branches beyond this
  local worktree.
- Do not merge, rebase, reset, stash, prune, delete branches, clean worktrees,
  or mutate parked merge state.
- Do not mutate the live task ledger or active-job registry; write intended
  ledger entries under the report bundle instead.

## Required Validation

- `python3 /home/l4nd0/.agents/skills/tenn-git-guard/scripts/tenn_git_guard.py preflight --repo-root . --topic "scribe mode control-plane capture" --json`
- `python3 .agents/skills/tenn-git-guard/scripts/tenn_git_guard.py preflight --repo-root . --topic "scribe mode control-plane capture" --json`
- `python3 scripts/agent_job_registry.py list-active --read-only --repo-root .`
- `python3 scripts/agent_task_ledger.py --repo-root . validate`
- `python3 scripts/agent_task_ledger.py --repo-root . search --text scribe`
- `rg -n "scribe|Scribe" docs/agent_tasks reports/agent_jobs .agents/skills docs/dev_flow scripts --hidden --glob '!**/.git/**'`
- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/scribe_mode_control_plane_capture_v1_20260626.md`
- `find .agents/skills -maxdepth 2 -name SKILL.md | sort`
- `[ ! -d .codex/skills ] || find .codex/skills -maxdepth 2 -name SKILL.md | sort`
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/scribe_mode_control_plane_capture_v1_20260626.md --repo-root .`
- `python3 scripts/agent_job_contract.py check-report-artifacts docs/agent_tasks/scribe_mode_control_plane_capture_v1_20260626.md --repo-root .`
- `python3 scripts/agent_job_contract.py check-closeout docs/agent_tasks/scribe_mode_control_plane_capture_v1_20260626.md --repo-root .`
- Final diff/code review using `docs/dev_flow/templates/PR_REVIEW.md` and the
  host code-reviewer stance under Tenn gates.

## Definition Of Done

- Scribe is documented as a report-local capture mode, not an executor, worker,
  reviewer, or new visible skill.
- Long `/goal` and long/risky `/fix` runs know where to capture user steering,
  hard constraints, conflicts, owner decisions, and superseded corrections.
- Templates provide compact Scribe slots without creating a new `SCRIBE.md`
  artifact requirement.
- `SKILLS_SURFACE.md` continues to prefer modes/sections/templates over new
  always-visible skills and records Scribe's home if routing text changed.
- Repo-backed visible skill count is unchanged.
- Legacy `.codex/skills` remains absent or has no visible `SKILL.md` entries.
- No product/runtime/extraction/data/source-document/gold-label/DB/service/
  host-global/GitHub surfaces change.
- Report-local validation, review, and intended ledger entries are written.
- Push the local branch and open a draft PR only after explicit owner approval.
- Merging still requires separate explicit owner approval.
