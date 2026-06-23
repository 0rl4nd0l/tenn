---
job_id: repo_path_ownership_work_preservation_v1_20260623
lane: Reporting
supporting_lanes:
  - Evaluation
  - Provenance
  - Repo Hygiene
owner: Codex
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/repo_path_ownership_work_preservation_v1_20260623
mutation_mode: safe_extension
production_data_access: false
task_scope: control_plane_only
closeout_scope: control_plane_only
allowed_files:
  - AGENTS.md
  - docs/agent_tasks/repo_path_ownership_work_preservation_v1_20260623.md
  - docs/dev_flow/CODEX_OPERATOR_GUIDE.md
  - docs/dev_flow/CONTROL_PLANE_STATUS.md
  - docs/dev_flow/CONTROL_PLANE_OPEN_WORK.md
  - docs/dev_flow/REPO_PATH_OWNERSHIP_AND_WORK_PRESERVATION.md
  - docs/dev_flow/SKILLS_SURFACE.md
  - .agents/skills/tenn-git-guard/SKILL.md
  - .agents/skills/tenn-git-guard/scripts/tenn_git_guard.py
  - .agents/skills/tenn-git-guard/tests/test_tenn_git_guard.py
  - .agents/skills/tenn-fix/SKILL.md
  - reports/agent_jobs/repo_path_ownership_work_preservation_v1_20260623/README.md
  - reports/agent_jobs/repo_path_ownership_work_preservation_v1_20260623/DECISIONS.md
  - reports/agent_jobs/repo_path_ownership_work_preservation_v1_20260623/PATH_AUDIT.md
  - reports/agent_jobs/repo_path_ownership_work_preservation_v1_20260623/DUPLICATE_WORK_AUDIT.md
  - reports/agent_jobs/repo_path_ownership_work_preservation_v1_20260623/VALIDATION.md
  - reports/agent_jobs/repo_path_ownership_work_preservation_v1_20260623/GUARD_PREFLIGHT.json
  - reports/agent_jobs/repo_path_ownership_work_preservation_v1_20260623/PATH_OWNERSHIP_CHECK.json
  - reports/agent_jobs/repo_path_ownership_work_preservation_v1_20260623/PR_REVIEW.md
---

# Repo Path Ownership Work Preservation V1

## Objective

Make Tenn control-plane preflight prove repo path ownership and prior-work
visibility before implementation-capable Codex sessions start coding.

## Scope

Allowed:

- Add a control-plane source-of-truth doc for canonical branch, valid starting
  paths, invalid/runtime/sparse paths, prior-work discovery, preservation
  statuses, and stop rules.
- Extend the existing `tenn-git-guard` preflight with path ownership metadata
  and duplicate-work blocking when ledger evidence proves active/open/merged or
  owner-boundary work.
- Update existing operator docs and `tenn-fix`/`tenn-git-guard` instructions.
- Preserve current-turn path, duplicate-work, and validation evidence in the
  report bundle.
- Open a focused PR for this control-plane-only lane.

Forbidden:

- Product, runtime, data, extraction, source-PDF, gold-label, prompt, DB,
  Qdrant, Redis, news, memory, service, model/GPU, training, promotion, EV,
  betting, snapshot, greyhound runtime, or host-global mutation.
- Branch deletion, worktree removal, `git clean`, `git reset --hard`,
  stash/drop, rebase, merge, cherry-pick, pruning, or parked-work mutation.
- Inspecting `/home/l4nd0/tenn-cockpit-bff-proxy-missions-v1-20260623`
  beyond listing it as dirty/unrelated if it appears in `git worktree list`.
- Adding a new visible repo-backed skill. The visible skill count must remain
  10.

## Required Evidence

- Portable guard preflight from the requested start path and the clean task
  worktree.
- Current canonical branch and HEAD after PR #397.
- Path/worktree audit for requested known paths and registered worktrees.
- Duplicate-work audit across open PRs, local branches, registered worktrees,
  task ledger, active registry, merge parking registry, reports, and recent
  task cards.

## Required Validation

- `python3 /home/l4nd0/.agents/skills/tenn-git-guard/scripts/tenn_git_guard.py preflight --repo-root . --topic "repo path ownership work preservation duplicate work enforcement" --json`
- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/repo_path_ownership_work_preservation_v1_20260623.md`
- `python3 scripts/agent_task_ledger.py validate`
- `python3 scripts/agent_job_registry.py list-active --read-only --repo-root .`
- `python3 -m py_compile .agents/skills/tenn-git-guard/scripts/tenn_git_guard.py`
- `python3 -m unittest discover -s .agents/skills/tenn-git-guard/tests`
- Path ownership check implemented by guard preflight.
- Duplicate-work / preservation check implemented by guard preflight.
- Visible skill count check, expected 10.
- Skill frontmatter/H1 check.
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/repo_path_ownership_work_preservation_v1_20260623.md --no-write-report`
- `python3 scripts/agent_job_contract.py check-report-artifacts docs/agent_tasks/repo_path_ownership_work_preservation_v1_20260623.md --repo-root .`
- Forbidden product/runtime/data/extraction/count-24 guard.
- Greyhound path guard.
- Host-global guard.

## Definition Of Done

- Future sessions have one current control-plane doc answering the canonical
  branch, valid/invalid starting paths, cwd-not-git behavior, sibling-worktree
  creation rule, first command, prior-work search surfaces, preservation
  statuses, stop rules, and old-fix handling.
- `tenn-git-guard` preflight exposes path ownership metadata and blocks on
  ledger-proven active/open/merged or owner-boundary duplicate work.
- Report artifacts preserve path and duplicate-work evidence without touching
  product/runtime/data/extraction/greyhound/host-global surfaces.
- A focused PR is opened.
