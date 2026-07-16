# Tenn agent policy

These rules are the durable default. Follow a task-specific procedure only when
the work actually needs it. User instructions and live repository evidence win.

## Verify the target

- Inspect the current branch, HEAD, upstream, and status before editing.
- Do not assume `main` is canonical. Use the current live canonical branch.
- Preserve unknown dirty or untracked work. Never reset, clean, stash,
  overwrite, delete, or absorb it.
- If the selected checkout is dirty, stale, detached, or otherwise unsuitable,
  create a clean sibling worktree from the verified base and work there.
- Recheck HEAD before publishing if the base or target may have moved.

## Risk tiers

### Tier 0 — always autonomous

Reads, search, inspection, diffs, status, and other non-mutating evidence work
need no task card, registry, ledger, report, runtime proof, or approval.

### Tier 1 — autonomous local delivery

Local branches/worktrees, source and docs edits, focused validation, commits,
pushes, and draft PRs are autonomous. Keep the diff narrow, protect unrelated
work, and use changed-file linting and focused tests. Missing unrelated local
tools must not block docs-only or unrelated delivery; report the gap and rely on
CI where appropriate.

### Tier 2 — explicit approval required

Ask before runtime, service, queue, DB, Qdrant, GPU, model, extraction,
backfill, paid-resource, production-data, merge, destructive, or shared-state
actions. Do not infer that approval from a request to edit code or open a PR.

## V2 is opt-in

Task cards, registries, ledgers, reports, and V2 contracts are optional tools
for genuinely concurrent or repeated autonomous goals. They are enforced only
when `TENN_V2_REQUIRED=1` is explicitly set. Ordinary Tier 0 and Tier 1 work
must not need them.

## Hooks and validation

- Hooks must be risk-aware: Tier 0 passes; Tier 1 has no task-state dependency.
- Hooks may warn, but Stop must always pass and must never write state.
- No hook may silently rewrite files, change modes, or launch broad tests.
- Run `git diff --check`, fast lint for changed applicable files, and focused
  tests for changed behavior. CI remains the full-suite gate.
- Keep evidence concise: commands run, their exit status, changed files, and
  any skipped tool with the reason.

## Event waiter

Use `scripts/codex_event_waiter.py` as an attached wait for authorised long
commands and GitHub checks. It requires no task state by default. Bind GitHub
waits to the exact head SHA, write one terminal result with bounded redacted
logs, and refresh live state after wake-up. Detached wake-up remains disabled.
The waiter does not authorise merges or runtime changes.

## Closeout

Before a Tier 1 closeout, confirm the intended branch/worktree, `git diff
--check`, focused validation, commit SHA, push result, draft PR URL, and final
Git status. State any remaining approved boundary or unavailable local tool.
