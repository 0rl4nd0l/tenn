# Evidence

## Current Schedule

Read-only command:

```bash
crontab -l
systemctl --user list-timers '*news*' --all --no-pager
systemctl --user list-unit-files '*news*' --no-pager
```

Findings:

- Crontab contains `0 2 * * * /home/l4nd0/tenn/financial-engine_v2/scripts/nightly_news.sh`.
- User systemd has no matching `*news*` timers or unit files.

## Script Behavior

Read-only inspection of `/home/l4nd0/tenn/financial-engine_v2/scripts/nightly_news.sh` found:

- The script uses `set -euo pipefail`.
- It writes logs under `reports/ops_checks/nightly`.
- It only reaches `summary_json=...` and `finished_at=...` after the fetch and sync phases succeed.
- If fetch exits before sync, the script can leave only early log lines and no summary artifact.

## Latest Artifacts

Read-only commands:

```bash
find /home/l4nd0/tenn/reports/ops_checks/nightly -maxdepth 1 -type f
stat -c '%y %s %n' /home/l4nd0/tenn/reports/ops_checks/nightly/nightly_news_2026-05-26_020001.log
wc -l /home/l4nd0/tenn/reports/ops_checks/nightly/nightly_news_2026-05-26_020001.log
```

Findings:

- Only two nightly files were present: `nightly_news_2026-05-25_020001.log` and `nightly_news_2026-05-26_020001.log`.
- No `.summary.json` files were present.
- The 2026-05-26 log was 240 bytes and 2 lines.
- The two lines were `started_at=2026-05-26T02:00:01+10:00` and `phase=fetch ...`.
- No matching live `nightly_news`, `fetch_daily_news`, `load_news_to_qdrant`, or memo process was found beyond the audit command itself.

## Duplicate Search

Read-only GitHub search found only source issue #81 for the same root cause.
