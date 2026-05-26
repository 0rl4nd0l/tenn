# GitHub Issue Drafts From Automation Audit

These are issue-ready drafts. They were not created on GitHub in this task
because the task card is report-only and does not authorize live GitHub
mutation.

## Draft 1: Reconcile Tenn Codex automation topology across installed units, docs, templates, and runner defaults

## Task
`automation_topology_reconciliation_v1_20260525`

## Lane
Primary lane: Reporting

Supporting lanes: Repo Hygiene, Ops

Mode: audit_only / safe_extension

## Finding
Installed Tenn Codex automation units target `/home/l4nd0/tenn`, while the
automation worktree docs/templates and runner defaults still reference
`/home/l4nd0/tenn-fast-dev-storage-v1`; the primary runtime repo also lacks the
repo-facing automation docs/templates.

## Summary
In plain language:
- What the issue is or was: Tenn's automation map is split between what is installed on the host and what the repo/worktree documentation says should be installed.
- What it impacted: Operator confidence, future automation changes, and the ability to tell which worktree a scheduled Codex audit is actually inspecting.
- How it restricted Tenn: New agents can follow stale docs or templates and make changes against the wrong checkout, while the installed systemd units are already pointing somewhere else.
- Why fixing it is a meaningful step forward: A single accurate automation topology prevents duplicated schedulers, wrong-worktree audits, and stale handoffs before GitHub issue automation is expanded.

## Evidence
- `/home/l4nd0/.config/systemd/user/tenn-codex-repo-hygiene.service`: installed unit sets `TENN_CODEX_AUTOMATION_TARGET_WORKTREE=/home/l4nd0/tenn`.
- `/home/l4nd0/tenn-codex-automations-v1-20260516/docs/dev/automation_index.md`: documents the inspected worktree as `/home/l4nd0/tenn-fast-dev-storage-v1`.
- `/home/l4nd0/tenn-codex-automations-v1-20260516/scripts/codex_automation_runner.py`: default target worktree is `/home/l4nd0/tenn-fast-dev-storage-v1`.
- `/home/l4nd0/.codex/automations/tenn/reports/20260525T120015+1000-doc-drift.md`: confirms installed units and repo docs/templates disagree.
- Local check: `/home/l4nd0/tenn/docs/dev` and `/home/l4nd0/tenn/systemd/user` are absent.
- GitHub duplicate check: no matching issue or PR returned for automation topology / codex automation docs / systemd target searches.

## Why this matters
Automation should be boring and inspectable. If installed units, docs, runner
defaults, and repo templates disagree, future operators cannot tell whether a
scheduled report is current truth, stale worktree evidence, or a local-only
override.

## Required task card
`docs/agent_tasks/automation_topology_reconciliation_v1_20260525.md`

## Required output
`reports/agent_jobs/automation_topology_reconciliation_v1_20260525/`

## Allowed files / surfaces
- `docs/agent_tasks/automation_topology_reconciliation_v1_20260525.md`
- `reports/agent_jobs/automation_topology_reconciliation_v1_20260525/**`
- Documentation under `docs/dev/` if the task is approved as docs safe-extension.
- Systemd template files only if the task explicitly allows template alignment.

## Forbidden files / surfaces
- production DB/Qdrant/news/memory
- canonical financial truth
- parser routing
- extraction prompts
- gold labels
- runtime/model/GPU/service config
- installed user systemd unit mutation unless explicitly approved
- unrelated dirty work

## Acceptance criteria
- Installed unit targets, runner defaults, and documentation are reconciled or the intentional local override is documented.
- Primary repo either contains the authoritative automation docs/templates or points to the automation worktree as the durable source.
- No new scheduler is introduced.
- No live service state is changed unless separately approved.

## Validation
- `systemctl --user cat 'tenn-codex-*' --no-pager`
- `systemctl --user list-timers 'tenn-codex-*' --all --no-pager`
- `git diff --check`
- task-card validate/check-diff
- focused docs/template grep for stale `/home/l4nd0/tenn-fast-dev-storage-v1`

## Hard stops
- Any required installed service mutation without explicit approval.
- Any product/runtime/data mutation.
- Any attempt to add a second scheduler instead of reconciling the existing timer/report stack.

## Draft 2: Add read-only/no-lock mode for agent_job_registry.py list-active

## Task
`registry_list_active_readonly_mode_v1_20260525`

## Lane
Primary lane: Repo Hygiene

Supporting lanes: Reporting, Ops

Mode: safe_extension

## Finding
Audit-only Codex jobs need to read active agent jobs, but
`scripts/agent_job_registry.py list-active` can try to create a shared registry
lock, causing read-only automation reports to mark registry truth as
`DATA_MISSING`.

## Summary
In plain language:
- What the issue is or was: A command that should be safe for audits can need write access just to list active jobs.
- What it impacted: Repo hygiene reports, collision checks, and confidence that automated audits are not racing live agent work.
- How it restricted Tenn: Read-only automation cannot reliably answer "is another agent active?" and must downgrade to `DATA_MISSING`.
- Why fixing it is a meaningful step forward: A no-lock read mode gives every audit job a trustworthy collision check without mutating registry state.

