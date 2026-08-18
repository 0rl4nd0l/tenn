# GEMINI.md - Gemini Tool Notes

`AGENTS.md` is the Tenn repo constitution. If this file conflicts with
`AGENTS.md`, follow `AGENTS.md`.

This file records Gemini-specific operation notes only. It is not an independent
source of truth for commits, runtime startup, skills, hooks, or validation.

## Gemini Role

Gemini is a strategic engineering peer. It should keep outputs concise, verify
current evidence, and preserve unrelated dirty state.

## Hooks

Gemini has repo-local `BeforeTool` hooks in `.gemini/settings.json`. With an
active task card, the hook validates the card and checks the current diff against
`allowed_files` using the repo hook wrapper. Final validation should still be
run explicitly by the agent when closing out work.

## Skills

Repo-backed Tenn skills live under `.agents/skills`; see
`docs/agents/skill-registry.md`. Treat `.codex/skills` as legacy/custom unless a
current task card explicitly says otherwise.

## Runtime

Use `docs/entrypoints.md` only for tasks that actually require runtime startup
or runtime validation. Repo-hygiene, docs, reports, hooks, and task-card work
should not start services by default.

## Validation

Follow the risk-based validation policy in `AGENTS.md`. Run focused tests or
checks that exercise the files changed; do not run broad suites merely because a
tool identity file says so.
