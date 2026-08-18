# Validation

## Results

- PASS: `/home/l4nd0/.codex/skills/.system/skill-creator/scripts/quick_validate.py /home/l4nd0/.codex/skills/tenn-issue-closeout`
- PASS: `/home/l4nd0/.codex/skills/.system/skill-creator/scripts/quick_validate.py /home/l4nd0/.codex/skills/tenn-issue-resolution-reviewer`
- PASS: `/home/l4nd0/.codex/skills/.system/skill-creator/scripts/quick_validate.py /home/l4nd0/.codex/skills/tenn-issue-finder`
- PASS: custom hyphen-case/frontmatter check for all edited skill files.
- PASS: YAML parse for all three skill-local `agents/openai.yaml` files.
- PASS: no unfinished placeholder markers in edited files.
- PASS: ASCII check for edited skill, prompt metadata, task, protocol, and report files.
- PASS: `python3 scripts/agent_job_contract.py validate docs/agent_tasks/github_issue_system_protocol_source_candidate_v1_20260525.md`
- PASS: `python3 -m json.tool reports/agent_jobs/github_issue_system_protocol_source_candidate_v1_20260525/status.json`
- PASS: `git diff --check`
- FAIL: `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/github_issue_system_protocol_source_candidate_v1_20260525.md --repo-root .`
  - Reason: unrelated dirty task cards outside this task's allowlist.
- FAIL: `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/github_issue_system_protocol_source_candidate_v1_20260525.md`
  - Reason: unrelated dirty task cards outside this task's allowlist.

## GitHub Mutation

No live GitHub issue, label, milestone, Project, PR, comment, or closure
mutation was performed.
