---
name: tenn-task-card-registry-safety
description: Use for Tenn task-card validation, dirty-state review, registry safety, collision checks, allowed-files enforcement, and deciding whether a repo task can proceed safely without broad mutation or unrelated cleanup.
---

# Tenn Task Card Registry Safety

Use this skill before implementation-capable Tenn work, especially in dirty
shared checkouts or multi-agent contexts.

## Core Rule

The task card is the execution contract. Do not expand the effective work beyond
its lane, mutation mode, hard stops, and `allowed_files` without explicit user
approval.

## Required Checks

1. Verify `pwd`, branch, HEAD, origin, and `git status --short --untracked-files=all`.
2. Read the active task card or create the narrowest task card required.
3. Validate with:
   `python3 scripts/agent_job_contract.py validate <task_card>`
4. Compare intended files to `allowed_files` before editing.
5. Inspect registry state only through safe read-only evidence.

## Registry Safety

The current audit found that `python3 scripts/agent_job_registry.py list-active --read-only`
is not implemented in this checkout. Plain `list-active` may acquire a lock and
write transient registry files.

- Do not rely on lock-writing registry commands for read-only audits.
- Prefer direct read-only inspection of existing registry files when safe, or
  record `DATA_MISSING`.
- Do not claim, heartbeat, release, or check-overlap unless the task explicitly
  allows that registry mutation and the user-approved workflow requires it.

## Dirty-State Handling

- Preserve unrelated dirty and untracked files.
- If dirty files overlap the intended allowlist, stop or move to an approved
  clean sibling worktree.
- If dirty files are unrelated but block `check-diff`, record the blocker in the
  report instead of widening the allowlist or cleaning foreign work.

## Final Checks

- Run `git diff --check`.
- Run task-card `check-diff` when available and safe; use `--no-write-report`
  unless the diff-check artifact is explicitly allowed.
- Report disallowed files, skipped unsafe registry commands, ignored report
  artifacts, and the next safe prompt.
