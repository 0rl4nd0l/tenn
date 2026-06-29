# Tenn Project Boundaries

Last verified: 2026-06-29T18:35:22+1000.

Verification scope: Tenn documentation and agent routing only. This document
does not prove runtime functionality for Tenn or any sibling project.

Source evidence:

- Task card:
  `docs/agent_tasks/greyhound_project_boundary_docs_v1_20260629.md`
- Review board:
  `/home/l4nd0/tenn/reports/agent_jobs/tenn_greyhound_repo_separation_review_board_20260629T175721+1000/`
- Fresh Tenn task worktree:
  `/home/l4nd0/tenn-greyhound-project-boundary-docs-v1-20260629`
- Fresh Tenn task branch:
  `docs/greyhound-project-boundary-v1-20260629`
- Initial Tenn task base:
  `3b32b8b3be8b04bb5a198c71ec928db182438f17`
- Publish refresh canonical parent:
  `6c486d07743d3483d05fa163dc5c02fd66b68863`

## Boundary Rule

Tenn is the ASX financial data ingestion, extraction, and cockpit workflow
repository. Its main runtime code lives under `financial-engine_v2/`, with
repo-level scripts and evaluation helpers under `scripts/`.

Greyhound racing prediction, collector, odds, SQLite/runtime artifact, model,
and daemon work is an external sibling project. Greyhound is not a Tenn
subsystem, even when a current filesystem path contains `tenn`.

Agents must route Tenn and Greyhound work through separate project identities:

| Work class | Project owner | Routing rule |
| --- | --- | --- |
| ASX filings, source-bound financial metrics, extraction prompts/parsers, Cockpit, Tenn RAG, Tenn memory/news stores, Tenn control-plane docs | Tenn | Use Tenn repo instructions, Tenn task cards, Tenn reports, and Tenn validation gates. |
| Greyhound race data, odds capture, prediction models, SQLite/live odds DBs, `shadow-autopilot.service`, Greyhound runtime artifacts, Greyhound evidence roots | Greyhound | Use the Greyhound repo/worktree, Greyhound-scoped task cards or reports, and Greyhound runtime proof. |

## Agent Handling Rules

- Do not treat Greyhound repo dirt, services, DBs, artifacts, branches, or
  worktrees as Tenn subsystem state.
- Do not edit Greyhound files from a Tenn task card unless the task card
  explicitly names a Greyhound-owned file and the owner has approved a
  cross-project exception.
- Do not move Greyhound paths, rewrite Greyhound service units, clean
  Greyhound artifacts, or mutate Greyhound DBs as Tenn repo hygiene.
- Do not use Tenn runtime, extraction, financial-truth, or Cockpit validation
  as evidence that Greyhound functionality works.
- Do not use Greyhound daemon activity, odds output, or prediction artifacts as
  evidence that Tenn functionality works.
- If an operator asks for Greyhound work while the current checkout is Tenn,
  stop before mutation and retarget to a Greyhound-specific worktree or write a
  no-write handoff/manifest.

## Filesystem Path Caveat

The review board found Greyhound under current NVMe paths that include `tenn`
in the parent directory name. That path label is not the project boundary.
Repository identity, runtime ownership, task-card scope, report lane, and
runtime proof define the boundary.

Physical Greyhound relocation is a separate workstream. It requires owner
approval, a no-write relocation manifest, service-unit inventory, DB/artifact
inventory, rollback steps, and Runtime Functionality Proof before any moved
runtime can be called working.

## Tenn Task Cards

Tenn task cards should keep Greyhound out of `allowed_files` unless the card is
explicitly a cross-project boundary or handoff task. Normal Tenn task cards
should not include:

- Greyhound repo files.
- Greyhound DBs or SQLite files.
- Greyhound systemd units.
- Greyhound runtime artifact roots.
- Greyhound branch, worktree, or cleanup operations.
- Greyhound GitHub issue or PR writes.

When a Tenn task needs to mention Greyhound for routing clarity, prefer a
docs-only or report-local note that names Greyhound as an external sibling
project, not a Tenn subsystem.
