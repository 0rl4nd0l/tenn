# Validation

## Commands Run

| Command | Exit | Notes |
| --- | ---: | --- |
| `git fetch origin migration/clean-runtime-baseline-reconstruct-v1` | 0 | Refreshed current base |
| `git worktree add -b control-plane/auto-progress-issue291-planner-v2-20260612 ... origin/migration/clean-runtime-baseline-reconstruct-v1` | 0 | Created clean current-base worktree |
| `git branch --show-current && git rev-parse HEAD && git rev-parse @{u} && git status --short --untracked-files=all` | 0 | Confirmed clean worktree at merged base |
| `python3 scripts/agent_job_registry.py list-active --read-only --repo-root .` | 0 | Active registry empty; no lock acquired |
| `gh issue view 291 --repo 0rl4nd0l/tenn --json ...` | 0 | Issue #291 inspected |
| `gh issue list --repo 0rl4nd0l/tenn --state open --label state:ready --limit 100 --json ...` | 0 | Open ready issue scan |
| `gh api repos/0rl4nd0l/tenn/milestones --paginate --jq ...` | 0 | Milestone scan |
| `gh issue view 234 --repo 0rl4nd0l/tenn --json ...` | 0 | Top draft candidate inspected |
| `gh issue view 139 --repo 0rl4nd0l/tenn --json ...` | 0 | Alternate control-plane candidate inspected |
| `python3 scripts/agent_job_contract.py validate docs/agent_tasks/tenn_auto_progress_issue291_readonly_planner_v2_20260612.md` | 0 | Task card valid |
| `python3 -m py_compile scripts/auto_progress.py` | 0 | Script compiles |
| `python3 scripts/auto_progress.py triage-issues ... --dry-run` | 0 | Generated issue/milestone/ranking artifacts |
| `python3 scripts/auto_progress.py issue-to-card --issue 234 ... --dry-run` | 0 | Generated #234 context pack and draft task card |

## Final Checks

| Command | Exit | Notes |
| --- | ---: | --- |
| `for f in ...; do test -f "$f"; done` | 0 | All required report files exist |
| `python3 - <<'PY' ... markdown whitespace check ... PY` | 0 | No trailing whitespace in generated markdown |
| `git diff --check` | 0 | No whitespace errors in tracked diff |
| `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/tenn_auto_progress_issue291_readonly_planner_v2_20260612.md --no-write-report` | 0 | Diff is inside task-card allowlist |
| `python3 - <<'PY' ... changed-path guard ... PY` | 0 | Changed files limited to control-plane skill, task card, script, and report bundle |
| `git status --short --untracked-files=all` | 0 | Local uncommitted control-plane changes only |

## Preservation PR Checks

Run on 2026-06-13 after explicit approval to preserve the V2 planner through a
PR.

| Command | Exit | Notes |
| --- | ---: | --- |
| `git fetch origin migration/clean-runtime-baseline-reconstruct-v1` | 0 | Target branch refreshed; current target is `5db45d832722451959bbd19364fe472d18e22127` |
| `git diff --name-status 143cdf1789979aff8a5e6c129d362e75452e8085..origin/migration/clean-runtime-baseline-reconstruct-v1` | 0 | Target advanced through extraction-side paths; no overlap with V2 control-plane paths |
| `git status --short --untracked-files=all` in shared checkout | 0 | Shared checkout still only showed `docs/agent_tasks/extraction_count24_approval_packet_current_canonical_v1_20260609.md` |
| `python3 scripts/agent_job_registry.py list-active --read-only --repo-root .` | 0 | Active registry empty; no lock acquired |
| `gh issue view 291 --repo 0rl4nd0l/tenn --json ...` | 0 | Issue #291 remained open |
| `gh issue view 234 --repo 0rl4nd0l/tenn --json ...` | 0 | Issue #234 remained open and ready |
| `python3 -m py_compile scripts/auto_progress.py` | 0 | Script compiles |
| `python3 scripts/agent_job_contract.py validate docs/agent_tasks/tenn_auto_progress_issue291_readonly_planner_v2_20260612.md` | 0 | Task card valid |
| `python3 - <<'PY' ... repo skill parse ... PY` | 0 | `tenn-auto-progress` parsed as H1-format repo skill |
| `python3 scripts/auto_progress.py triage-issues --repo 0rl4nd0l/tenn --milestone "M0 — Control Plane Hardening" --labels state:ready --risk low,medium --output-dir reports/agent_jobs/tenn_auto_progress_issue291_readonly_planner_v2_20260612/triage_check --dry-run` | 0 | Generated preservation-check issue and milestone scan |
| `python3 scripts/auto_progress.py issue-to-card --repo 0rl4nd0l/tenn --issue 234 --output-dir reports/agent_jobs/tenn_auto_progress_issue291_readonly_planner_v2_20260612/issue234_check --dry-run` | 0 | Generated preservation-check #234 context pack and draft card |

## Final Status Snapshot

```text
 M .agents/skills/tenn-auto-progress/SKILL.md
?? docs/agent_tasks/tenn_auto_progress_issue291_readonly_planner_v2_20260612.md
?? scripts/auto_progress.py
!! reports/agent_jobs/tenn_auto_progress_issue291_readonly_planner_v2_20260612/
```

The report bundle is ignored by repository rules, so `git status --short`
without ignored output does not display it.

## Boundary Confirmation

- No GitHub mutation was performed during the read-only planning slice.
- The later preservation flow is approved only to commit, push this branch, and
  open one PR.
- No product, runtime, data, or extraction paths were modified.
- No services, extraction jobs, broad tests, or dependency installs were run.
- The shared checkout still only shows the unapproved count-24 extraction task
  card as visible dirt.
