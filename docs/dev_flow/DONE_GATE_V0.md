# Tenn Done Gate V0

Done Gate V0 is the minimal closeout evidence contract for Tenn agent work.

It answers one question: can an agent truthfully claim this task is done?

## Purpose

Done Gate prevents completion claims that are based only on confidence, file
creation, passing activity checks, or implied evidence. It keeps closeout small
enough for normal use while requiring the evidence Orlando otherwise has to ask
for manually.

Dev Status answers whether a session is safe to start. Done Gate answers
whether the task can close.

## When It Applies

Use Done Gate before any Tenn agent says `DONE`, `complete`, `ready`, `fixed`,
`working`, `merge-ready`, or equivalent.

It applies to:

- report-only tasks;
- docs and control-plane changes;
- script or tooling changes;
- PR reviews and merge-readiness calls;
- runtime or product changes;
- extraction, financial-truth, or data-sensitive tasks;
- first-mate or auto-progress lanes before they advance a task.

For runtime, ingestion, extraction, automation, collector, scheduler, service,
pipeline, or product behavior claims, Done Gate does not replace the Runtime
Functionality Proof table required by `AGENTS.md`. The runtime proof must be
included in the evidence packet.

## Required Evidence Packet Fields

Every closeout must include:

| Field | Required evidence |
| --- | --- |
| original intent | Restate the user request or task-card objective. |
| task card / issue / PR | Exact task card path, issue number, PR number, or `not applicable`. |
| mutation mode | `report_only`, `docs_only`, `control_plane_only`, `safe_extension`, `runtime_mutation`, `data_mutation`, or the task-card value. |
| allowed_files check | Show whether every touched path is in the task-card allowlist, or why no task card applies. |
| exact files changed | List every changed tracked file and intentional ignored report artifact. |
| forbidden surfaces | State whether product/runtime/data/extraction/DB/Qdrant/news/memory/source-PDF/gold-label/prompt/service surfaces were touched. |
| validation commands run | Exact commands, cwd when useful, and exit status. |
| validation results | Pass/fail result with important output, failure reason, skipped reason, or raw-log path. |
| evidence produced | Report files, validation logs, review files, screenshots, scorecards, runtime proof tables, or query output. |
| risk classification | One V0 risk level and the reason. |
| known limitations | What the evidence does not prove. |
| unresolved blockers | Remaining blocker or `none`. |
| owner decisions needed | Required approval/choice or `none`. |
| current git status | Fresh `git status --short --untracked-files=all`; note ignored report files if relevant. |
| next safe action | One concrete owner-safe action. |

Use `docs/dev_flow/templates/DONE_GATE_EVIDENCE_PACKET.md` for the compact
packet shape.

## Do-Not-Claim-Done Rules

Do not claim `DONE` if any of these are true:

- validation was not run;
- validation failed;
- `allowed_files` were exceeded;
- forbidden surfaces may have been touched;
- HEAD or the worktree changed unexpectedly;
- unrelated worktree dirt exists and ownership is unresolved;
- PR/check status is unknown when PR/check status is relevant;
- runtime or data mutation happened without approval;
- evidence is missing, stale, inferred, or only implied;
- the task is merely "files created" but not validated;
- the result depends on a service, DB, model, external site, or GitHub state
  that was not checked;
- runtime-like work lacks the Runtime Functionality Proof table from
  `AGENTS.md`;
- extraction or financial-truth work lacks source-bound provenance and
  validation evidence;
- an owner approval or product decision is still required.

When a stop rule applies, use `NOT DONE`, `BLOCKED`, `DATA_MISSING`, or
`OWNER_DECISION_REQUIRED` instead of `DONE`.

## Risk Levels

| Risk level | Meaning | Closeout rule |
| --- | --- | --- |
| `LOW` | Narrow report, docs, or control-plane work with exact paths, passing structural validation, and no forbidden surfaces. | `DONE` is allowed when all evidence fields pass. |
| `MEDIUM` | Code, tooling, shared workflow, or PR-review work with focused validation and no runtime/data mutation. | `DONE` needs validation and allowed-files proof. |
| `HIGH` | Cross-layer behavior, merge readiness, runtime/product, extraction, financial truth, or data-sensitive work. | Requires stronger proof, review, and often owner approval. |
| `BLOCKED` | A hard stop prevents truthful completion. | Do not claim `DONE`; state blocker and next safe action. |
| `DATA_MISSING` | Required evidence cannot be obtained. | Do not claim `DONE`; state missing source and why it matters. |
| `OWNER_DECISION_REQUIRED` | The next meaningful step needs owner approval or choice. | Stop or close as decision-needed. |

## Owner-Decision Rules

Use `OWNER_DECISION_REQUIRED` when the next step would require approval for:

- GitHub writes, PR creation, merge, rebase, reset, stash, clean, branch
  deletion, worktree deletion, or force operations;
- product, runtime, data, extraction, DB, Qdrant, news, memory, source-PDF,
  gold-label, prompt, service, model/GPU, Docker, or secret mutation;
- expanding `allowed_files`;
- adopting, superseding, parking, or advancing another agent's work;
- changing behavior, architecture, product scope, financial truth, or owner
  policy beyond the active task card.

The packet must separate `known limitations` from `owner decisions needed`.
Do not bury required approvals inside a narrative caveat.

## Pairing With Tenn Primitives

### Dev Status

Start sessions with `python3 scripts/tenn_dev_status.py`. If Dev Status reports
a blocking or unexpected state, stop before editing. At closeout, rerun Dev
Status when the task or `AGENTS.md` requires it and record the result in the
Done Gate packet.

### `AGENTS.md`

`AGENTS.md` remains the repo constitution. Done Gate is the closeout evidence
shape that proves the run respected `AGENTS.md`, including Dev Status preflight,
task-card discipline, forbidden surfaces, and Runtime Functionality Proof.

### Task Cards

Task cards define the mutation contract. Done Gate requires an exact changed
file list and an `allowed_files` comparison. If the diff exceeds the allowlist,
the task is not done until the owner expands scope or the out-of-scope change
is handled through an approved path.

### Tenn Git Guard

Tenn git guard remains the worktree, branch, dirty-state, ledger, registry, and
duplicate-work guard. Done Gate records the guard result as closeout evidence;
it does not replace guard preflight.

### PR Review

For PR review or merge-readiness claims, Done Gate must name the PR number,
reviewed head SHA, base, check status, unresolved review comments, and the
verdict. If the live PR head or checks are unknown, use `DATA_MISSING`.

### First-Mate / Auto-Progress

Future first-mate or auto-progress workflows should treat Done Gate as the
terminal truth check. A lane should not auto-advance, mark complete, open a PR,
or ask the owner to trust a completion claim unless the packet passes. If the
packet fails, route the lane to `NOT DONE`, `BLOCKED`, `DATA_MISSING`, or
`OWNER_DECISION_REQUIRED` with one next safe action.
