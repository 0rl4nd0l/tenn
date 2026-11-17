# Cockpit Home Narrative Read-Only Adapter

## Summary

Implemented a backend-owned, read-only Cockpit Home narrative adapter for issue #151.

- Empty or unavailable narrative sources still return explicit `DATA_MISSING`.
- Existing queued market-update follow-ups can populate a deterministic operational `session_summary`.
- `theme_candidates` and `tomorrow_prep` remain empty with visible missing-evidence signals until backend producers exist.
- No production data, memory writes, LLM generation, retrieval changes, or canonical financial truth changes were introduced.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/cockpit_home_narrative_readonly_adapter_v1_20260601.md --write-report`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/cockpit_home_narrative_readonly_adapter_v1_20260601.md`
- `uv run --python 3.10 --with-requirements financial-engine_v2/backend/requirements.txt --with-requirements financial-engine_v2/backend/requirements-dev.txt python -m pytest financial-engine_v2/backend/tests/test_cockpit_home_attention_queue.py`
- `corepack pnpm exec vitest run lib/cockpit-home-api.test.ts -t "Cockpit Home BFF route"`
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/cockpit_home_narrative_readonly_adapter_v1_20260601.md`

## Notes

The full mounted frontend Home test file still fails on an unrelated Strategy Lab component fixture issue: `payload.artifact_refs` is undefined in `buildStrategyLabHomeSummary`. The BFF route subset covering Home narrative payload assembly passed.
