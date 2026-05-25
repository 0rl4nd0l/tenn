# Validation

## Passed Before Report Creation

- `python3 /home/l4nd0/.codex/skills/.system/skill-creator/scripts/quick_validate.py` passed for:
  - `/home/l4nd0/.codex/skills/tenn-issue-finder`
  - `/home/l4nd0/.codex/skills/tenn-issue-closeout`
  - `/home/l4nd0/.codex/skills/tenn-issue-resolution-reviewer`
  - `docs/process/codex_skill_sources/github_issue_system/tenn-issue-finder`
  - `docs/process/codex_skill_sources/github_issue_system/tenn-issue-closeout`
  - `docs/process/codex_skill_sources/github_issue_system/tenn-issue-resolution-reviewer`
- YAML parse passed for all edited external and repo mirror `agents/openai.yaml` files.
- External skill files and repo mirrors compared equal with `cmp`.
- `git diff --check` passed.
- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/branch_hygiene_issue_visibility_v1_20260525.md` passed.

## Passed After Report Creation

- `python3 -m json.tool reports/agent_jobs/branch_hygiene_issue_visibility_v1_20260525/status.json` passed.
- `python3 -m json.tool reports/agent_jobs/branch_hygiene_issue_visibility_v1_20260525/diff-check.json` passed.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/branch_hygiene_issue_visibility_v1_20260525.md` passed with no disallowed files.
- `git diff --check` passed.
