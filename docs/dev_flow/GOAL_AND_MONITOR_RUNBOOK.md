# Goal And Monitor Runbook

Status: report-only audit. This file distinguishes repo-backed Tenn behavior from host-only Codex slash-goal behavior.

Verified from commit `154888ecca6220ab598efcd140a2c2b62fca3da7`.

## Short Answer

`/goal` is Codex/host behavior, not Tenn repo code. The Tenn repo provides `tenn-goal-report`, task cards, report bundles, handoff templates, and the Runtime Functionality Proof policy.

No repo-backed `/goal monitor` implementation was found. A host-only command named `codex-goal-monitor` exists on this machine and is read-only/warning-oriented. It must be labeled `HOST_ONLY` in Tenn docs and reports.

## What Happens When Orlando Uses `/goal`

When Orlando starts or resumes a slash-goal session, Codex host state may track the active objective, status, and token usage outside the repo. In this environment, the current Codex goal tool surface reported no active goal for this thread:

```bash
codex-goal-monitor --current --json
```

The current audit session also had no active API goal when queried through the available Codex goal tool.

Repo behavior begins only after Codex is operating in the Tenn checkout:

1. Read `AGENTS.md`.
2. Read the relevant repo-backed skill under `.agents/skills/<skill>/SKILL.md`.
3. Create or validate a task card for any mutation.
4. Write state into `reports/agent_jobs/<job_id>/`.
5. Use `tenn-goal-report` conventions for long-running status.
6. Use `tenn-handoff` before pausing, context reset, or session transfer.

## Host Behavior Versus Repo Behavior

| Area | Owner | Evidence | Status |
| --- | --- | --- | --- |
| Slash command `/goal` | Codex host | Goal state exists outside this repo when a goal is active. | HOST_ONLY |
| `codex-goal-monitor` | Host-local Codex tooling | Command exists at `/home/l4nd0/.local/bin/codex-goal-monitor`; help and `--current --json` worked. | HOST_ONLY |
| `codex-goal-handoff` | Host-local Codex tooling | Command exists and prints host handoff usage. | HOST_ONLY |
| Host goal database | Host-local Codex state | Prior repo reports identify `~/.codex/goals_1.sqlite` as the slash-goal state source. | HOST_ONLY |
| Repo long-goal reporting | Tenn repo | `.agents/skills/tenn-goal-report/SKILL.md` and report templates. | PARTIAL |
| Repo Stop hook | Tenn repo plus Codex host hook loader | `.codex/hooks.json` runs `scripts/agent_job_hook.py`. | IMPLEMENTED |
| Runtime Functionality Proof | Tenn repo policy and docs checker | `AGENTS.md` and `scripts/check_runtime_functionality_proof_docs.py`. | IMPLEMENTED |

## What `tenn-goal-report` Implements

`tenn-goal-report` is a repo-backed reporting protocol for long-running Tenn work. It gives Codex a way to keep a durable report of:

- current objective and exact scope;
- task card and allowlist;
- latest validation state;
- `WAITING_ON_USER` state and reason;
- completed work versus remaining work;
- handoff and next prompt.

It does not implement the `/goal` slash command. It does not run a daemon, timer, or hook. It does not automatically stop Codex when a goal is complete or blocked.

Use it like this:

```text
Use tenn-goal-report. Read .agents/skills/tenn-goal-report/SKILL.md fully first.
Keep reports/agent_jobs/<job_id>/README.md current and do not claim DONE without the relevant proof.
```

## Is There A Real `/goal monitor` Implementation?

Repo status: `NOT_FOUND`.

This audit found no Tenn repo command, script, skill, hook, daemon, or timer that implements `/goal monitor`.

Host status: `HOST_ONLY`.

The host command exists:

```bash
codex-goal-monitor --help
codex-goal-monitor --current --json
```

The host command is useful as extra evidence, but it is not repo-backed Tenn functionality. Treat it as advisory unless a separate host automation task proves stronger behavior.

## Monitor Daemons, Timers, And Hooks

