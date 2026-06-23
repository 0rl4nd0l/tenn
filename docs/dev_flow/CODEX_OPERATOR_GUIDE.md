# Codex Operator Guide

Status: practical Orlando guide for the Tenn control plane after PR #383 and the Runtime Functionality Proof closeout-gate follow-up.

## The Operating Rule

Use repo-backed Tenn skills by path and require evidence before claims. Autocomplete is not authority. Host/global skills are not substitutes for Tenn control-plane skills.

For serious Tenn work, start with:

```text
Read AGENTS.md fully.
Read docs/dev_flow/SKILLS_SURFACE.md fully.
Read .agents/skills/<skill>/SKILL.md fully and follow it.
```

First preflight command:

```bash
python3 /home/l4nd0/.agents/skills/tenn-git-guard/scripts/tenn_git_guard.py preflight --repo-root <repo-root> --topic "<topic-or-path>" --json
```

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
| Metric extraction | `tenn-financial-metric-extraction` | Uses the narrow Financial Truth extraction workflow. |
| Worker scouts | `codex-worker-bridge` through `tenn-fix` | Runs bounded OpenCode evidence scouts under Codex authority. |
| Git/task-card safety | `tenn-git-guard` | Backend guard for preflight, registry, ledger, and allowed diff checks. |

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
3. Pick the repo-backed skill by path.
4. Validate or create a task card.
5. Run the portable `tenn-git-guard` preflight first.
6. In a Tenn control-plane checkout, run repo-local registry/ledger validation
   only when those scripts are available and useful.
7. Do only the allowed work.
8. Preserve report evidence.
9. Run validation and allowed-diff checks.
10. Apply Runtime Functionality Proof for runtime claims and run `check-closeout`.
11. Handoff or open a PR only if explicitly permitted.

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

Use Tenn repo skills as explicit files, not autocomplete labels. For ordinary next-action work, start with `tenn-issue`. For any mutation, use `tenn-fix`. For decisions, use `tenn-review-board`. For long goals, keep `tenn-goal-report` state current. Before stopping, use `tenn-handoff`.

When Codex claims readiness, ask for the exact validation command and the proof target. For runtime behavior, ask for the nine Runtime Functionality Proof fields and the `check-closeout` result. For docs/report work, ask for portable guard preflight, task-card validation, any Tenn-control-plane-local ledger/registry checks that were available, `check-diff`, `check-report-artifacts`, and `git diff --check`.
