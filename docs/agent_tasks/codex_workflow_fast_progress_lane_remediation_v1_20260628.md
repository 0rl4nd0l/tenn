---
job_id: codex_workflow_fast_progress_lane_remediation_v1_20260628
lane: Reporting
supporting_lanes:
  - Repo Hygiene
owner: Codex
approval_required: false
allow_unapproved_safe_extension: true
allow_audit_code_changes: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/codex_workflow_fast_progress_lane_remediation_v1_20260628
mutation_mode: safe_extension
production_data_access: false
closeout_scope: control_plane_only
allowed_files:
  - docs/agent_tasks/codex_workflow_fast_progress_lane_remediation_v1_20260628.md
  - AGENTS.md
  - docs/dev_flow/SKILLS_SURFACE.md
  - docs/dev_flow/CODEX_OPERATOR_GUIDE.md
  - .agents/skills/tenn-git-guard/SKILL.md
  - .agents/skills/tenn-git-guard/scripts/tenn_git_guard.py
  - .agents/skills/tenn-git-guard/tests/test_tenn_git_guard.py
  - .agents/skills/tenn-fix/SKILL.md
  - .agents/skills/tenn-review-board/SKILL.md
  - reports/agent_jobs/codex_workflow_fast_progress_lane_remediation_v1_20260628/STATE.md
  - reports/agent_jobs/codex_workflow_fast_progress_lane_remediation_v1_20260628/DECISIONS.md
  - reports/agent_jobs/codex_workflow_fast_progress_lane_remediation_v1_20260628/VALIDATION.md
  - reports/agent_jobs/codex_workflow_fast_progress_lane_remediation_v1_20260628/PR_REVIEW.md
  - reports/agent_jobs/codex_workflow_fast_progress_lane_remediation_v1_20260628/NEXT_GOAL.md
  - reports/agent_jobs/codex_workflow_fast_progress_lane_remediation_v1_20260628/TASK_LEDGER_ENTRY.json
---

# Codex Workflow Fast Progress Lane Remediation V1

## Objective

Implement the review-board remediation plan for Codex workflow bloat: add a
fast/summarized guard lane and explicit workflow lane selection so ordinary
small fixes reach action faster while high-risk Tenn work still uses full guard
and Runtime Functionality Proof.

## Source Artifact

The board packet is report-local in the stale starting checkout:

```text
/home/l4nd0/tenn/reports/agent_jobs/codex_workflow_remediation_review_board_v1_20260628/BOARD_DECISION.json
```

This task starts from current canonical in a fresh sibling worktree because
the stale checkout was guard-classified as `STALE_PATH`.

## Scope

- Add guard CLI support for summarized fallback output while preserving full
  fallback detail when requested.
- Cap or summarize branch and worktree fallback output for fast/small use.
- Add explicit `FAST_PROGRESS`, `STANDARD_FIX`, `FULL_GUARD`, and
  `RUNTIME_PROOF` lane selection guidance.
- Update `tenn-fix` so ordinary small fixes avoid review-board, handoff, worker
  delegation, and broad report packets unless a real blocker appears.
- Update `tenn-review-board` so boards do not become another report-only loop.
- Add focused guard tests proving summarized output and unchanged blocking for
  stale/non-git/dirty-related paths.

## Hard Boundaries

- Control-plane docs, repo-backed skills, guard script/tests, this task card,
  and this report bundle only.
- Do not touch product, runtime, backend, data, extraction, parser, source-PDF,
  gold-label, prompt, schema, service, model, GPU, DB, Qdrant, Redis, news,
  memory, or count-24 paths.
- Do not mutate host-global files under `/home/l4nd0/.codex`,
  `/home/l4nd0/.agents`, plugin cache directories, or any home-directory skill
  roots.
- Do not add a new visible skill.
- Do not weaken Runtime Functionality Proof for runtime-like work.
- Do not clean, delete branches, remove worktrees, merge, rebase, reset, stash,
  cherry-pick, prune, or force-push.
- Do not mutate GitHub unless explicitly approved after local validation.

## Required Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/codex_workflow_fast_progress_lane_remediation_v1_20260628.md`
- Portable guard preflight for this task worktree.
- Repo-local task ledger validation when available.
- Repo-local registry read-only listing when available.
- Focused guard tests for summarized fallback output and blocking behavior.
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/codex_workflow_fast_progress_lane_remediation_v1_20260628.md --no-write-report`
- `python3 scripts/agent_job_contract.py check-report-artifacts docs/agent_tasks/codex_workflow_fast_progress_lane_remediation_v1_20260628.md`
- Product/runtime/data/extraction/count-24 guard by changed-path inspection.
- Host-global guard by changed-path inspection.
- Final `git status --short --untracked-files=all`.

## Definition Of Done

- Fast/summarized guard mode is implemented and tested.
- Full guard mode remains available and tested.
- Stale path, non-git, and dirty-related blocking behavior remains intact.
- Control-plane docs and skills explain lane selection clearly.
- The visible repo skill count does not increase.
- No product/runtime/data/extraction/count-24 or host-global mutation occurs.