## Evidence
- `/home/l4nd0/.codex/automations/tenn/reports/20260525T080015+1000-repo-hygiene.md`: records `agent_job_registry.py list-active` failing in read-only mode trying to create `.git/tenn-agent-registry/.lock`.
- `/home/l4nd0/.codex/automations/tenn/reports/20260525T120015+1000-doc-drift.md`: records registry state as `DATA_MISSING` for the same read-only lock behavior.
- Current interactive command `python3 scripts/agent_job_registry.py list-active` succeeds when not sandboxed read-only, showing the problem is specifically read-only automation compatibility.
- GitHub duplicate check: no matching issue or PR returned for `agent_job_registry list-active read-only lock no-lock`.

## Why this matters
The task-card/registry system is the control plane for avoiding overlapping
agent work. Audit-only jobs should be able to inspect it without taking locks
or requiring write access.

## Required task card
`docs/agent_tasks/registry_list_active_readonly_mode_v1_20260525.md`

## Required output
`reports/agent_jobs/registry_list_active_readonly_mode_v1_20260525/`

## Allowed files / surfaces
- `docs/agent_tasks/registry_list_active_readonly_mode_v1_20260525.md`
- `reports/agent_jobs/registry_list_active_readonly_mode_v1_20260525/**`
- `scripts/agent_job_registry.py`
- `scripts/test_agent_job_registry.py`
- related registry docs if present

## Forbidden files / surfaces
- production DB/Qdrant/news/memory
- canonical financial truth
- parser routing
- extraction prompts
- gold labels
- runtime/model/GPU/service config
- unrelated dirty work

## Acceptance criteria
- `list-active` can run in a read-only context without trying to create a lock.
- Existing write/claim/release registry operations still take the appropriate locks.
- Tests cover read-only list behavior and write-mode locking behavior.
- Automation reports no longer need to mark active registry jobs as `DATA_MISSING` solely because of read-only filesystem constraints.

## Validation
- focused registry unit tests
- `python3 scripts/agent_job_registry.py list-active`
- a read-only/sandbox simulation if available
- task-card validate/check-diff
- `git diff --check`

## Hard stops
- Any change that weakens lock safety for claim/release/write operations.
- Any hidden fallback that silently ignores unreadable registry state.
- Any product/runtime/data mutation.

## Draft 3: Harden nightly_news.sh observability and migrate scheduling out of raw cron

## Task
`nightly_news_observability_systemd_migration_v1_20260525`

## Lane
Primary lane: Ops

Supporting lanes: Reporting, Query Orchestration

Mode: audit_only / safe_extension

## Finding
The nightly news cron job appears to start but not complete observably. The
latest log contains only startup/fetch lines, with no sync phase, no
`finished_at`, and no summary JSON.

## Summary
In plain language:
- What the issue is or was: Tenn's nightly news job can fail or stop early without leaving a clear final status.
- What it impacted: News ingestion, Qdrant/news sync visibility, memo extraction follow-up, and operator confidence in daily data freshness.
- How it restricted Tenn: When the job does not write a summary or exit status, downstream agents cannot tell whether the pipeline succeeded, failed, or only fetched partial data.
- Why fixing it is a meaningful step forward: Better observability turns a silent nightly pipeline into a trustworthy operational surface before broader automation depends on it.

## Evidence
- Crontab entry: `0 2 * * * /home/l4nd0/tenn/financial-engine_v2/scripts/nightly_news.sh`.
- `/home/l4nd0/tenn/financial-engine_v2/scripts/nightly_news.sh`: fetch phase at lines invoking `scripts/fetch_daily_news.py`; sync phase and summary emit later in the same script.
- `/home/l4nd0/tenn/reports/ops_checks/nightly/nightly_news_2026-05-25_020001.log`: contains only start/fetch lines.
- No `nightly_news_2026-05-25_020001.summary.json` was found in the nightly report directory.
- No matching running `nightly_news`, `fetch_daily_news`, `load_news_to_qdrant`, or memo backfill process was found during audit.
- GitHub duplicate check: no matching issue or PR returned for `nightly_news observability systemd cron summary json`.

## Why this matters
News is part of Tenn's current-context and retrieval surface. A silent or
half-observed nightly job can make the system look stale or incomplete without
giving operators enough evidence to repair the right phase.

## Required task card
`docs/agent_tasks/nightly_news_observability_systemd_migration_v1_20260525.md`

## Required output
`reports/agent_jobs/nightly_news_observability_systemd_migration_v1_20260525/`

## Allowed files / surfaces
- `docs/agent_tasks/nightly_news_observability_systemd_migration_v1_20260525.md`
- `reports/agent_jobs/nightly_news_observability_systemd_migration_v1_20260525/**`
- `financial-engine_v2/scripts/nightly_news.sh`
- focused ops docs or systemd timer template only if explicitly approved

