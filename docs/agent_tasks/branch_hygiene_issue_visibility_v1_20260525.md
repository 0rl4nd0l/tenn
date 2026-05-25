---
job_id: branch_hygiene_issue_visibility_v1_20260525
lane: Reporting
supporting_lanes:
  - Repo Hygiene
  - Evaluation
owner: Codex
allowed_files:
  - docs/agent_tasks/branch_hygiene_issue_visibility_v1_20260525.md
  - docs/process/github_issue_system_protocol.md
  - docs/process/codex_skill_sources/github_issue_system/tenn-issue-closeout/SKILL.md
  - docs/process/codex_skill_sources/github_issue_system/tenn-issue-closeout/agents/openai.yaml
  - docs/process/codex_skill_sources/github_issue_system/tenn-issue-finder/SKILL.md
  - docs/process/codex_skill_sources/github_issue_system/tenn-issue-finder/agents/openai.yaml
  - docs/process/codex_skill_sources/github_issue_system/tenn-issue-resolution-reviewer/SKILL.md
  - docs/process/codex_skill_sources/github_issue_system/tenn-issue-resolution-reviewer/agents/openai.yaml
  - reports/agent_jobs/branch_hygiene_issue_visibility_v1_20260525/README.md
  - reports/agent_jobs/branch_hygiene_issue_visibility_v1_20260525/status.json
  - reports/agent_jobs/branch_hygiene_issue_visibility_v1_20260525/validation.md
  - reports/agent_jobs/branch_hygiene_issue_visibility_v1_20260525/mirror_sync.md
  - reports/agent_jobs/branch_hygiene_issue_visibility_v1_20260525/diff-check.json
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 3600
output_dir: reports/agent_jobs/branch_hygiene_issue_visibility_v1_20260525
mutation_mode: safe_extension
allow_audit_code_changes: true
production_data_access: false
---

# Branch Hygiene Issue Visibility

Mode detail: skill/protocol safe_extension.

## Objective

Update Tenn's GitHub issue-system protocol and issue-management skills so
unmerged branch work is classified, parked, linked to issues/PRs, or explicitly
marked `DATA_MISSING` instead of silently aging out.

## Allowed External Skill Writes

These files live outside the Tenn git repository and are not covered by repo
diff validation:

- `/home/l4nd0/.codex/skills/tenn-issue-closeout/SKILL.md`
- `/home/l4nd0/.codex/skills/tenn-issue-closeout/agents/openai.yaml`
- `/home/l4nd0/.codex/skills/tenn-issue-resolution-reviewer/SKILL.md`
- `/home/l4nd0/.codex/skills/tenn-issue-resolution-reviewer/agents/openai.yaml`
- `/home/l4nd0/.codex/skills/tenn-issue-finder/SKILL.md`
- `/home/l4nd0/.codex/skills/tenn-issue-finder/agents/openai.yaml`

## Required Outputs

- Branch Hygiene / Merge Visibility protocol section.
- Branch classifications:
  `ACTIVE_LINKED`, `PARKED_READY_FOR_REVIEW`,
  `PARKED_NEEDS_REBASE`, `BLOCKED_BY_CI`, `BLOCKED_BY_DEPENDENCY`,
  `SUPERSEDED`, `STALE_UNKNOWN_NEEDS_AUDIT`, and
  `SAFE_TO_ARCHIVE_CANDIDATE`.
- Issue-finder branch discovery and branch review draft rules.
- Closeout merge-block parking/linking rules.
- Resolution-reviewer branch readiness and parking review rules.
- Branch review issue body template with existing labels and milestone.
- Report artifacts and validation evidence.

## Forbidden

- Product/backend/frontend/runtime code mutation.
- Production DB, Qdrant, news, or memory store mutation.
- Canonical financial truth mutation.
- Parser routing, extraction prompt, or gold-label changes.
- Model/runtime/GPU/service configuration changes.
- Live GitHub issue, PR, label, milestone, Project, or comment mutation.
- Branch delete, prune, reset, stash, merge, rebase, or cherry-pick.
- Unrelated dirty files.

## Validation

- `quick_validate.py` on all edited external skills.
- YAML parse for edited skill-local and mirrored `agents/openai.yaml`.
- External skills and repo mirrors are byte-for-byte in sync after update.
- Task-card validate/check-diff.
- `git diff --check`.
- `python3 -m json.tool` for status and diff-check report JSON.
- No live GitHub mutation.

## Hard Stops

Stop if completing the task requires product/runtime/data mutation, live GitHub
mutation, forbidden branch operations, service configuration, or touching
unrelated dirty files.
