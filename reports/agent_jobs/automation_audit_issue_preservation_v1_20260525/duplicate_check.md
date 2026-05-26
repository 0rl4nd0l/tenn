# Duplicate Check

All searches were read-only. No GitHub issues, comments, labels, closures, or
PR changes were created.

## GitHub Searches

Repository: `0rl4nd0l/tenn`

Commands:

```bash
gh issue list --repo 0rl4nd0l/tenn --state all --search "automation topology reconciliation OR codex automation docs systemd target" --limit 20
gh issue list --repo 0rl4nd0l/tenn --state all --search "agent_job_registry list-active read-only lock no-lock" --limit 20
gh issue list --repo 0rl4nd0l/tenn --state all --search "nightly_news observability systemd cron summary json" --limit 20
gh issue list --repo 0rl4nd0l/tenn --state all --search "llama-server 8001 ownership provenance systemd runtime" --limit 20
gh pr list --repo 0rl4nd0l/tenn --state all --search "automation topology registry list-active nightly_news llama-server 8001" --limit 20
```

Results:

- Automation topology reconciliation: no matching issue or PR returned.
- Registry read-only/no-lock list-active mode: no matching issue or PR returned.
- nightly_news.sh observability / systemd migration: no matching issue or PR returned.
- llama-server :8001 ownership/provenance audit: no matching issue or PR returned.

## Repo/Report Searches

Related local evidence exists in reports, docs, scripts, and memory, but no
current GitHub tracker was found in the read-only GitHub searches above.

Notable local evidence:

- `/home/l4nd0/.codex/automations/tenn/reports/20260525T080015+1000-repo-hygiene.md`
- `/home/l4nd0/.codex/automations/tenn/reports/20260525T120015+1000-doc-drift.md`
- `/home/l4nd0/tenn/financial-engine_v2/scripts/nightly_news.sh`
- `/home/l4nd0/tenn/reports/ops_checks/nightly/nightly_news_2026-05-25_020001.log`
- `/home/l4nd0/.config/systemd/user/tenn-codex-*.service`
- `/home/l4nd0/.config/systemd/user/llama-cpp-router.service`
- `/home/l4nd0/.config/systemd/user/llama-cpp-qwen25.service`
