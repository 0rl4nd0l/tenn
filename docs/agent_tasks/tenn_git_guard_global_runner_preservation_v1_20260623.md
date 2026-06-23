---
job_id: tenn_git_guard_global_runner_preservation_v1_20260623
lane: Reporting
supporting_lanes:
  - Provenance
  - Evaluation
owner: Codex
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/tenn_git_guard_global_runner_preservation_v1_20260623
mutation_mode: safe_extension
production_data_access: false
task_scope: control_plane_only
closeout_scope: report_only
allowed_files:
  - docs/agent_tasks/tenn_git_guard_global_runner_preservation_v1_20260623.md
  - .agents/skills/tenn-git-guard/SKILL.md
  - .agents/skills/tenn-git-guard/scripts/tenn_git_guard.py
  - .agents/skills/tenn-git-guard/tests/test_tenn_git_guard.py
  - docs/dev_flow/SKILLS_SURFACE.md
  - reports/agent_jobs/tenn_git_guard_global_runner_preservation_v1_20260623/README.md
  - reports/agent_jobs/tenn_git_guard_global_runner_preservation_v1_20260623/VALIDATION.md
  - reports/agent_jobs/tenn_git_guard_global_runner_preservation_v1_20260623/GUARD_SMOKE.json
  - reports/agent_jobs/tenn_git_guard_global_runner_preservation_v1_20260623/RUNTIME_GUARD_SMOKE.json
  - reports/agent_jobs/tenn_git_guard_global_runner_preservation_v1_20260623/RUNTIME_DIRTY_CLASSIFICATION.md
  - reports/agent_jobs/tenn_git_guard_global_runner_preservation_v1_20260623/handoff/HANDOFF.md
  - reports/agent_jobs/tenn_git_guard_global_runner_preservation_v1_20260623/handoff/NEXT_GOAL.md
  - reports/agent_jobs/tenn_git_guard_global_runner_preservation_v1_20260623/handoff/LEDGER_ENTRY.json
---

# Tenn Git Guard Global Runner Preservation V1

## Objective

Preserve the host-global `tenn-git-guard` runner in a repo-backed control-plane
surface so fresh sessions can run guard preflight against runtime/product repos
even when those repos do not contain Tenn control-plane scripts.

## Scope

Allowed:

- Update the repo-backed `tenn-git-guard` skill to prefer the global runner.
- Add the portable guard runner and focused unit tests under the skill.
- Update the skill surface route map to mention the portable runner contract.
- Write report-local validation and handoff artifacts for this lane.
- Run read-only guard smoke against the Greyhound runtime checkout.

Forbidden:

- Product, runtime, data, extraction, source-PDF, gold-label, prompt, DB,
  Qdrant, Redis, news, memory, service, model/GPU, training, promotion, EV,
  betting, snapshot, registry, or live-system mutation.
- GitHub mutation outside the explicitly approved preservation branch/PR:
  no comments, labels, closes, unrelated edits, or merges.
- Branch deletion, worktree removal, `git clean`, `git reset --hard`,
  stash/drop, rebase, or cherry-pick.
- Weakening identity, source, official-result, or pre-jump timing gates.

## Required Evidence

- Existing host-global skill files under
  `/home/l4nd0/.agents/skills/tenn-git-guard/`.
- Current control-plane branch, HEAD, dirty state, registry state, and ledger
  state.
- Greyhound runtime guard smoke for
  `/mnt/tenn-nvme2/tenn/offloaded-home/l4nd0/greyhound-runtime-master-live-20260621`.

## Required Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/tenn_git_guard_global_runner_preservation_v1_20260623.md`
- `python3 -m py_compile .agents/skills/tenn-git-guard/scripts/tenn_git_guard.py .agents/skills/tenn-git-guard/tests/test_tenn_git_guard.py`
- `python3 -m unittest discover -s .agents/skills/tenn-git-guard/tests`
- `python3 .agents/skills/tenn-git-guard/scripts/tenn_git_guard.py preflight --repo-root . --topic "tenn git guard global runner preservation" --json`
- `python3 .agents/skills/tenn-git-guard/scripts/tenn_git_guard.py preflight --repo-root /mnt/tenn-nvme2/tenn/offloaded-home/l4nd0/greyhound-runtime-master-live-20260621 --topic "score-live output guard" --json`
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/tenn_git_guard_global_runner_preservation_v1_20260623.md --no-write-report`

## Definition Of Done

- Repo-backed skill instructions no longer tell fresh sessions to require
  repo-local Tenn scripts inside runtime repos.
- Portable runner and tests are present under the repo-backed skill surface.
- Report artifacts explain that missing ledger rows remain `DATA_MISSING` until
  ledger state itself is populated.
- Greyhound runtime promotion remains blocked.
