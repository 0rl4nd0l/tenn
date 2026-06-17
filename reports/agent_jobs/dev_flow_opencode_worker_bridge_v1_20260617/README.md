# OpenCode Worker Bridge Closeout

## Status

DONE_WITH_RISK: implementation complete and validation passed. Risk is limited
to PR #368 owning the broader model-routing/result-template docs lane, so this
branch intentionally avoided those files.

## Summary

This task adds a generic Codex-to-OpenCode worker bridge for bounded read-only
delegation. The bridge supports probing OpenCode, running evidence-only workers,
validating worker result artifacts, summarizing worker outputs, and emitting a
ledger-compatible JSON entry.

## Files Touched

- `scripts/opencode_worker_bridge.py`
- `tests/test_opencode_worker_bridge.py`
- `.agents/skills/codex-worker-bridge/SKILL.md`
- `docs/dev_flow/templates/WORKER_TASK.md`
- `docs/dev_flow/templates/OPENCODE_WORKER_META.json`
- `docs/dev_flow/worker_bridge/README.md`
- `docs/agent_tasks/dev_flow_opencode_worker_bridge_v1_20260617.md`
- `reports/agent_jobs/dev_flow_opencode_worker_bridge_v1_20260617/`

## Files Intentionally Not Touched

- `docs/dev_flow/templates/MODEL_ROUTING.md`
- `docs/dev_flow/templates/WORKER_RESULT.md`

Those files are already in PR #368's active docs-freshness/model-routing lane.

## Unsafe Actions Avoided

- No Tenn product/runtime/extraction files were edited.
- No DB, Qdrant, Redis, news, memory, backfill, source PDF, gold-label, model,
  GPU, or live-service state was touched.
- No host-global OpenCode agents were created.
- No write-worker behavior was implemented.

## Recommended Worker Agents

If host-global OpenCode agent creation is later approved:

```bash
opencode agent create evidence-scout
opencode agent create docs-scout
opencode agent create validation-scout
```

## Validation

See `VALIDATION.md`.
