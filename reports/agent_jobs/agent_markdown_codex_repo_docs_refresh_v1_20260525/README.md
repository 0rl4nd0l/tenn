# Agent Markdown and Codex Repo Documentation Audit

Issue: #78
Lane: Reporting
Mode: AUDIT
Worktree: `/home/l4nd0/tenn-repo-hygiene-agent-docs-refresh-audit-v1-20260601`
Branch: `audit/repo-hygiene-agent-docs-refresh-v1-20260601`

## Summary

This report-only slice inventories Tenn agent-facing instruction surfaces,
records the highest-value contradiction and bloat findings, and proposes a
bounded safe-extension follow-up patch. It does not edit standing instructions,
product code, runtime config, data stores, or the active shared checkout.

The strongest current finding is a lane vocabulary mismatch: `AGENTS.md` and
`scripts/agent_job_contract.py` only accept six task-card lanes, while GitHub
issue forms and several issue/task briefs use `repo-hygiene`, `runtime`, and
`cockpit` labels. That mismatch forces valid GitHub work into proxy task-card
lanes such as `Reporting`.

## Artifacts

- `instruction_surface_inventory.json` - classified instruction surface list.
- `contradiction_matrix.md` - evidence-backed findings and proposed action.
- `load_map.md` - default-loaded versus on-demand instruction surfaces.
- `patch_recommendations.md` - bounded follow-up patch plan and non-goals.
- `validation.json` - command-level validation record.

## Boundaries

No product/backend/frontend/runtime code, service config, model/GPU config,
production data, DB, Qdrant, news, memory, source registry, canonical financial
truth, parser routing, extraction prompt, gold label, or standing instruction
file was changed.
