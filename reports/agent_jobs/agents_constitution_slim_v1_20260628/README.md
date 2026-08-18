# Agents Constitution Slim V1

status: PR_OPENED
scope: docs_only

## Objective

Slim `AGENTS.md` so it stays a repo constitution rather than a procedure
manual, while preserving the hard Tenn guardrails.

## Current State

- Fresh task worktree: `/home/l4nd0/tenn-agents-constitution-slim-v1-20260628`
- Branch: `control-plane/agents-constitution-slim-v1-20260628`
- Base: `origin/migration/clean-runtime-baseline-reconstruct-v1@b2adf891096f41d4ddef260b1c47fd9b5a8417a4`
- Task card: `docs/agent_tasks/agents_constitution_slim_v1_20260628.md`

## Completed Work

- Reduced `AGENTS.md` from the current base's 364 lines to 241 lines. The
  resolved file is 12005 bytes.
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
- Committed local cleanup as
  `d07fc0f3633395fb727a556bce5b6f25d3af27dc`.
- Opened draft PR #462:
  `https://github.com/0rl4nd0l/tenn/pull/462`.
- Fixed the report contradiction found during PR review: GitHub writes were
  not avoided; they were performed only after explicit user approval.
- Refreshed the PR branch by merging current canonical
  `b2adf891096f41d4ddef260b1c47fd9b5a8417a4`.
- Resolved the `AGENTS.md` merge conflict by keeping the slim constitution
  structure and folding in current-base execution-lane and `--fallback-detail`
  guidance.

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

Live PR state must be rechecked after each push. Last pre-push refresh state:

- PR #462: open draft.
- Base: `migration/clean-runtime-baseline-reconstruct-v1`.
- Head: `control-plane/agents-constitution-slim-v1-20260628`.
- Mergeable before refresh: `CONFLICTING`.
- Merge state before refresh: `DIRTY`.
- Checks before refresh: `scan` success; `lint-and-test` success.

## Unsafe Actions Avoided

- No service starts.
- No dependency installs.
- No unapproved GitHub writes. Branch push and draft PR creation happened only
  after explicit user approval.
- No unapproved merge, rebase, reset, stash, clean, prune, branch deletion, or
  worktree deletion. The canonical branch refresh merge happened only after
  explicit user approval.
- No runtime or production-data mutation.

## Next Recommended Prompt

Review PR #462 after `lint-and-test` finishes. If checks are green and the
shorter `AGENTS.md` preserves the intended guardrails, mark the PR ready for
review or merge under the normal Tenn merge gate.
