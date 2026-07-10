---
job_id: codex_event_waiter_v1_20260710
lane: Reporting
supporting_lanes:
  - Repo Hygiene
  - Evaluation
owner: Codex
approval_required: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/codex_event_waiter_v1_20260710
mutation_mode: safe_extension
production_data_access: false
closeout_scope: control_plane_only
allowed_files:
  - docs/agent_tasks/codex_event_waiter_v1_20260710.md
  - scripts/codex_event_waiter.py
  - scripts/test_codex_event_waiter.py
  - .agents/skills/tenn-fix/SKILL.md
  - docs/dev_flow/CODEX_OPERATOR_GUIDE.md
  - reports/agent_jobs/codex_event_waiter_v1_20260710/STATE.md
  - reports/agent_jobs/codex_event_waiter_v1_20260710/DECISIONS.md
  - reports/agent_jobs/codex_event_waiter_v1_20260710/APPROVAL_MANIFEST.json
  - reports/agent_jobs/codex_event_waiter_v1_20260710/ATTACHED_WAIT_PROOF.json
  - reports/agent_jobs/codex_event_waiter_v1_20260710/ATTACHED_WAIT_PROOF.json.log
  - reports/agent_jobs/codex_event_waiter_v1_20260710/DETACHED_WAKE_PROOF.json
  - reports/agent_jobs/codex_event_waiter_v1_20260710/TASK_LEDGER_ENTRY.json
  - reports/agent_jobs/codex_event_waiter_v1_20260710/VALIDATION.md
  - reports/agent_jobs/codex_event_waiter_v1_20260710/PR_REVIEW.md
  - reports/agent_jobs/codex_event_waiter_v1_20260710/DONE_GATE_EVIDENCE.md
  - reports/agent_jobs/codex_event_waiter_v1_20260710/NEXT_GOAL.md
---

# Codex Event Waiter V1

## Objective

Implement a Tenn-first control-plane waiter that lets Codex block on GitHub PR
checks or a long-running command without spending model turns on repeated
polling. Attached waiting is the supported default. Detached thread wake-up is
experimental and must fail closed unless a disposable-thread proof succeeds.

## Approval

USER_APPROVED: Orlando approved the decision-complete plan and then explicitly
requested implementation. This approval covers the repo-local control-plane
files and report artifacts listed above. It does not authorize GitHub writes,
runtime/data/extraction mutation, persistent services, or host-global config.

## Scope

- Add `github-pr` and `command` waiter modes with one terminal JSON result.
- Bind GitHub waits to an expected PR head SHA and recheck aggregate check
  status without modifying GitHub.
- Run command arguments without a shell and capture bounded report-local logs.
- Prove attached waiting with no intermediate model polling.
- Gate any detached wake path behind a disposable-thread proof and an explicit
  experimental flag.
- Document how `tenn-fix` and operators should use the waiter and ledger
  `waiting_on_timer` state.

## Hard Boundaries

- Do not touch product, backend, runtime, data, extraction logic, source PDFs,
  gold labels, prompts, DB, Qdrant, Redis, news, memory, service config, Docker,
  model/GPU config, or secrets.
- Do not install dependencies or persistent systemd services.
- Do not mutate host-global Codex files or configuration.
- Do not create, update, comment on, push, merge, or otherwise mutate GitHub.
- Do not merge, rebase, reset, stash, clean, delete, prune, or remove worktrees.
- Wait completion is activity evidence only. Extraction/runtime functionality
  still requires the Runtime Functionality Proof table.

## Required Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/codex_event_waiter_v1_20260710.md`
- Portable Git Guard preflight for the task worktree.
- `python3 -m unittest scripts.test_codex_event_waiter`
- `python3 -m py_compile scripts/codex_event_waiter.py scripts/test_codex_event_waiter.py`
- Focused `ruff` check through an existing or ephemeral environment.
- Attached wait proof with one terminal record and no intermediate model poll.
- Detached wake proof, or an explicit fail-closed `DATA_MISSING` result that
  leaves the experimental path disabled.
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/codex_event_waiter_v1_20260710.md --no-write-report`
- `python3 scripts/agent_job_contract.py check-report-artifacts docs/agent_tasks/codex_event_waiter_v1_20260710.md`
- `python3 scripts/agent_job_contract.py check-closeout docs/agent_tasks/codex_event_waiter_v1_20260710.md`
- Final diff review and fresh `git status --short --untracked-files=all`.

## Definition Of Done

- Attached GitHub and command waits are implemented and focused tests pass.
- Waiting emits one terminal JSON record and an atomic evidence artifact.
- GitHub waits fail closed on head drift and never write to GitHub.
- Command waits use `shell=False` and clean up timed-out children.
- Detached wake-up is either proven and explicitly experimental or disabled
  with a durable evidence-backed follow-up.
- Tenn workflow documentation requires a live recheck after wake-up.
- No forbidden surface is touched.
