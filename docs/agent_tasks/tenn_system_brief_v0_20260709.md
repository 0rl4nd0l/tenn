---
job_id: tenn_system_brief_v0_20260709
lane: Reporting
supporting_lanes:
  - Evaluation
  - Query Orchestration
owner: Codex
approval_required: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/tenn_system_brief_v0_20260709
mutation_mode: safe_extension
production_data_access: false
task_scope: control_plane_only
approved_external_artifacts:
  - /home/l4nd0/.codex/skills/tenn-system-brief/SKILL.md
  - /home/l4nd0/.codex/skills/tenn-system-brief/agents/openai.yaml
allowed_files:
  - docs/agent_tasks/tenn_system_brief_v0_20260709.md
  - scripts/system_brief.py
  - scripts/test_system_brief.py
  - reports/agent_jobs/tenn_system_brief_v0_20260709/README.md
  - reports/agent_jobs/tenn_system_brief_v0_20260709/STATE.md
  - reports/agent_jobs/tenn_system_brief_v0_20260709/VALIDATION.md
  - reports/agent_jobs/tenn_system_brief_v0_20260709/diff-check.json
---

# Tenn System Brief V0

## Approval

USER_APPROVED: Orlando approved the first system-brief slice after the
automation audit and grill-me session. The approved scope is a read-only
conversation starter skill plus a repo helper that reviews work needing
approval or review.

## Objective

Create a Tenn session-start briefing flow that can be run when opening Codex.
It should inspect current control-plane evidence and produce a prioritized,
conversational queue of review or approval work without mutating GitHub,
runtime state, timers, reports, data stores, or product surfaces.

## Scope

- Add a read-only `scripts/system_brief.py` helper.
- Surface the highest-priority current item across automation candidates,
  report-review markers, automation draft PRs, eligible `state:ready` GitHub
  issues, parked experiment branches, token anomalies, and stale reports.
- Degrade unavailable external evidence to `DATA_MISSING` queue items rather
  than failing the brief.
- Add focused tests for prioritization, eligible issue filtering, missing GitHub
  handling, marker handling, and output shape.
- Add a host Codex skill at
  `/home/l4nd0/.codex/skills/tenn-system-brief/SKILL.md` that instructs Codex
  to run the helper read-only first and ask for explicit mutation language
  before launching any follow-up workflow.
- Record local report artifacts for this implementation.

## Out Of Scope

- No GitHub issue, PR, label, comment, close, reopen, merge, push, or branch
  cleanup.
- No systemd timer/service install, daemon reload, enable/start/stop/restart, or
  live automation mutation.
- No DB, Qdrant, Redis, news-store, memory-store, source-PDF, gold-label,
  extraction prompt, backfill, Docker, service, model/GPU, or secret mutation.
- No high-risk experiment branch creation.
- No safe-fix draft PR creation.
- No report-review marker backfill.
- No broad automation-runner behavior change.
- No default write artifact from the brief helper.

## Validation Plan

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/tenn_system_brief_v0_20260709.md`
- `python3 -m unittest scripts.test_system_brief`
- `python3 scripts/system_brief.py --repo-root /home/l4nd0/tenn --automation-root /home/l4nd0/.codex/automations/tenn --json`
- `python3 scripts/system_brief.py --repo-root /home/l4nd0/tenn --automation-root /home/l4nd0/.codex/automations/tenn`
- `python3 /home/l4nd0/.codex/skills/.system/skill-creator/scripts/quick_validate.py /home/l4nd0/.codex/skills/tenn-system-brief`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/tenn_system_brief_v0_20260709.md`
- `python3 scripts/agent_job_contract.py check-report-artifacts docs/agent_tasks/tenn_system_brief_v0_20260709.md`
- `python3 scripts/agent_job_contract.py check-closeout docs/agent_tasks/tenn_system_brief_v0_20260709.md`
- `git diff --check`
- `git status --short --untracked-files=all`
