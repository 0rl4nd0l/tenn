---
job_id: automation_candidate_store_layer1_v0_20260709
lane: Reporting
supporting_lanes:
  - Evaluation
  - Query Orchestration
owner: Codex
approval_required: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/automation_candidate_store_layer1_v0_20260709
mutation_mode: safe_extension
production_data_access: false
task_scope: control_plane_only
stacked_on_pr: 491
allowed_files:
  - docs/agent_tasks/automation_candidate_store_layer1_v0_20260709.md
  - scripts/automation_candidate_store.py
  - scripts/test_automation_candidate_store.py
  - scripts/system_brief.py
  - scripts/test_system_brief.py
  - reports/agent_jobs/automation_candidate_store_layer1_v0_20260709/README.md
  - reports/agent_jobs/automation_candidate_store_layer1_v0_20260709/STATE.md
  - reports/agent_jobs/automation_candidate_store_layer1_v0_20260709/VALIDATION.md
  - reports/agent_jobs/automation_candidate_store_layer1_v0_20260709/diff-check.json
---

# Automation Candidate Store Layer 1 V0

## Approval

USER_APPROVED: Orlando approved the next grill-session layer after PR #491
preserved the Tenn system brief helper: candidate store plus suppression.

## Objective

Add the first repo-side implementation of the automation backlog candidate
store. The store should provide deterministic fingerprints, append-only JSONL
state, TTL-based suppression defaults, and read-only list/summarize behavior
that the system brief can consume without mutating host automation state.

## Scope

- Add a stdlib `scripts/automation_candidate_store.py` helper.
- Support deterministic candidate fingerprints from job/lane/evidence/root
  cause plus optional issue, PR, source commit, and evidence hash.
- Support append-only JSONL records with latest-record resolution by
  fingerprint.
- Apply suppression defaults for duplicate, rejected, deferred, data-missing,
  needs-spec, and failed-validation states.
- Resurface suppressed records when evidence hash or linked-state hash changes.
- Add focused tests for fingerprint stability, TTL defaults, latest-record
  resolution, suppression/resurface behavior, CLI upsert/list behavior, and
  system-brief integration.
- Update `scripts/system_brief.py` to consume the candidate-store helper when
  the host-local state file exists.

## Out Of Scope

- No writes to `~/.codex/automations/tenn/state/candidates.jsonl` during this
  implementation or validation.
- No automation-runner prompt changes.
- No GitHub issue, PR, label, comment, close, reopen, merge, push, or branch
  cleanup beyond publishing this code branch if approved.
- No systemd timer/service install, daemon reload, enable/start/stop/restart, or
  live automation mutation.
- No DB, Qdrant, Redis, news-store, memory-store, source-PDF, gold-label,
  extraction prompt, backfill, Docker, service, model/GPU, or secret mutation.
- No safe-fix draft PR creation by an automation.
- No high-risk experiment branch creation by an automation.

## Validation Plan

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/automation_candidate_store_layer1_v0_20260709.md`
- `python3 -m unittest scripts.test_automation_candidate_store scripts.test_system_brief`
- `python3 scripts/automation_candidate_store.py --help`
- `python3 scripts/automation_candidate_store.py fingerprint --job demo --lane reporting --evidence-path reports/demo.md --root-cause "demo"`
- `python3 scripts/system_brief.py --repo-root /home/l4nd0/tenn-automation-candidate-store-layer1-v0-20260709 --automation-root /home/l4nd0/.codex/automations/tenn --json`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/automation_candidate_store_layer1_v0_20260709.md`
- `python3 scripts/agent_job_contract.py check-report-artifacts docs/agent_tasks/automation_candidate_store_layer1_v0_20260709.md`
- `python3 scripts/agent_job_contract.py check-closeout docs/agent_tasks/automation_candidate_store_layer1_v0_20260709.md`
- `git diff --check`
- `git status --short --untracked-files=all`
