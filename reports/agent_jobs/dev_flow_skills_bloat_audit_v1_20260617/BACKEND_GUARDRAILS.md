# Backend Guardrails

## Guardrail Stack

1. `AGENTS.md`: constitution and source-of-truth hierarchy.
2. Task card: exact execution contract and allowed files.
3. `tenn-git-guard`: branch, worktree, upstream, registry, ledger, duplicate
   work, and owner-boundary preflight.
4. `tenn-task-card-registry-safety`: task-card validation, dirty state, and
   allowed-file enforcement.
5. Hooks: backstop only; do not rely on hooks instead of preflight.
6. `tenn-code-reviewer`: final read-only diff/PR review before ready claims.
7. `VALIDATION.md` in the report bundle: durable command evidence.

## Backend-Only Skill List

- `tenn-git-guard`
- `tenn-task-card-registry-safety`
- `tenn-worker`
- `tenn-code-reviewer`
- `tenn-improve-codebase-architecture`
- `tenn-auto-progress`
- `tenn-frame-design`
- most of `tenn-git-hygiene`
- host `code-reviewer`
- host `code-fixer`
- host `function-quality`
- host `architecture-check`
- host `architecture-cleanup-steward`
- host `prompt-crafter`
- host `prompt-structure-reference`
- host `diagnose` except explicit debugging requests
- plugin-owned specialty skills unless explicitly domain-triggered

## Hook Findings

- `.codex/hooks.json` is present.
- PreToolUse Bash hook points to `graphify-out/GRAPH_REPORT.md` when a graph
  exists.
- Stop hook runs `python3 scripts/agent_job_hook.py --platform codex --event Stop`.
- `scripts/agent_job_hook.py` now uses `list-active --read-only` and
  `check-diff --no-write-report` for hook paths.
- Host hooks are present under `/home/l4nd0/.codex/hooks`, but this audit did
  not mutate them.

## Required Future Guardrails

- Docs Impact Check must run in `/fix`, `tenn-code-reviewer`, and handoff.
- Task tier must be recorded before subagents or expensive/high-reasoning work.
- Small workers may gather evidence, but cannot make final decisions for
  `large` or `critical` tasks.
- Review board is required for `critical` tasks.
- Host-global mutation needs explicit owner approval and exact external path
  contract.
- Plugin skills should remain hidden unless their router or explicit domain
  trigger is invoked.

## Guardrail Anti-Patterns

- Calling host `code-fixer` directly without Tenn task card.
- Running `tenn-auto-progress` repeatedly instead of choosing one next action.
- Running `tenn-frame-design` for narrow tasks that only need a README.
- Treating `.codex/skills` as active repo authority.
- Treating `reports/` artifacts as preserved without `git add -f` or explicit
  local-only closeout.
- Letting small/cheap workers decide merge readiness, financial truth, cleanup,
  or owner-boundary questions.
