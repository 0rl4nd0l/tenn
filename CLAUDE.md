# CLAUDE.md - Claude Tool Notes

`AGENTS.md` is the Tenn repo constitution. If this file conflicts with
`AGENTS.md`, follow `AGENTS.md`.

This file is intentionally narrow. It records Claude-specific context only; it
does not create independent safety, commit, runtime, or skill policy.

## Claude Role

- Use Claude as an implementation and investigation peer in the shared Tenn
  checkout.
- Ground substantive claims in current-turn evidence.
- Preserve unrelated dirty files and respect active task-card allowlists.
- Do not commit, push, resolve backend flags, start services, or mutate runtime
  or data surfaces unless the current task card and user approval explicitly
  permit that exact action.

## Required Shared Policy

Before non-trivial work, read and follow:

- `AGENTS.md`
- the active task card, when present
- `docs/README.md` for the current documentation source map
- relevant repo-backed skills under `.agents/skills`

Use `docs/architecture/SYSTEM_CONTRACT.md` when touching product architecture,
runtime behavior, extraction, RAG, financial truth, model routing, or data
integrity. Do not treat it as a required read for unrelated repo-hygiene or
report-only work.

Use `docs/entrypoints.md` only when the task actually needs runtime startup or
runtime validation.

## Claude Hooks

`.claude/settings.json` should stay low-side-effect and repo-relative. It should
not hardcode checkout paths, start services, run broad tests, auto-format files,
or enforce commit/clean-tree policy.

## Cockpit Flag Closeout

If a task is explicitly about Cockpit flagged feedback, do not resolve backend
flag records until:

1. a task card permits the write path,
2. the user has approved any commit/backend mutation,
3. the fix has been verified, and
4. the resolve payload can cite the reviewed commit metadata.

Otherwise, report the needed closeout as a blocked follow-up.

## Validation

Use `AGENTS.md` risk-based validation:

- docs/report-only changes: syntax and artifact checks are usually enough
- narrow code changes: focused tests
- runtime/product changes: targeted runtime or regression validation

Do not run broad runtime validation just because this file exists.
