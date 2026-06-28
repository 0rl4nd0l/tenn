# Agents Constitution Slim V1

status: DONE
scope: docs_only

## Objective

Slim `AGENTS.md` so it stays a repo constitution rather than a procedure
manual, while preserving the hard Tenn guardrails.

## Current State

- Fresh task worktree: `/home/l4nd0/tenn-agents-constitution-slim-v1-20260628`
- Branch: `control-plane/agents-constitution-slim-v1-20260628`
- Base: `origin/migration/clean-runtime-baseline-reconstruct-v1@7a0bab4ca9337c6c9d735f23d5898d9b306ecc2d`
- Task card: `docs/agent_tasks/agents_constitution_slim_v1_20260628.md`

## Completed Work

- Reduced `AGENTS.md` from 342 lines / 17011 bytes to 222 lines / 10925 bytes.
- Preserved the Runtime Functionality Proof table and compatibility heading
  required by `scripts/check_runtime_functionality_proof_docs.py`.
- Routed repeatable procedure to existing homes:
  `.agents/skills/tenn-fix/SKILL.md`,
  `.agents/skills/tenn-git-guard/SKILL.md`,
  `.agents/skills/tenn-goal-report/SKILL.md`,
  `.agents/skills/tenn-handoff/SKILL.md`,
  `docs/dev_flow/CODEX_OPERATOR_GUIDE.md`, and
  `docs/dev_flow/SKILLS_SURFACE.md`.
- Added short routing notes to `CODEX_OPERATOR_GUIDE.md` and
  `SKILLS_SURFACE.md`.

## Runtime Functionality Proof

not_applicable: This task is docs-only and did not start services, mutate
runtime state, access production data, or claim runtime functionality.

## Files Touched

- `AGENTS.md`
- `docs/agent_tasks/agents_constitution_slim_v1_20260628.md`
- `docs/dev_flow/CODEX_OPERATOR_GUIDE.md`
- `docs/dev_flow/SKILLS_SURFACE.md`
- `reports/agent_jobs/agents_constitution_slim_v1_20260628/`

## Files Intentionally Not Touched

- Product/runtime/backend/extraction/parser/evaluator code.
- DB, Qdrant, Redis, news, memory, source PDFs, gold labels, prompts,
  production data, services, model/GPU config, Docker, and count-24 paths.
- Host-global files under `/home/l4nd0/.codex` and `/home/l4nd0/.agents`.

## Validation Status

All required docs/control-plane checks passed. See `VALIDATION.md`.

## Unsafe Actions Avoided

- No service starts.
- No dependency installs.
- No GitHub writes.
- No merge, rebase, reset, stash, clean, prune, push, branch deletion, or
  worktree deletion.
- No runtime or production-data mutation.

## Next Recommended Prompt

Review the `AGENTS.md` slimming diff on
`control-plane/agents-constitution-slim-v1-20260628`; if it preserves the
guardrails, commit it locally or open a PR.
