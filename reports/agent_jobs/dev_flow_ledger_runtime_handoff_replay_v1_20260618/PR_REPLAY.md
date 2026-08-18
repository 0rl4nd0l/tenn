# PR Replay Notes

## Source State

- PR #367: `OPEN`
- source head: `control-plane/agent-ledger-runtime-handoff-v1-20260617`
- source head SHA: `7315d50f8cc18450c28f5354ca4b7d2a18e8ad0e`
- base: `migration/clean-runtime-baseline-reconstruct-v1`
- live mergeability before replay: `DIRTY` / `CONFLICTING`
- REST comparison before replay: ahead 2, behind 21, rebaseable false

## Replay Decision

The old PR branch was not force-pushed because it is part of the dirty branch
history being separated from current canonical. A clean sibling replay branch
was created from latest canonical and only the still-relevant PR #367 payload was
applied.

## Preserved From PR #367

- `scripts/agent_task_ledger.py`
- `tests/test_agent_task_ledger.py`
- `docs/agent_registry/task_ledger/*`
- task-ledger templates under `docs/dev_flow/templates/`
- repo-native `.agents/skills/tenn-handoff/SKILL.md`
- task-ledger/session/handoff updates to existing Tenn skills
- original PR #367 report bundle evidence

## Resolved Against Later PRs

- Kept PR #368 docs impact and model routing guidance in existing skills.
- Kept PR #374 validation-environment autonomy guidance in existing skills.
- Did not touch OpenCode bridge files from PRs #370 and #373.
- Did not replay superseded dirty changes from the original checkout.

## Intended Outcome

The replay PR should supersede PR #367 for merge purposes. Closing or otherwise
mutating PR #367 remains a separate GitHub owner decision unless explicitly
approved.
