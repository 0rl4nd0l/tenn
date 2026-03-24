# docs/claude — Claude-Normalized Guide

This directory contains Claude-optimized consolidations of existing repo knowledge.
These docs do **not** replace the authoritative source files — they curate and cross-link them.

When in doubt, prefer the source file. When a conflict exists between a doc here and a source file, trust the source file and flag the conflict.

---

## Index

| Doc | Purpose |
|-----|---------|
| [project-overview.md](project-overview.md) | What this repo is, what it does, and who uses it |
| [STATE.md](STATE.md) | Active workstream tracker — what is planned, in-flight, verified, and shipped |
| [current-state.md](current-state.md) | Active runtime profile, local backend status, operational notes |
| [safety.md](safety.md) | Safety constraints, secret handling, and prohibited actions |
| [runbook.md](runbook.md) | Consolidated operational runbook with incident routing |
| [decisions.md](decisions.md) | Key architectural and operational decisions |
| [architecture/system-map.md](architecture/system-map.md) | Component map with ports and responsibilities |
| [architecture/data-flow.md](architecture/data-flow.md) | Data ingestion and retrieval pipeline flow |
| [skills/debugging.md](skills/debugging.md) | Debugging patterns for this codebase |
| [skills/performance.md](skills/performance.md) | Performance and GPU/inference guidance |
| [skills/implementation-discipline.md](skills/implementation-discipline.md) | Implementation process and pre-merge checklist |
| [skills/domain-financial-pipeline.md](skills/domain-financial-pipeline.md) | Domain-specific patterns for the financial pipeline |
| [skills/domain-news-substrate.md](skills/domain-news-substrate.md) | News pipeline architecture, invariants, and drift detection |
| [skills/domain-model-routing.md](skills/domain-model-routing.md) | Model routing roles, adaptive scoring, finance policy |
| [hooks.md](hooks.md) | All active automation hooks (Claude Code + git); includes PreToolUse sensitive-path warning and auto-pytest |
| [mcp-servers.md](mcp-servers.md) | MCP server inventory, prerequisites, troubleshooting, and workflow integration |
| [commands.md](commands.md) | All available slash commands, Claude-only skills, and subagents |
| [tasks/README.md](tasks/README.md) | Task process and template |
| [lessons.md](lessons.md) | Bug regression lessons — pattern + rule that prevents recurrence |
| [gap-analysis.md](gap-analysis.md) | Missing capabilities and recommended actions |
| [introduction-plan.md](introduction-plan.md) | Staged plan to introduce missing pieces safely |

---

## Source Trace

All docs in this directory were synthesized from:
- `docs/entrypoints.md`
- `docs/validation_baseline.md`
- `docs/current_system.md`
- `docs/architecture/` (18 docs, 00_README.md through model-routing.md)
- `docs/ops/` (30+ runbooks and incident docs)
- `docs/setup/environment.md`, `runtime.md`, `troubleshooting.md`
- `financial-engine_v2/README.md`
- `financial-engine_v2/.env.example`
- `agent_contract.json`
- `ruff.toml`, `pytest.ini`, `requirements.txt`
