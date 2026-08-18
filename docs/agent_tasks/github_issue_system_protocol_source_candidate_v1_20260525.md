---
job_id: github_issue_system_protocol_source_candidate_v1_20260525
lane: Reporting
supporting_lanes:
  - Evaluation
  - Repo Hygiene
  - Provenance
  - Query Orchestration
  - Financial Truth
  - Memory
  - Runtime
owner: Codex
allowed_files:
  - docs/agent_tasks/github_issue_system_protocol_source_candidate_v1_20260525.md
  - docs/process/github_issue_system_protocol.md
  - reports/agent_jobs/github_issue_system_protocol_source_candidate_v1_20260525/README.md
  - reports/agent_jobs/github_issue_system_protocol_source_candidate_v1_20260525/status.json
  - reports/agent_jobs/github_issue_system_protocol_source_candidate_v1_20260525/validation.md
  - reports/agent_jobs/github_issue_system_protocol_source_candidate_v1_20260525/diff-check.json
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 3600
output_dir: reports/agent_jobs/github_issue_system_protocol_source_candidate_v1_20260525
mutation_mode: safe_extension
allow_audit_code_changes: true
production_data_access: false
---

# GitHub Issue System Protocol Source Candidate

Mode detail: skill/source-authoring safe_extension.

## Objective

Update Tenn issue-management skills and create a source candidate for GitHub
Issues as Tenn's live actionable backlog.

## Allowed External Skill Writes

These files live outside the Tenn git repository and are not covered by repo
diff validation:

- `/home/l4nd0/.codex/skills/tenn-issue-closeout/SKILL.md`
- `/home/l4nd0/.codex/skills/tenn-issue-resolution-reviewer/SKILL.md`
- `/home/l4nd0/.codex/skills/tenn-issue-finder/SKILL.md`
- `/home/l4nd0/.codex/skills/tenn-issue-closeout/agents/openai.yaml`
- `/home/l4nd0/.codex/skills/tenn-issue-resolution-reviewer/agents/openai.yaml`
- `/home/l4nd0/.codex/skills/tenn-issue-finder/agents/openai.yaml`

## Forbidden

- Product/backend/frontend/runtime code.
- Production DB, Qdrant, news, or memory store mutation.
- Canonical financial truth mutation.
- Parser routing, extraction prompts, or gold-label changes.
- Model/runtime/GPU/service config changes.
- Live GitHub issue, comment, label, milestone, Project, or PR mutation.
- Unrelated dirty files.
- Merge, cherry-pick, rebase, reset, stash, prune, delete, or cleanup.

## Required Outputs

- Updated Tenn issue-management skill files.
- Updated skill-local prompt metadata if needed.
- `docs/process/github_issue_system_protocol.md`
- This task card.
- Report status and validation summary.

## Validation

- Skill frontmatter and hyphen-case name checks.
- YAML parse for skill-local `agents/openai.yaml`.
- No unfinished placeholder markers in edited files.
- ASCII punctuation check for edited skill/protocol files.
- `git diff --check` inside the Tenn repository.
- Task-card validation and diff check where current worktree dirt permits it.
- No live GitHub mutation.

## Hard Stops

Stop if completing the task requires product/runtime/data mutation, live GitHub
mutation during validation, service configuration, forbidden branch operations,
or touching unrelated dirty files.
