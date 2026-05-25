# Branch Hygiene Issue Visibility

Generated: 2026-05-25T17:08:40+10:00

Branch: `safe/github-issue-branch-hygiene-visibility-v1-20260525`
Base HEAD: `dfa76437bebd9e0ec22f6c80ec9ab5e9177a5f4b`

## Summary

This safe-extension updates Tenn's GitHub issue-system protocol and mirrored
issue-management skills so unmerged branch work is visible through GitHub
Issues, PRs, task cards, reports, or merge-parking records instead of silently
aging out.

## Changed Files

- `docs/agent_tasks/branch_hygiene_issue_visibility_v1_20260525.md`
- `docs/process/github_issue_system_protocol.md`
- `docs/process/codex_skill_sources/github_issue_system/tenn-issue-finder/SKILL.md`
- `docs/process/codex_skill_sources/github_issue_system/tenn-issue-finder/agents/openai.yaml`
- `docs/process/codex_skill_sources/github_issue_system/tenn-issue-closeout/SKILL.md`
- `docs/process/codex_skill_sources/github_issue_system/tenn-issue-closeout/agents/openai.yaml`
- `docs/process/codex_skill_sources/github_issue_system/tenn-issue-resolution-reviewer/SKILL.md`
- `docs/process/codex_skill_sources/github_issue_system/tenn-issue-resolution-reviewer/agents/openai.yaml`
- `reports/agent_jobs/branch_hygiene_issue_visibility_v1_20260525/README.md`
- `reports/agent_jobs/branch_hygiene_issue_visibility_v1_20260525/status.json`
- `reports/agent_jobs/branch_hygiene_issue_visibility_v1_20260525/validation.md`
- `reports/agent_jobs/branch_hygiene_issue_visibility_v1_20260525/mirror_sync.md`
- `reports/agent_jobs/branch_hygiene_issue_visibility_v1_20260525/diff-check.json`

External Codex-local skill files updated in place:

- `/home/l4nd0/.codex/skills/tenn-issue-finder/SKILL.md`
- `/home/l4nd0/.codex/skills/tenn-issue-finder/agents/openai.yaml`
- `/home/l4nd0/.codex/skills/tenn-issue-closeout/SKILL.md`
- `/home/l4nd0/.codex/skills/tenn-issue-closeout/agents/openai.yaml`
- `/home/l4nd0/.codex/skills/tenn-issue-resolution-reviewer/SKILL.md`
- `/home/l4nd0/.codex/skills/tenn-issue-resolution-reviewer/agents/openai.yaml`

## Branch Hygiene Sections Added

- Protocol: `Branch Hygiene / Merge Visibility` and `Branch Review Issue Body Template`.
- `tenn-issue-finder`: branch discovery, classification, issue-draft gating, and branch review issue template.
- `tenn-issue-closeout`: merge visibility gate, branch classification before closeout, branch review follow-up body, and stronger merge-parking rules.
- `tenn-issue-resolution-reviewer`: branch readiness, regression, validation, supersession, and parking eligibility review.

## Branch Classifications

- `ACTIVE_LINKED`
- `PARKED_READY_FOR_REVIEW`
- `PARKED_NEEDS_REBASE`
- `BLOCKED_BY_CI`
- `BLOCKED_BY_DEPENDENCY`
- `SUPERSEDED`
- `STALE_UNKNOWN_NEEDS_AUDIT`
- `SAFE_TO_ARCHIVE_CANDIDATE`

## GitHub Mutation

No live GitHub issues, PRs, labels, milestones, Projects, or comments were
mutated for this task.

## DATA_MISSING

- No live GitHub issue/PR duplicate check was performed because this task
  explicitly forbids live GitHub mutation and only required protocol/skill
  updates.
- No branch inventory issue was created in this task; the next recommended
  action is a separate read-only branch hygiene inventory issue/task.

## Validation

See `validation.md`, `mirror_sync.md`, and `diff-check.json`.
