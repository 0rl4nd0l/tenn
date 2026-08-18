---
job_id: automation_github_dedupe_layer2_v0_20260709
lane: Reporting
supporting_lanes:
  - Evaluation
  - Query Orchestration
owner: Codex
approval_required: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/automation_github_dedupe_layer2_v0_20260709
mutation_mode: safe_extension
production_data_access: false
task_scope: control_plane_only
stacked_on_pr: 492
allowed_files:
  - docs/agent_tasks/automation_github_dedupe_layer2_v0_20260709.md
  - scripts/automation_github_dedupe.py
  - scripts/test_automation_github_dedupe.py
  - scripts/automation_candidate_store.py
  - scripts/test_automation_candidate_store.py
  - reports/agent_jobs/automation_github_dedupe_layer2_v0_20260709/README.md
  - reports/agent_jobs/automation_github_dedupe_layer2_v0_20260709/STATE.md
  - reports/agent_jobs/automation_github_dedupe_layer2_v0_20260709/VALIDATION.md
  - reports/agent_jobs/automation_github_dedupe_layer2_v0_20260709/diff-check.json
---

# Automation GitHub Dedupe Layer 2 V0

## Approval

USER_APPROVED: Orlando approved continuing the grill-session automation
backlog stack after PR #492 preserved the candidate store layer.

## Objective

Add a read-only GitHub dedupe gate for automation backlog candidates. The gate
should help an automation decide whether a candidate already has a related
issue or draft PR before any future write layer considers creating GitHub
comments, issues, branches, or PRs.

## Scope

- Add a stdlib `scripts/automation_github_dedupe.py` helper.
- Query GitHub through read-only `gh issue list` and `gh pr list` commands.
- Classify candidate overlap as `new`, `duplicate_issue`, `duplicate_pr`,
  `needs_review`, or `data_missing`.
- Prefer exact fingerprint/issue/PR/url/title/root-cause matches over fuzzy
  overlap.
- Return machine-readable JSON with evidence and command provenance.
- Add a candidate-store integration helper that converts high-confidence
  duplicate classifications into append-only duplicate candidate records.
- Add focused tests with mocked command runners only.

## Out Of Scope

- No real GitHub writes by this helper: no issue create/edit/comment/close,
  PR create/edit/comment/merge, label mutation, branch mutation, or workflow
  dispatch.
- No writes to `~/.codex/automations/tenn/state/candidates.jsonl` during this
  implementation or validation.
- No automation-runner prompt changes.
- No systemd timer/service install, daemon reload, enable/start/stop/restart,
  or live automation mutation.
- No DB, Qdrant, Redis, news-store, memory-store, source-PDF, gold-label,
  extraction prompt, backfill, Docker, service, model/GPU, or secret mutation.
- No high-risk experiment branch creation by an automation.

## Validation Plan

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/automation_github_dedupe_layer2_v0_20260709.md`
- `python3 -m unittest scripts.test_automation_github_dedupe scripts.test_automation_candidate_store`
- `python3 scripts/automation_github_dedupe.py --help`
- `python3 scripts/automation_github_dedupe.py check --repo 0rl4nd0l/tenn --title "Automation candidate store" --root-cause "candidate state suppression" --label state:ready --json`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/automation_github_dedupe_layer2_v0_20260709.md`
- `python3 scripts/agent_job_contract.py check-report-artifacts docs/agent_tasks/automation_github_dedupe_layer2_v0_20260709.md`
- `python3 scripts/agent_job_contract.py check-closeout docs/agent_tasks/automation_github_dedupe_layer2_v0_20260709.md`
- `git diff --check`
- `git status --short --untracked-files=all`
