# Validation

## Completed

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/system_brief_draft_pr_coverage_fix_v1_20260709.md`
  - exit status: 0
  - result: task card valid
- `python3 scripts/agent_job_registry.py list-active --read-only --repo-root .`
  - exit status: 0
  - result: no active jobs
- red `python3 -m unittest scripts.test_system_brief`
  - exit status: 1
  - result: regression test failed because #491-style system brief draft PR was
    omitted from the brief
- green `python3 -m unittest scripts.test_system_brief`
  - exit status: 0
  - result: 7 tests passed
- `python3 -m py_compile scripts/system_brief.py scripts/test_system_brief.py`
  - exit status: 0
  - result: compile check passed
- `python3 -m unittest scripts.test_system_brief scripts.test_automation_candidate_store scripts.test_automation_github_dedupe scripts.test_automation_write_gate scripts.test_automation_write_executor_plan`
  - exit status: 0
  - result: 39 tests passed
- `python3 scripts/system_brief.py --repo-root . --automation-root /home/l4nd0/.codex/automations/tenn --json`
  - exit status: 0
  - result: live read-only smoke showed #491-#495 as `draft_pr`; older unrelated
    drafts as `stale_draft_pr`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/system_brief_draft_pr_coverage_fix_v1_20260709.md`
  - exit status: 0
  - result: changed files are within `allowed_files`
- `python3 scripts/agent_job_contract.py check-report-artifacts docs/agent_tasks/system_brief_draft_pr_coverage_fix_v1_20260709.md`
  - exit status: 0
  - result: required report artifacts exist
- `python3 scripts/agent_job_contract.py check-closeout docs/agent_tasks/system_brief_draft_pr_coverage_fix_v1_20260709.md`
  - exit status: 0
  - result: closeout check passed
- `git diff --check`
  - exit status: 0
  - result: no tracked-diff whitespace errors
- `rg -n "sk-|api[_-]?key|secret|token|password" scripts/system_brief.py scripts/test_system_brief.py docs/agent_tasks/system_brief_draft_pr_coverage_fix_v1_20260709.md reports/agent_jobs/system_brief_draft_pr_coverage_fix_v1_20260709`
  - exit status: 0
  - result: no secret material; matches were existing token-usage terms and
    explicit safety-boundary text
- `rg -n "issue create|issue comment|pr create|pr comment|git push|systemctl|subprocess\\.run" scripts/system_brief.py scripts/test_system_brief.py`
  - exit status: 0
  - result: only the existing generic read-only command runner matched
- code-reviewer pass
  - result: no critical findings, warnings, or suggestions

## Pending

- CI completion for PR #496 after publication.

## Publication

- `git push -u origin control-plane/system-brief-draft-pr-coverage-fix-v1-20260709`
  - exit status: 1
  - result: local pre-push hook blocked because
    `financial-engine_v2/.venv/bin/ruff` and
    `financial-engine_v2/.venv/bin/pytest` were missing
- `TENN_ALLOW_MISSING_HOOK_TOOLS=1 git push -u origin control-plane/system-brief-draft-pr-coverage-fix-v1-20260709`
  - exit status: 0
  - result: branch pushed; markdown hygiene hook passed
- GitHub connector draft PR creation
  - result: PR #496 opened against
    `control-plane/automation-write-executor-plan-layer4-v0-20260709`
- `gh pr list --repo 0rl4nd0l/tenn --head control-plane/system-brief-draft-pr-coverage-fix-v1-20260709 --json number,title,state,isDraft,mergeStateStatus,url,headRefName,baseRefName,statusCheckRollup`
  - exit status: 0
  - result: PR #496 open draft; `scan` passed; `lint-and-test` in progress
