---
job_id: system_brief_draft_pr_coverage_fix_v1_20260709
lane: Reporting
supporting_lanes:
  - Evaluation
  - Repo Hygiene
owner: Codex
approval_required: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/system_brief_draft_pr_coverage_fix_v1_20260709
mutation_mode: safe_extension
production_data_access: false
task_scope: control_plane_only
stacked_on_pr: 495
allowed_files:
  - docs/agent_tasks/system_brief_draft_pr_coverage_fix_v1_20260709.md
  - scripts/system_brief.py
  - scripts/test_system_brief.py
  - reports/agent_jobs/system_brief_draft_pr_coverage_fix_v1_20260709/README.md
  - reports/agent_jobs/system_brief_draft_pr_coverage_fix_v1_20260709/STATE.md
  - reports/agent_jobs/system_brief_draft_pr_coverage_fix_v1_20260709/VALIDATION.md
  - reports/agent_jobs/system_brief_draft_pr_coverage_fix_v1_20260709/diff-check.json
---

# System Brief Draft PR Coverage Fix V1

## Approval

USER_APPROVED: Orlando approved proceeding from the stack review finding that
the system brief omitted draft PR #491 and other reviewable draft PRs.

## Objective

Fix `scripts/system_brief.py` so the startup brief surfaces all draft PRs that
need review, including the root system-brief PR #491, while keeping current
automation/control-plane stack PRs ahead of older unrelated drafts.

## Scope

- Widen draft PR collection beyond titles or heads containing `automation` or
  `[experiment]`.
- Preserve priority for current automation/control-plane/system-brief stack
  work.
- Demote older unrelated draft PRs to a lower-priority stale draft class.
- Add regression tests proving #491-style system-brief draft PRs are included
  and older unrelated drafts do not outrank current stack items.

## Out Of Scope

- No GitHub writes by the helper.
- No issue, PR, label, branch, worktree, timer, service, runtime, data, DB,
  Qdrant, Redis, source-PDF, gold-label, extraction, Docker, model/GPU, or
  secret mutation.
- No merge, rebase, retargeting, branch cleanup, or timer install.

## Validation Plan

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/system_brief_draft_pr_coverage_fix_v1_20260709.md`
- red test: `python3 -m unittest scripts.test_system_brief`
- green tests: `python3 -m unittest scripts.test_system_brief scripts.test_automation_candidate_store scripts.test_automation_github_dedupe scripts.test_automation_write_gate scripts.test_automation_write_executor_plan`
- `python3 scripts/system_brief.py --repo-root . --automation-root /home/l4nd0/.codex/automations/tenn --json`
- `python3 -m py_compile scripts/system_brief.py scripts/test_system_brief.py`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/system_brief_draft_pr_coverage_fix_v1_20260709.md`
- `python3 scripts/agent_job_contract.py check-report-artifacts docs/agent_tasks/system_brief_draft_pr_coverage_fix_v1_20260709.md`
- `python3 scripts/agent_job_contract.py check-closeout docs/agent_tasks/system_brief_draft_pr_coverage_fix_v1_20260709.md`
- `git diff --check`
- `git status --short --untracked-files=all`
