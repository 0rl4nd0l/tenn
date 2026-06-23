# Changed Docs Summary

## Docs Changed

- `AGENTS.md`: added one concise pointer to `docs/README.md` as the docs source map.
- `CLAUDE.md`: added the source map to Claude's shared read-first policy.
- `README.md`: added agent documentation entrypoints and replaced a stale absolute `financial-engine_v2/README.md` link with a relative link.
- `docs/README.md`: added the canonical documentation source map, active/archive routing, current docs-audit snapshot, conflict rules, and do-not-touch boundaries.
- `docs/agents/domain.md`: inserted `docs/README.md` into the generic-skill read-first stack.
- `docs/current_system.md`: added a reference/snapshot banner requiring fresh runtime verification.
- `docs/startup.md`: scoped the Docker-only wording to full-stack mode and preserved `docs/entrypoints.md` for agent runtime tasks.
- `docs/claude/current-state.md`: added an archive/reference banner for dated current-state claims.
- `docs/prompts/CODEX_MASTER_PROMPT.md`: marked the old master prompt reference-only and removed current all-agent authority wording.
- `docs/dev_flow/SKILLS_SURFACE.md`: refreshed stale metadata to `e402bf38`, added verification scope, and classified specialist/backend skills.
- `docs/entrypoints.md`: changed validation wording from live-current to last documented because validation was not rerun.
- `docs/setup/environment.md`: added freshness note and refreshed checked launcher/verifier path guidance to `/mnt/tenn-nvme2/...`.
- `docs/architecture/model-routing.md`: refreshed checked model routing config names and NVMe2 model path evidence without claiming live inference.
- `docs/agent_tasks/docs_current_state_consolidation_v1_20260623.md`: added validated task card for this job.

## Docs Intentionally Not Touched

- `docs/dev_flow/CONTROL_PLANE_STATUS.md`, `docs/dev_flow/CONTROL_PLANE_OPEN_WORK.md`, and `docs/agent_registry/task_ledger/*`: audit-time PR #387 collision risk; PR #387 merged before publish preflight, but these files remain intentionally untouched by this job.
- `docs/setup/*` and `docs/architecture/*`: mapped but not rewritten; runtime/topology truth was not live-probed.
- Historical task cards and report bundles: mapped as evidence/archive surfaces, not mass-edited.
- Runtime/product/extraction/data files: out of scope.
