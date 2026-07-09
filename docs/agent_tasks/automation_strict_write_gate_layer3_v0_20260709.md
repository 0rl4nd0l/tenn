---
job_id: automation_strict_write_gate_layer3_v0_20260709
lane: Reporting
supporting_lanes:
  - Evaluation
  - Query Orchestration
owner: Codex
approval_required: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/automation_strict_write_gate_layer3_v0_20260709
mutation_mode: safe_extension
production_data_access: false
task_scope: control_plane_only
stacked_on_pr: 493
allowed_files:
  - docs/agent_tasks/automation_strict_write_gate_layer3_v0_20260709.md
  - scripts/automation_write_gate.py
  - scripts/test_automation_write_gate.py
  - reports/agent_jobs/automation_strict_write_gate_layer3_v0_20260709/README.md
  - reports/agent_jobs/automation_strict_write_gate_layer3_v0_20260709/STATE.md
  - reports/agent_jobs/automation_strict_write_gate_layer3_v0_20260709/VALIDATION.md
  - reports/agent_jobs/automation_strict_write_gate_layer3_v0_20260709/diff-check.json
---

# Automation Strict Write Gate Layer 3 V0

## Approval

USER_APPROVED: Orlando approved continuing the automation backlog stack after
PR #493 passed checks.

## Objective

Add a strict manifest-only write gate for automation backlog candidates. The
gate should combine candidate-store records and GitHub dedupe results, decide
whether a future write is eligible, name the exact approval phrase required,
and fail closed when the candidate is unsafe, duplicate, ambiguous, high-risk
without isolation, or missing current dedupe evidence.

## Scope

- Add a stdlib `scripts/automation_write_gate.py` helper.
- Produce machine-readable JSON manifests only.
- Support safe manifest action classes:
  - `open_issue`
  - `comment_existing_issue`
  - `comment_existing_pr`
  - `create_draft_pr`
  - `park_high_risk`
  - `review_only`
- Require exact approval phrases before `may_execute` can be true.
- Keep fuzzy GitHub dedupe matches as review-only, not writes.
- Require explicit isolation metadata before high-risk work can be parked for
  later review.
- Add focused tests using inline JSON and temp files only.

## Out Of Scope

- No GitHub writes by this helper: no issue create/edit/comment/close, PR
  create/edit/comment/merge, label mutation, branch mutation, or workflow
  dispatch.
- No writes to `~/.codex/automations/tenn/state/candidates.jsonl` during this
  implementation or validation.
- No automation-runner prompt changes.
- No systemd timer/service install, daemon reload, enable/start/stop/restart,
  or live automation mutation.
- No DB, Qdrant, Redis, news-store, memory-store, source-PDF, gold-label,
  extraction prompt, backfill, Docker, service, model/GPU, or secret mutation.
- No actual high-risk branch or worktree creation.

## Validation Plan

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/automation_strict_write_gate_layer3_v0_20260709.md`
- initial red test: `python3 -m unittest scripts.test_automation_write_gate`
- green tests: `python3 -m unittest scripts.test_automation_write_gate scripts.test_automation_github_dedupe scripts.test_automation_candidate_store`
- `python3 scripts/automation_write_gate.py --help`
- `python3 scripts/automation_write_gate.py manifest --candidate-json '{"title":"Safe","root_cause":"safe gap","evidence_path":"reports/demo.md","lane":"reporting","risk":"low"}' --dedupe-json '{"status":"new","errors":[]}' --requested-action open_issue --approval-phrase "open issue" --json`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/automation_strict_write_gate_layer3_v0_20260709.md`
- `python3 scripts/agent_job_contract.py check-report-artifacts docs/agent_tasks/automation_strict_write_gate_layer3_v0_20260709.md`
- `python3 scripts/agent_job_contract.py check-closeout docs/agent_tasks/automation_strict_write_gate_layer3_v0_20260709.md`
- `git diff --check`
- `git status --short --untracked-files=all`
