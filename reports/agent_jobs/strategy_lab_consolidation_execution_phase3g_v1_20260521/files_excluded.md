# Files Excluded

Excluded by boundary:

- `financial-engine_v2/backend/app/services/strategy_lab_artifact_schema.py`
- `financial-engine_v2/scripts/test_strategy_lab_artifact_schema.py`
- `financial-engine_v2/scripts/fixtures/strategy_lab_artifact_schema/`
- `docs/strategy_lab_quantdinger_artifact_schema.md`
- Runtime/backend/product code.
- Cockpit UI/backend code.
- Tenn stores.
- Parser/extraction/gold-label files.
- Source-registry files.
- Docker/systemd/env/secrets files.
- Dependency files and lockfiles.
- Broker/exchange/paper/live/trading execution configs.
- QuantDinger/MCP runtime directories.
- Real API client code.
- Artifact store implementation.
- Autonomous loops or scheduled jobs.

Excluded as generated or archive-only:

- `tests/strategy_lab/__pycache__/`
- `*.pyc`
- Duplicate older `reports/agent_jobs/strategy_lab_quantdinger_framework_v1_20260520/` bundles in Phase 3B and Phase 3C source worktrees.

Excluded as unrelated shared-checkout dirt:

- Cockpit task cards in `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`.
- The prior Phase 3G collision-audit task card/report bundle.
