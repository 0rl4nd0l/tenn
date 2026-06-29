# Codex Operator Guide

Status: practical Orlando guide for the Tenn control plane after PR #383, the
Runtime Functionality Proof closeout-gate follow-up, and the 2026-06-24
key/narrative skill surface trim.

## The Operating Rule

Use repo-backed Tenn skills by path and require evidence before claims. Autocomplete is not authority. Host/global skills are not substitutes for Tenn control-plane skills.

`AGENTS.md` is the always-loaded constitution: source-of-truth hierarchy,
safety boundaries, evidence labels, runtime proof, task-card discipline, and
done criteria. This guide and the repo-backed skills hold repeatable procedure,
prompt patterns, and exact operating commands so the root file stays concise.

For serious Tenn work, start with:

```text
Read AGENTS.md fully.
Read docs/dev_flow/SKILLS_SURFACE.md fully.
Read docs/dev_flow/REPO_PATH_OWNERSHIP_AND_WORK_PRESERVATION.md when path ownership or prior-work preservation is in scope.
Read .agents/skills/<skill>/SKILL.md fully and follow it.
```

First preflight command:

```bash
python3 /home/l4nd0/.agents/skills/tenn-git-guard/scripts/tenn_git_guard.py preflight --repo-root <repo-root> --topic "<topic-or-path>" --json
```

This default is the fast/summarized shape: it keeps blocking fields but caps
branch/worktree fallback detail. Use full detail only for high-risk duplicate
work, hygiene, merge, parking, stale-work, or broad audit decisions:

```bash
python3 /home/l4nd0/.agents/skills/tenn-git-guard/scripts/tenn_git_guard.py preflight --repo-root <repo-root> --topic "<topic-or-path>" --fallback-detail full --json
```

If the installed host runner rejects `--fallback-detail` or still emits full
fallback rows by default, use the repo-backed fallback from a current Tenn
control-plane checkout until the host skill copy is refreshed.

From a Tenn control-plane checkout, use this repo-backed fallback only when the
installed host skill path is unavailable:

```bash
python3 .agents/skills/tenn-git-guard/scripts/tenn_git_guard.py preflight --repo-root . --topic "<topic-or-path>" --json
```

## Which Skill To Ask For

| Orlando wants | Ask for | What it does |
| --- | --- | --- |
| "What next?" | `tenn-issue` | Finds and prioritizes the next safe issue/task path. |
| Risky decision | `tenn-review-board` | Produces a board decision, dissent, and next goal. |
| Implementation | `tenn-fix` | Runs task-card-first bounded implementation and validation. |
| Long-running goal | `tenn-goal-report` | Keeps report-local state and stop/continue discipline. |
| Handoff or new session | `tenn-handoff` | Creates durable handoff and next prompt. |
| Plain-English status | `tenn-explain` | Explains branch, issue, report, or subsystem state. |
| Zoom out | `zoom-out` or `tenn-explain` | Steps up one layer and maps the broader system/problem. |
| Brief mode | `caveman` | Makes future answers terse while preserving technical accuracy. |
| Metric extraction | `tenn-financial-metric-extraction` | Uses the narrow Financial Truth extraction workflow. |
| Architecture improvement | `tenn-improve-codebase-architecture` | Runs architecture/deepening review under Tenn gates. |
| Worker scouts | `codex-worker-bridge` through `tenn-fix` | Runs bounded OpenCode evidence scouts under Codex authority. |
| Git/task-card safety | `tenn-git-guard` | Backend guard for preflight, registry, ledger, and allowed diff checks. |

## Execution Lanes

| Lane | Use when | Default shape |
| --- | --- | --- |
| `FAST_PROGRESS` | Small docs/control-plane or narrow code fixes with exact files and no runtime/data/extraction/GitHub/destructive boundary. | Summarized guard, exact task card when editing, focused validation, direct closeout. |
| `STANDARD_FIX` | Normal bounded implementation. | Task card, guard, allowed-files check, validation, docs impact, final diff review. |
| `FULL_GUARD` | Stale path, dirty overlap, duplicate-work risk, merge/parking, owner-boundary, architecture, or broad cleanup. | `--fallback-detail full`, stop on unresolved risk. |
| `RUNTIME_PROOF` | Runtime-like work may be called working, functional, complete, or `DONE`. | Runtime Functionality Proof table and closeout gate. |

When in doubt, use `FULL_GUARD`. When the lane is clearly `FAST_PROGRESS`,
avoid review boards, handoffs, workers, and broad report packets unless the
guard or validation finds a real blocker.

## How To Force Repo-Backed Skills

If autocomplete hides a Tenn skill, ask for it by file:

```text
Read .agents/skills/tenn-review-board/SKILL.md fully first, then use that skill. Do not substitute host/global review skills.
```

For implementation:

```text
Read .agents/skills/tenn-fix/SKILL.md fully first. Create or validate a task card before editing. Keep the diff inside allowed_files.
```

For a long goal:

```text
Read .agents/skills/tenn-goal-report/SKILL.md fully first. Keep reports/agent_jobs/<job_id>/README.md updated and stop with WAITING_ON_USER when owner input is required.
```

## What Not To Use

Do not use these as Tenn substitutes:

- `$review` if it only exposes host/global review skills;
- host/global `code-reviewer` instead of `tenn-review-board`;
- host/global skills when a repo-backed `.agents/skills/<skill>/SKILL.md` exists for the task;
- `.codex/skills/cockpit-flag-orchestrator` as a default Tenn workflow;
- `scripts/sync_codex_skills.sh --apply` without explicit approval, because it mutates host-global Codex files;
- host `codex-goal-monitor` as proof that a repo `/goal monitor` exists.

