---
job_id: docs_current_state_consolidation_v1_20260623
lane: Reporting
supporting_lanes:
  - Memory
  - Evaluation
  - Repo Hygiene
owner: Codex
approval_required: false
allow_unapproved_safe_extension: true
allow_audit_code_changes: true
timeout_seconds: 10800
output_dir: reports/agent_jobs/docs_current_state_consolidation_v1_20260623
mutation_mode: safe_extension
requested_mutation_mode: audit_first_then_docs_only_safe_extension
production_data_access: false
allowed_files:
  - docs/**/*.md
  - docs/**/*.json
  - docs/**/*.csv
  - AGENTS.md
  - CLAUDE.md
  - README.md
  - .agents/skills/**/*.md
  - docs/agent_tasks/docs_current_state_consolidation_v1_20260623.md
  - docs/agent_registry/merge_parking/**
  - docs/README.md
  - docs/agents/domain.md
  - docs/architecture/model-routing.md
  - docs/claude/current-state.md
  - docs/current_system.md
  - docs/dev_flow/SKILLS_SURFACE.md
  - docs/entrypoints.md
  - docs/prompts/CODEX_MASTER_PROMPT.md
  - docs/setup/environment.md
  - docs/startup.md
  - reports/agent_jobs/docs_current_state_consolidation_v1_20260623/README.md
  - reports/agent_jobs/docs_current_state_consolidation_v1_20260623/status.json
  - reports/agent_jobs/docs_current_state_consolidation_v1_20260623/doc_inventory.json
  - reports/agent_jobs/docs_current_state_consolidation_v1_20260623/doc_conflict_matrix.json
  - reports/agent_jobs/docs_current_state_consolidation_v1_20260623/evidence_manifest.json
  - reports/agent_jobs/docs_current_state_consolidation_v1_20260623/changed_docs_summary.md
  - reports/agent_jobs/docs_current_state_consolidation_v1_20260623/subagent_findings/README.md
forbidden_files:
  - financial-engine_v2/data/**
  - financial-engine_v2/reports/**
  - "**/*.db"
  - "**/*.sqlite"
  - "**/*.parquet"
  - "source PDFs / ASX docs / production documents"
  - "backend/runtime code"
  - "extraction/parser/gold-label/evaluator logic except documentation references"
  - "Qdrant/Postgres/SQLite data stores"
  - "Docker volumes, service configs, runtime binding files, migrations, secrets"
  - .github/workflows/**
---

# Docs Current State Consolidation V1

## Objective

Update and consolidate Tenn repo documentation into a smaller, evidence-backed,
agent-navigable documentation system. The primary lane is Reporting, supported
by Memory, Evaluation, and Repo Hygiene.

The outcome must reduce active sources of truth, clarify where future Codex,
Claude, and GPT agents should start, mark stale or historical documents as
archive/reference-only where safe, and produce a report-local evidence manifest
for current-state claims.

## Mode

Audit first, then docs-only safe extension if collision risk is LOW or MEDIUM.
Downgrade to report-only if the audit finds HIGH collision risk, required code
changes, production data access, or owner-boundary conflicts.

## Required Preflight

- Confirm working path, branch, HEAD, upstream, remotes, git status,
  worktrees, and recent commits.
- Validate this task card with the repo validator if available.
- Inspect read-only registry active jobs and overlap checks if available.
- Inspect live and committed task-ledger availability.
- Classify dirty and untracked files as own-scope docs dirt, foreign dirt,
  contested docs surfaces, or forbidden runtime/data surfaces.
- Confirm available documentation surfaces: `AGENTS.md`, `CLAUDE.md`,
  `README.md`, docs indexes, architecture docs, task cards, registry docs,
  report bundles, `.agents/skills`, and source/current-state maps.

## Required Scout Passes

- Repo State and Worktree Scout.
- Documentation Inventory Scout.
- Runtime / Topology Documentation Fact Checker.
- Agent Navigation / Onboarding Scout.
- Evidence and Architecture Guard.
- Final Reviewer / Diff Guard.

Actual subagents may be used when available. If they are unavailable, the parent
agent must emulate the passes internally and report each pass separately.

## Documentation Strategy

- Prefer a small canonical set over many new documents.
- Keep `AGENTS.md` concise and route details into docs or skills.
- Add or update a docs index/source map when it reduces navigation cost.
- Time-bound volatile facts such as branch, HEAD, worktree, active jobs, ports,
  services, and dirty state with "last verified" evidence.
- Separate configured/expected, observed during audit, historical, and
  `DATA_MISSING` runtime or topology statements.
- Prefer marking stale docs archive/deprecated/reference-only via canonical
  indexes or short top notes over deleting files.

## Hard Boundaries

- Do not edit product, runtime, backend, extraction, parser, prompt, gold-label,
  evaluator, schema, migration, service, model, GPU, DB, Qdrant, Redis, news,
  memory-store, source-document, or production-data behavior.
- Do not run production extraction or mutate production data.
- Do not start, stop, rebind, restart, or reload services.
- Do not clean, stash, reset, delete, prune, merge, rebase, force-release,
  push, or open a PR without separate explicit approval.
- Do not merge parked work.
- Do not make broad architecture decisions beyond documentation consolidation.
- Do not claim global correctness; claim only inspected and updated surfaces.

## Required Report Artifacts

Write these under
`reports/agent_jobs/docs_current_state_consolidation_v1_20260623/`:

- `README.md`
- `status.json`
- `doc_inventory.json` or `doc_inventory.csv`
- `doc_conflict_matrix.json`
- `evidence_manifest.json`
- `changed_docs_summary.md`
- `subagent_findings/` or equivalent pass sections

The validator treats broad report globs as literal required artifact paths, so
the active `allowed_files` list enumerates the exact report artifacts above
instead of relying on the requested broad report-directory glob.

## Validation

- Task-card validation if available.
- Registry `list-active --read-only` and overlap checks if available.
- `git diff --check`.
- Changed-files versus allowed-files check.
- Markdown link/path sanity checks for changed docs.
- Markdown formatting/lint if available.
- Grep/search for stale conflicting references in changed docs and key
  entrypoints.
- JSON validity for generated evidence/status files.
- No forbidden file changes.
- Final `git status --short --untracked-files=all`.

## Definition Of Done

- A future agent can start at the top-level docs and know where to go next.
- Current-state statements are evidence-backed and timestamped.
- Fragmented docs are mapped, consolidated, or clearly demoted to
  archive/reference status.
- No runtime/product/financial-truth/data behavior changed.
- All changed files stay inside this task-card scope.
- Validation and remaining `DATA_MISSING` are reported honestly.