| Surface | Finding | Status |
| --- | --- | --- |
| Repo `/goal monitor` daemon | Not found. | NOT_FOUND |
| Repo `/goal monitor` timer | Not found. | NOT_FOUND |
| Repo `/goal monitor` hook | Not found. | NOT_FOUND |
| Repo Codex Stop hook | Exists, but validates task card, registry, and diff contract. It is not a goal monitor. | IMPLEMENTED |
| Host `codex-goal-monitor` | Exists and is read-only/warning-oriented. | HOST_ONLY |
| Host systemd Tenn Codex timers | Timers exist for host automation, but no `/goal monitor` timer was found. | HOST_ONLY |
| Legacy `.claude/monitors` | Claude-era monitor scripts exist. They are not Codex `/goal monitor`. | STALE |

## Where Reports Are Written

Tenn repo reports should be written under:

```text
reports/agent_jobs/<job_id>/
```

For a long goal, the minimum useful report state is:

- `README.md` with objective, scope, status, latest validation, and next action;
- `VALIDATION.md` with commands and results;
- `HANDOFF.md` and `HANDOFF_NEXT_GOAL.md` when pausing or transferring;
- any task-specific evidence files listed in the task card.

Host goal monitor output is not a Tenn report by default. It prints to stdout or JSON. Host handoff tooling may write under `/tmp`, but those files are not repo artifacts unless explicitly copied into an approved report bundle.

## Automatic Versus Manual

| Action | Automatic? | Notes |
| --- | --- | --- |
| Slash-goal host state | Host-dependent | Automatic only when the Codex host slash-goal flow is active. |
| `tenn-goal-report` state updates | No | Codex must update the report manually. |
| Task-card validation | Hook-dependent | Automatic only if repo Codex hooks load; otherwise run manually. |
| Registry read-only check | Hook-dependent | Automatic only through hooks; always safe to run manually. |
| Runtime Functionality Proof | No | Must be collected and shown before `DONE` for runtime/product/data work. |
| Handoff generation | No | Use `tenn-handoff` deliberately. |

## What Can Continue Without Orlando

Codex can continue without Orlando when all of these are true:

- the task card exists and validates;
- the work remains inside the allowed files and lanes;
- the registry check does not show an overlap conflict;
- no product/runtime/data/extraction/count-24 or host-global mutation is needed;
- any OpenCode worker is read-only or otherwise explicitly permitted;
- validation commands are available;
- the next action does not require an owner decision.

## What Must Stop With `WAITING_ON_USER`

Use `WAITING_ON_USER` when continuing would require:

- product/runtime/data/extraction/count-24 mutation outside the task card;
- host-global Codex mutation, including skill sync `--apply`;
- GitHub issue/PR creation not permitted by the task card;
- merge, rebase, cherry-pick, worktree deletion, or branch deletion;
- spending money or using external services without approval;
- runtime proof that cannot be collected because credentials, services, or data are missing;
- an owner decision about scope, architecture, or risk.

## Long `/goal` State Pattern

For a long Tenn goal, use this sequence:

1. Read `AGENTS.md` and the relevant `.agents/skills/<skill>/SKILL.md`.
2. Print preflight: pwd, branch, HEAD, upstream, status, canonical branch head.
3. Create or validate a task card.
4. Run registry read-only and ledger validation or record `DATA_MISSING`.
5. Write a report bundle under `reports/agent_jobs/<job_id>/`.
6. Keep a report-local status in `README.md`: objective, scope, current status, completed work, validation, risks, next action.
7. Before pausing, write `HANDOFF.md` and `HANDOFF_NEXT_GOAL.md`, or include the same information in the report.
8. Before `DONE`, run required validation and apply Runtime Functionality Proof if the work touched runtime behavior.

## Runtime Functionality Proof Before `DONE`

For runtime, product, data, service, extraction, automation, or UI functionality, `DONE` requires proof of intended output, not just process evidence.

Use the nine fields in `AGENTS.md`:

1. intended output;
2. live output location;
3. pre-run max timestamp/count;
4. post-run max timestamp/count;
5. rows/files inserted or updated after run start;
6. readiness/gate status;
7. exact command or query used;
8. result: `WORKING`, `PARTIAL`, `BROKEN`, or `DATA_MISSING`;
9. remaining blocker.

For docs-only audits like this one, Runtime Functionality Proof is not applicable to the docs themselves. If the audit makes any claim about a monitor, service, hook, or worker, that claim must be tied to actual command output and classified honestly.
