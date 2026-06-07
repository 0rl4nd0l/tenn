---
name: tenn-frame-design
description: Use for Tenn long-running /goal work that needs a compact execution Frame, durable STATE and OPERATOR_NOTES artifacts, optional Scribe capture, live steering preservation, and control-plane-only guardrails before implementation starts.
---

# Tenn Frame Design

Use this skill before long Tenn `/goal` runs, multi-turn handoffs, or any task
where the agent needs a compact frame of judgment before execution. This is
control-plane infrastructure only.

## Boundaries

- Do not implement product/backend/frontend/runtime/data/extraction changes from
  this skill.
- Do not mutate DB, Qdrant, news, memory, backfills, source PDFs, gold labels,
  prompts, services, runtime/model/GPU config, or production data.
- Do not create, edit, or comment on GitHub issues unless the user explicitly
  approves that exact action.
- Keep artifacts instruction-only and Tenn-native. Do not copy third-party skill
  text.

## Artifacts

Create these under the task card `output_dir` or
`reports/agent_jobs/<goal_or_job_id>/`:

- `FRAME.md`: compact plan and judgment contract.
- `STATE.md`: current state, progress, validation, blockers, and next action.
- `OPERATOR_NOTES.md`: durable user steering, corrections, preferences, and
  decisions captured during the run.
- `SCRIBE.md`: optional instructions for a Scribe role when the user requests
  live steering capture.

## Frame Workflow

1. Verify repo path, branch, HEAD, origin, dirty state, task card, and registry
   evidence before execution.
2. Write a compact `FRAME.md` before broad work starts.
3. Keep the Frame stable. Update it only for user steering, discovered hard
   constraints, changed stop states, or materially corrected evidence.
4. Keep `STATE.md` short and current. It should answer what is happening now,
   what is done, what is blocked, and what the next safe action is.
5. Preserve user steering in `OPERATOR_NOTES.md` or the Frame steering log.
6. At closeout, link Frame artifacts from the goal report.

For Git Hygiene or control-plane remediation Frames, define the autonomy
profile, approval boundary, Shot 1/Shot 2 split, stop states, and
owner-decision classes before execution starts.

## FRAME.md Schema

Use these exact headings:

```markdown
# Frame

## Objective
<one concrete objective, preserving the user's real goal>

## Why This Matters
<short Tenn-specific reason this work matters>

## Non-Negotiables
- <hard boundary or invariant>

## Judgement Rules
- <rule for deciding scope, tradeoffs, readiness, or stop conditions>

## Scope In
- <included surface>

## Scope Out
- <excluded surface>

## Evidence Sources
- <current repo, task card, registry, report, issue, runtime, or user evidence>

## Success Shape
- <what a good completed state looks like>

## Stop States
- <condition that requires stopping, waiting, or reporting DATA_MISSING>

## Steering Log
- <YYYY-MM-DD HH:MM TZ> - <user correction, invariant, preference, or decision>
```

Keep the body compact. Prefer one-line bullets. Mark unknowns as `DATA_MISSING`
instead of filling gaps from memory.

## Scribe Pattern

Use Scribe only when requested or when live steering is likely to be lost during
a long `/goal` run.

Scribe responsibilities:

- Monitor live user corrections, guardrails, invariants, preferences, and
  decisions.
- Write durable notes to `OPERATOR_NOTES.md` or concise entries in
  `FRAME.md` `Steering Log`.
- Summarize compactly to avoid token waste.
- Interrupt only when there is a conflict, safety issue, ambiguous permission,
  or a user correction invalidates the current Frame.

Scribe boundaries:

- Never implement code.
- Never mutate product, runtime, data, extraction, registry, GitHub, memory, DB,
  Qdrant, news, services, prompts, model/GPU config, source PDFs, or gold labels.
- Never reinterpret the user's goal into an easier slice.
- Do not ask for confirmation unless the next action is unsafe, conflicting, or
  genuinely ambiguous.

## OPERATOR_NOTES.md Format

Use append-only concise entries:

```markdown
# Operator Notes

- <YYYY-MM-DD HH:MM TZ> - <correction/preference/decision> - Impact: <how the
  run should change>
```

If a note changes the Frame, update `FRAME.md` and reference the note.

## STATE.md Format

```markdown
# State

State: RUNNING | WAITING_ON_USER | BLOCKED_EXTERNAL | VALIDATING |
  DONE_WITH_RISK | DONE

Current Focus: <one line>
Completed: <compact bullets>
Blocked: <compact bullets or None>
Next Safe Action: <one line>
Validation: <commands/status or pending>
```
