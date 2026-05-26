# Evidence

## Source Branch And Commit

Read-only commands:

```bash
git show --no-patch --oneline --decorate af69c6fef20070f06d3b57594c9847d2ba98448a
git show --stat --name-status af69c6fef20070f06d3b57594c9847d2ba98448a
git branch --all --contains af69c6fef20070f06d3b57594c9847d2ba98448a
```

Findings:

- Source commit exists: `af69c6fe fix(repo-hygiene): add read-only registry listing`.
- Local branch exists: `safe/registry-readonly-no-lock-list-active-v1-20260525`.
- Exact source commit changed:
  - `scripts/agent_job_registry.py`
  - `scripts/test_agent_job_registry.py`
  - `docs/agent_tasks/registry_readonly_no_lock_list_active_v1_20260525.md`
  - `reports/agent_jobs/registry_readonly_no_lock_list_active_v1_20260525/*`

## Active Baseline Check

Read-only commands:

```bash
git merge-base --is-ancestor af69c6fef20070f06d3b57594c9847d2ba98448a HEAD
python3 scripts/agent_job_registry.py list-active --help
python3 scripts/agent_job_registry.py list-active --read-only --repo-root .
```

Findings:

- `af69c6fe` is not an ancestor of current `HEAD` (`merge-base --is-ancestor` exit `1`).
- Current `list-active --help` exposes only `--repo-root` and `--stale-after-seconds`.
- Current `list-active --read-only --repo-root .` fails with `unrecognized arguments: --read-only`.

## Branch Hygiene

Read-only command:

```bash
git log --oneline --decorate --left-right --cherry-pick HEAD...safe/registry-readonly-no-lock-list-active-v1-20260525
```

Findings:

- The source branch has one unique commit, `af69c6fe`.
- Current HEAD has later unrelated commits, including local-news route and task-card preservation commits.
- Direct integration requires a separate approved integration task; this report did not mutate code or cherry-pick.

## Duplicate Search

Read-only GitHub search found #85 as the active integration tracker.