## Forbidden files / surfaces
- production DB/Qdrant/news/memory direct mutation
- canonical financial truth
- parser routing
- extraction prompts
- gold labels
- model/runtime/GPU/service config
- broad refetch, reindex, Qdrant wipe/delete, or DB reset
- installed crontab/systemd mutation unless explicitly approved
- unrelated dirty work

## Acceptance criteria
- The script always records exit status and emits a final summary artifact even on failure.
- stderr is captured in the log.
- Fetch, sync, memo dispatch/backfill, and finish/failure phases are distinguishable.
- A systemd timer migration plan or approved implementation replaces raw cron without introducing a second active schedule.
- No broad refetch or production data repair is performed by the observability task.

## Validation
- shell syntax check
- dry-run or bounded no-mutation smoke if supported
- forced failure smoke proving final status is written
- task-card validate/check-diff
- `git diff --check`
- final crontab/systemd state evidence if scheduler mutation is approved

## Hard stops
- Any broad news refetch, DB reset, Qdrant wipe, or reindex requirement.
- Any scheduler mutation without explicit approval.
- Any production data mutation outside the existing job's normal approved path.

## Draft 4: Audit llama-server :8001 ownership and runtime provenance

## Task
`llama_server_8001_ownership_provenance_audit_v1_20260525`

## Lane
Primary lane: Ops

Supporting lanes: Evaluation, Query Orchestration

Mode: audit_only

## Finding
The `:8001` llama-server runtime is live, but the visible user systemd units
`llama-cpp-router.service` and `llama-cpp-qwen25.service` are disabled/inactive.
The runtime ownership path is unclear.

## Summary
In plain language:
- What the issue is or was: Tenn has a working local LLM server on port 8001, but systemd does not show it as owned by the expected active service.
- What it impacted: Runtime provenance, restart safety, GPU/process guard interpretation, and confidence in which launcher controls model serving.
- How it restricted Tenn: Operators can see the model endpoint working but cannot safely restart, debug, or document it without risking the wrong service or manual process.
- Why fixing it is a meaningful step forward: Clear ownership of `:8001` makes local LLM routing safer and reduces accidental duplicate llama-server processes or stale service conclusions.

## Evidence
- `ss -ltnp` showed `llama-server` listening on `0.0.0.0:8001`.
- `ps` showed parent PID under user systemd and a router-owned child worker on an ephemeral port.
- `systemctl --user status llama-cpp-router.service llama-cpp-qwen25.service` showed both units inactive/dead and disabled.
- `systemctl` logs for `llama-cpp-qwen25.service` showed repeated `Unknown key name 'StartLimitIntervalSec' in section 'Service'`.
- Repo memory and docs indicate `:8001` is the canonical local LLM endpoint, but current live ownership was not proven as systemd-managed.
- GitHub duplicate check: no matching issue or PR returned for `llama-server 8001 ownership provenance systemd runtime`.

## Why this matters
The local LLM endpoint is shared by chat, extraction-adjacent checks, Codex
local routing, and operator workflows. If the owning launcher is unclear,
agents can restart the wrong thing or misclassify healthy router-owned child
workers as rogue processes.

## Required task card
`docs/agent_tasks/llama_server_8001_ownership_provenance_audit_v1_20260525.md`

## Required output
`reports/agent_jobs/llama_server_8001_ownership_provenance_audit_v1_20260525/`

## Allowed files / surfaces
- `docs/agent_tasks/llama_server_8001_ownership_provenance_audit_v1_20260525.md`
- `reports/agent_jobs/llama_server_8001_ownership_provenance_audit_v1_20260525/**`
- docs-only runtime provenance notes if separately approved

## Forbidden files / surfaces
- model/runtime/GPU/service config mutation
- starting, stopping, or restarting `llama-server`
- product/backend/frontend code
- production DB/Qdrant/news/memory
- canonical financial truth
- parser routing
- extraction prompts
- gold labels
- unrelated dirty work

## Acceptance criteria
- Current `:8001` parent/child process topology is recorded.
- The active launcher path is identified or marked `DATA_MISSING` with exact missing evidence.
- Systemd unit state is reconciled with live process state.
- The report states whether `:8001` is systemd-owned, manually launched, or launcher-owned through another path.
- No runtime processes are restarted or killed.

## Validation
- `ss -ltnp | rg ':8001'`
- `ps -eo pid,ppid,stat,etime,cmd | rg 'llama-server|run_llama'`
- `systemctl --user status llama-cpp-router.service llama-cpp-qwen25.service --no-pager`
- `journalctl --user -u llama-cpp-router.service -u llama-cpp-qwen25.service --since <date> --no-pager`
- task-card validate/check-diff
- `git diff --check`

## Hard stops
- Any restart/kill/start action.
- Any service or runtime config edit.
- Any assumption that a live port means systemd ownership without process evidence.
