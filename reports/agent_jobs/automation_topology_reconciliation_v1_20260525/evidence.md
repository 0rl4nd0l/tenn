# Evidence

## Current Repo

- Worktree: `/home/l4nd0/tenn-issue-resolution-batch-v1-20260526`
- Branch: `codex/long-running-issue-resolution-batch-v1-20260526`
- Base HEAD: `5a902c7e84aabc103914145de0feec569dd5efec`

## Installed Units

Read-only command:

```bash
systemctl --user cat 'tenn-codex-*' --no-pager
systemctl --user list-timers 'tenn-codex-*' --all --no-pager
systemctl --user list-units 'tenn-codex-*' --all --no-pager
```

Findings:

- Seven `tenn-codex-*` timers are loaded and active/waiting.
- Installed service files use `WorkingDirectory=/home/l4nd0/tenn-codex-automations-v1-20260516`.
- Installed service files set `TENN_CODEX_AUTOMATION_TARGET_WORKTREE=/home/l4nd0/tenn`.
- Latest timer samples show the automation-health, repo-hygiene, extraction-regression, bug-regression, doc-drift, future-opportunities, and memory-drift timers scheduled.

## Repo And Automation Worktree Mismatch

Read-only command:

```bash
rg -n "/home/l4nd0/tenn-fast-dev-storage-v1|/home/l4nd0/tenn|tenn-codex|automation" \
  docs/dev systemd/user .github scripts docs/process
rg -n "/home/l4nd0/tenn-fast-dev-storage-v1|/home/l4nd0/tenn|tenn-codex|automation" \
  /home/l4nd0/tenn-codex-automations-v1-20260516/docs/dev \
  /home/l4nd0/tenn-codex-automations-v1-20260516/systemd/user \
  /home/l4nd0/tenn-codex-automations-v1-20260516/scripts
```

Findings:

- This baseline does not have repo-local `docs/dev` or `systemd/user` automation docs/templates.
- `/home/l4nd0/tenn-codex-automations-v1-20260516/docs/dev/automation_index.md` still says the primary inspected worktree is `/home/l4nd0/tenn-fast-dev-storage-v1`.
- `/home/l4nd0/tenn-codex-automations-v1-20260516/scripts/codex_automation_runner.py` defaults `TARGET_WORKTREE` to `/home/l4nd0/tenn-fast-dev-storage-v1`.
- Automation worktree `systemd/user/tenn-codex-*.service` templates still set `TENN_CODEX_AUTOMATION_TARGET_WORKTREE=/home/l4nd0/tenn-fast-dev-storage-v1`.

## Duplicate Search

Read-only GitHub search found only source issue #79 for the same root cause.
