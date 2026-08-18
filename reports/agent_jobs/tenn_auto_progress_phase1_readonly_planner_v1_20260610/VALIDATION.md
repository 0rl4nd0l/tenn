# Validation

## Commands Run

| Command | Exit | Notes |
| --- | ---: | --- |
| `pwd` | 0 | Confirmed repo path |
| `git branch --show-current` | 0 | Current branch captured |
| `git rev-parse HEAD` | 0 | Current HEAD captured |
| `git rev-parse --abbrev-ref --symbolic-full-name @{u}` | 0 | Upstream captured |
| `git remote -v` | 0 | Origin captured |
| `git status --short --untracked-files=all` | 0 | Pre-existing unrelated count-24 task card plus new Phase 1 task card |
| `python3 scripts/agent_job_registry.py list-active --read-only --repo-root .` | 0 | Active registry returned empty |
| `python3 scripts/agent_job_contract.py validate docs/agent_tasks/tenn_auto_progress_phase1_readonly_planner_v1_20260610.md` | 0 | Task card valid |
| `gh issue view 291 --repo 0rl4nd0l/tenn --json ...` | 0 | Controlling issue read-only evidence |
| `gh api repos/0rl4nd0l/tenn/milestones --paginate --jq ...` | 0 | Milestones read-only evidence |
| `gh issue list --repo 0rl4nd0l/tenn --state open --label state:ready --json ...` | 0 | Large ready scan; output byte/noise capped |
| `gh issue list --repo 0rl4nd0l/tenn --state open --label lane:repo-hygiene --json ...` | 0 | Repo-hygiene candidates |
| `gh issue list --repo 0rl4nd0l/tenn --state open --label lane:evaluation --json ...` | 0 | Evaluation candidates |
| `gh issue list --repo 0rl4nd0l/tenn --state open --search ... --json ...` | 0 | Returned no additional rows |
| `gh issue view 281 --repo 0rl4nd0l/tenn --json ...` | 0 | Candidate issue body read |
| `gh issue view 234 --repo 0rl4nd0l/tenn --json ...` | 0 | Candidate issue body read |
| `gh issue view 139 --repo 0rl4nd0l/tenn --json ...` | 0 | Alternate candidate issue body read |
| `python3 ... required file existence check` | 0 | Required report files, skill, and task card exist |
| `python3 ... markdown whitespace check` | 0 | 15 markdown files checked; no trailing whitespace or missing final newlines |
| `git diff --check` | 0 | No tracked whitespace errors |
| `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/tenn_auto_progress_phase1_readonly_planner_v1_20260610.md --no-write-report` | 1 | Failed only because pre-existing unrelated `docs/agent_tasks/extraction_count24_approval_packet_current_canonical_v1_20260609.md` is outside this task-card allowlist |
| `python3 scripts/agent_job_contract.py validate docs/agent_tasks/tenn_auto_progress_phase1_readonly_planner_v1_20260610.md` | 0 | Revalidated after edits |
| `find reports/agent_jobs/tenn_auto_progress_phase1_readonly_planner_v1_20260610 -maxdepth 1 -type f -printf '%f\n' \| sort` | 0 | Required report files plus frame files present |
| `git status --ignored --short reports/... .agents/skills/tenn-auto-progress docs/agent_tasks/...` | 0 | Task card untracked; skill and report bundle ignored |
| `git status --short --untracked-files=all` | 0 | Final visible status captured |

## Final Validation

Passed:

- required report files exist
- whitespace check generated markdown
- `git diff --check`
- task-card validation
- final `git status --short --untracked-files=all`

Failed with expected residual risk:

- task-card `check-diff --no-write-report` returned `ok: false` because the
  pre-existing unrelated untracked task card
  `docs/agent_tasks/extraction_count24_approval_packet_current_canonical_v1_20260609.md`
  is outside this job's allowlist.

Final visible status:

```text
?? docs/agent_tasks/extraction_count24_approval_packet_current_canonical_v1_20260609.md
?? docs/agent_tasks/tenn_auto_progress_phase1_readonly_planner_v1_20260610.md
```

Ignored job artifacts:

```text
!! .agents/skills/tenn-auto-progress/
!! reports/agent_jobs/tenn_auto_progress_phase1_readonly_planner_v1_20260610/
```
