# Tenn Automation Index

This file indexes Tenn automated audit/proposal jobs. These jobs are intended to improve visibility, not mutate product/runtime systems.

## Operating Rules

- Default execution mode is audit-only.
- Default production data access is false.
- Codex jobs run from `/home/l4nd0/tenn-codex-automations-v1-20260516`.
- The primary inspected worktree is `/home/l4nd0/tenn`, matching the installed user systemd service target. On this host, that symlink resolves through `/home/l4nd0/tenn-runtime` to the active clean-baseline checkout.
- Logs, prompts, and final reports are written under `/home/l4nd0/.codex/automations/tenn/`.
- Mutation-capable work still requires task cards, registry coordination, allowed files, validation, and final reports.
- Only the native `automation-health` timer is persistent across missed calendar events. Codex chat timers use `Persistent=false` to avoid reboot catch-up bursts.

## Timer Templates

This table indexes repository unit templates. Confirm live installed state with
`systemctl --user list-timers 'tenn-codex-*' --all` before claiming a timer is
active on a host.

| Timer | Cadence | Job | Output |
| --- | --- | --- | --- |
| `tenn-codex-automation-health.timer` | Daily 07:45 | Automation Health Monitor | `~/.codex/automations/tenn/reports/*-automation-health.md` |
| `tenn-codex-repo-hygiene.timer` | Daily 08:00 | Repo Hygiene / Collision Scanner | `~/.codex/automations/tenn/reports/*-repo-hygiene.md` |
| `tenn-codex-extraction-regression.timer` | Daily 08:30 | Extraction Regression Scout | `~/.codex/automations/tenn/reports/*-extraction-regression.md` |
| `tenn-codex-bug-regression.timer` | Daily 09:00 | Bug / Regression Finder | `~/.codex/automations/tenn/reports/*-bug-regression.md` |
| `tenn-codex-memory-drift.timer` | Friday 11:00 | Project Memory Drift Scanner | `~/.codex/automations/tenn/reports/*-memory-drift.md` |
| `tenn-codex-doc-drift.timer` | Monday/Wednesday/Friday 12:00 | Documentation Drift Updater | `~/.codex/automations/tenn/reports/*-doc-drift.md` |
| `tenn-codex-future-opportunities.timer` | Tuesday 15:00 | Future Upgrade / Opportunity Scout | `~/.codex/automations/tenn/reports/*-future-opportunities.md` |
| `tenn-codex-daily-closeout.timer` | Daily 20:30 | Daily Closeout / Lock-Up Audit | `~/.codex/automations/tenn/reports/*-daily-closeout.md` |

## Health Checks

The native health monitor checks:

- user timer state
- failed user units
- Codex binary availability
- output root size
- latest prompt/log/report files
- expected report freshness per automation job

The daily closeout job is an end-of-day audit/proposal pass. It summarizes
current worktree, report, timer, PR, issue, and blocker evidence and emits one
next recommended operator prompt. It must not mutate files, GitHub, systemd,
runtime state, data stores, memory stores, model/GPU config, or production data.

## Never Auto-Write

- `financial-engine_v2/backend` extraction logic
- backend route contracts
- `cockpit-ui` product code
- Tenn DBs
- Qdrant
- news DBs
- company memory
- market memory
- gold labels
- canonical financial truth
- runtime/model config
