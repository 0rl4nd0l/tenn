# Dev Flow Remaining Operating Rules V1

## Objective

Add remaining hands-off operating rules, counter-lineage behavior, and Agent
Task Ledger awareness to Tenn dev-flow control-plane files.

## Current State

DONE

## Evidence Used

- PR #359: merged at `2026-06-16T08:19:52Z`, merge commit
  `158639adf4ebbe6db7b361f907dc058baa1d42f3`.
- PR #360: merged at `2026-06-16T09:35:07Z`, merge commit
  `85250db58bc4ebd5b3e46790311afc7ec7e5b910`.
- Worktree:
  `/home/l4nd0/tenn-dev-flow-remaining-operating-rules-v1-20260616`.
- Branch:
  `control-plane/dev-flow-remaining-operating-rules-v1-20260616`.
- Base: `origin/migration/clean-runtime-baseline-reconstruct-v1` at
  `85250db58bc4ebd5b3e46790311afc7ec7e5b910`.
- Required wrapper skills exist.
- Registry read-only check returned `ok: true`, `read_only: true`,
  `lock_acquired: false`, and no active jobs.
- Live Task Ledger and committed ledger are `DATA_MISSING`; bounded fallback
  search found no prior matching task/report/PR implementation.

## Constraints And Unsafe Actions

- Control-plane docs, skills, templates, task card, and report only.
- No product/runtime/data/extraction/count-24 mutation.
- No ledger script implementation.
- No host-global mutation.
- No cleanup or branch/worktree deletion.
- GitHub mutation limited to opening the PR after validation.

## Files Touched

- `AGENTS.md`
- `.agents/skills/tenn-issue/SKILL.md`
- `.agents/skills/tenn-review-board/SKILL.md`
- `.agents/skills/tenn-fix/SKILL.md`
- `.agents/skills/tenn-worker/SKILL.md`
- `.agents/skills/tenn-explain/SKILL.md`
- `.agents/skills/tenn-code-reviewer/SKILL.md`
- `.agents/skills/tenn-improve-codebase-architecture/SKILL.md`
- `docs/dev_flow/templates/ISSUE.md`
- `docs/dev_flow/templates/BOARD.md`
- `docs/dev_flow/templates/BOARD_DECISION.json`
- `docs/dev_flow/templates/STATE.md`
- `docs/dev_flow/templates/WORKER_RESULT.md`
- `docs/dev_flow/templates/PR_REVIEW.md`
- `docs/dev_flow/templates/EXPLAIN.md`
- `docs/dev_flow/templates/COUNTER_LINEAGE.md`
- `docs/agent_tasks/dev_flow_remaining_operating_rules_v1_20260616.md`
- `reports/agent_jobs/dev_flow_remaining_operating_rules_v1_20260616/`

## Files Intentionally Not Touched

- Product/runtime/data/extraction paths.
- count-24 approval packet paths.
- Source PDFs, gold labels, DB, Qdrant, Redis, news, memory, prompts, schema,
  runtime/model/GPU config, and services.
- Host-global files.

## Validation Status

Passed locally. See `VALIDATION.md`.

## Next Recommended Prompt

Review the opened PR after CI; do not merge automatically.
