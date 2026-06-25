# Control Surface Instructions Refine V1

status: DONE

## Objective

Refine Tenn Codex control-plane instructions from current canonical by fixing
the handoff milestone-heading contract and absent `.codex/skills` verification
wording.

## Scope

- control-plane docs, template, skill instruction, focused test, and report only
- no product/runtime/extraction/data/host-global mutation

## Latest State

- Fresh worktree:
  `/home/l4nd0/tenn-control-surface-instructions-refine-v1-20260625`
- Branch: `control-plane/control-surface-instructions-refine-v1-20260625`
- Base/head at start: `a68553a7341ef5344626d37da196c9e390584cf8`
- Guard preflight: pass, `VALID_TASK_WORKTREE`, no active registry jobs.
- Handoff milestone wording is now consistent across the handoff skill and
  task-ledger test.
- Legacy `.codex/skills` verification now passes when `.codex/skills` is
  absent, which is the current canonical state.
- Live task ledger append: passed at
  `/mnt/sdb2/home/l4nd0/tenn/.git/tenn-agent-registry/task-ledger.jsonl`.

## Validation Summary

- Focused test: `tests/test_agent_task_ledger.py` passed.
- Task-card validation: passed.
- Registry read-only check: passed, no active jobs.
- Ledger validation: passed.
- Diff/report/closeout gates: passed after final report update.

## Runtime Functionality Proof

Not applicable. This is a control-plane instruction/test lane and did not touch
runtime, extraction, ingestion, service, scheduler, DB, Qdrant, Redis, news,
memory, source documents, or production data.

## Next Action

Owner review, then commit/push/open PR only if explicitly approved.