## Standard Prompt Patterns

### New Goal

```text
Start from current canonical Tenn.
Read AGENTS.md, docs/dev_flow/SKILLS_SURFACE.md, and .agents/skills/tenn-goal-report/SKILL.md fully.
Create or validate a task card before mutation.
Keep a report bundle under reports/agent_jobs/<job_id>/.
Use Runtime Functionality Proof before any DONE claim for runtime/product/data behavior.
```

### Review Board

```text
Use tenn-review-board.
Read .agents/skills/tenn-review-board/SKILL.md fully.
Produce BOARD.md, BOARD_DECISION.json, and NEXT_GOAL.md in a report bundle.
Validate the decision with python3 scripts/check_board_decision.py <report-dir>/BOARD_DECISION.json.
If the task card lists BOARD_DECISION.json under output_dir, check-closeout validates it automatically too.
Do not use host/global review as a substitute.
```

### Implementation

```text
Use tenn-fix.
Read .agents/skills/tenn-fix/SKILL.md fully.
Run the portable Tenn git guard preflight:
python3 /home/l4nd0/.agents/skills/tenn-git-guard/scripts/tenn_git_guard.py preflight --repo-root <repo-root> --topic "<topic-or-path>" --json
Create or validate the task card.
Only edit allowed files.
Run validation, check-diff, check-closeout, and check-report-artifacts.
Treat check-closeout as the final report gate for Runtime Functionality Proof and listed BOARD_DECISION.json artifacts.
For `FAST_PROGRESS`, keep the report/direct closeout compact and skip board,
handoff, and worker delegation unless a blocker appears.
Open a PR only if the task card explicitly permits it.
```

### Handoff

```text
Use tenn-handoff.
Read .agents/skills/tenn-handoff/SKILL.md fully.
Write the current state, validation, risks, and exact next prompt.
Do not claim readiness without fresh evidence.
```

### Runtime Proof

```text
Before DONE, show the Runtime Functionality Proof fields from AGENTS.md:
intended output, live output location, pre-run count/timestamp, post-run count/timestamp, rows/files changed after run start, readiness/gate status, exact command/query, result, and remaining blocker.
```

The closeout gate is:

```text
python3 scripts/agent_job_contract.py check-closeout <task-card> --repo-root .
```

This gate also validates any `BOARD_DECISION.json` report artifact listed in
the task card `allowed_files` under `output_dir`.

For active task cards, `scripts/agent_job_hook.py` runs this gate on
Stop/SessionEnd. Runtime-like cards must either include the proof fields in
their report artifacts or explicitly declare report-only, docs-only, or
control-plane-only scope. Use task-card frontmatter such as
`closeout_scope: report_only`, `closeout_scope: docs_only`, or
`closeout_scope: control_plane_only`; alternatively add an anchored body line
like `Closeout scope: report-only`. Casual mentions of these words do not
exempt a runtime-like card.

### OpenCode Worker Scout

```text
Use tenn-fix and codex-worker-bridge.
Read .agents/skills/codex-worker-bridge/SKILL.md fully.
Run python3 scripts/opencode_worker_bridge.py probe.
Create a read-only evidence_only worker task.
Run through scripts/opencode_worker_bridge.py, validate-result, then have Codex decide what to use.
```

## Day-To-Day Tenn Flow

1. Confirm canonical branch and HEAD.
2. Read `AGENTS.md`.
3. Select `FAST_PROGRESS`, `STANDARD_FIX`, `FULL_GUARD`, or `RUNTIME_PROOF`.
4. Pick the repo-backed skill by path.
5. Validate or create a task card.
6. Run the portable `tenn-git-guard` preflight first and inspect
   `path_ownership`, `duplicate_work_classification`, and
   `stop_reimplementation`.
7. In a Tenn control-plane checkout, run repo-local registry/ledger validation
   only when those scripts are available and useful.
8. Do only the allowed work.
9. Preserve report evidence proportional to the lane.
10. Run validation and allowed-diff checks.
11. Apply Runtime Functionality Proof for runtime claims and run `check-closeout`.
12. Handoff or open a PR only if explicitly permitted.

## Red Flags That Codex Is Overclaiming

Treat these phrases as insufficient unless followed by intended-output proof:

- "service is active";
- "tests pass";
- "artifact exists";
- "PR merged";
- "script ran";
- "hook exists";
- "monitor exists";
- "OpenCode is available".

The missing question is always: did the intended output happen in the live target after the run?

## How To Operate Codex From Now On

Use Tenn repo skills as explicit files, not autocomplete labels. For ordinary
next-action work, start with `tenn-issue`. For any mutation, use `tenn-fix`.
For decisions, use `tenn-review-board`. For long goals, keep
`tenn-goal-report` state current. Before stopping, use `tenn-handoff`.

When Codex claims readiness, ask for the exact validation command and the proof target. For runtime behavior, ask for the nine Runtime Functionality Proof fields and the `check-closeout` result. For docs/report work, ask for portable guard preflight, task-card validation, any Tenn-control-plane-local ledger/registry checks that were available, `check-diff`, `check-report-artifacts`, and `git diff --check`.

For path/worktree or duplicate-work concerns, ask for the exact classification
from `docs/dev_flow/REPO_PATH_OWNERSHIP_AND_WORK_PRESERVATION.md`: valid
starting path, invalid/sparse/runtime-only paths, prior-work search surfaces,
preservation status, and whether Codex stopped instead of reimplementing.
