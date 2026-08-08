---
job_id: agent_markdown_codex_repo_docs_refresh_v1_20260525
lane: Reporting
supporting_lanes:
  - Repo Hygiene
  - Evaluation
owner: Codex
allowed_files:
  - docs/agent_tasks/agent_markdown_codex_repo_docs_refresh_v1_20260525.md
  - reports/agent_jobs/agent_markdown_codex_repo_docs_refresh_v1_20260525/README.md
  - reports/agent_jobs/agent_markdown_codex_repo_docs_refresh_v1_20260525/status.json
  - reports/agent_jobs/agent_markdown_codex_repo_docs_refresh_v1_20260525/validation.json
  - reports/agent_jobs/agent_markdown_codex_repo_docs_refresh_v1_20260525/diff-check.json
  - reports/agent_jobs/agent_markdown_codex_repo_docs_refresh_v1_20260525/instruction_surface_inventory.json
  - reports/agent_jobs/agent_markdown_codex_repo_docs_refresh_v1_20260525/contradiction_matrix.md
  - reports/agent_jobs/agent_markdown_codex_repo_docs_refresh_v1_20260525/load_map.md
  - reports/agent_jobs/agent_markdown_codex_repo_docs_refresh_v1_20260525/patch_recommendations.md
approval_required: false
timeout_seconds: 7200
stale_after_seconds: 7200
output_dir: reports/agent_jobs/agent_markdown_codex_repo_docs_refresh_v1_20260525
mutation_mode: audit_only
allow_audit_code_changes: true
production_data_access: false
github_mutation_allowed: pr_create
related_issue: 78
---

# Agent Markdown and Codex Repo Documentation Audit

## Objective

Advance issue #78 with an evidence-bound audit of Tenn agent-facing Markdown
and Codex/repo workflow documentation. This slice is audit-only: it inventories
instruction surfaces, identifies contradictions or instruction bloat, maps
default-loaded versus on-demand guidance, and proposes bounded follow-up patch
scope without editing standing instructions.

## Session Declaration

- Agent: Codex.
- Worktree:
  `/home/l4nd0/tenn-repo-hygiene-agent-docs-refresh-audit-v1-20260601`.
- Branch: `audit/repo-hygiene-agent-docs-refresh-v1-20260601`.
- Parent live branch: `migration/clean-runtime-baseline-reconstruct-v1`.
- Issue: #78.
- Primary task-card lane: Reporting.
- Supporting scope: Repo Hygiene and Evaluation.
- Intended files: this task card and this job's report artifacts only.
- Contested surfaces touched: none.
- Collision risk: LOW after active-registry overlap check; shared
  `docs/claude/STATE.md` is intentionally not touched because another active
  Financial Truth job owns it.
- Decision: proceed in AUDIT MODE only.

## Contract Check

- Target system layer: agent/documentation control-plane reporting only.
- Relevant contract rules: backend remains sole authority; Cockpit remains
  client/orchestration only; no retrieval, storage, extraction, runtime, memory,
  or financial truth mutation.
- What must not change: product/backend/frontend/runtime code, service config,
  model/GPU configuration, DB/Qdrant/news/memory state, canonical financial
  truth, parser routing, extraction prompts, gold labels, and shared branch
  dirty work.
- Why safe: this job writes only allowlisted report artifacts in an isolated
  worktree and leaves default-loaded instructions unchanged until evidence
  supports a narrower patch.
- GPU process check required: no. This job does not spawn, restart, or depend
  on `llama-server`.

## Required Behavior

- Inventory agent-facing instruction/documentation surfaces with evidence.
- Classify each surface as one of `core_stable_contract`,
  `specialized_workflow`, `stale_or_conflicting`, `duplicate`, `missing`, or
  `DATA_MISSING`.
- Identify contradictions, stale guidance, duplicated default-loaded rules, and
  unsafe instruction bloat.
- Produce an agent instruction load map for Codex, Claude, Gemini, GitHub issue
  work, task-card jobs, and report/closeout workflows.
- Recommend bounded docs edits only where current evidence proves stale,
  conflicting, duplicated, missing, or dangerously overbroad guidance.

## Forbidden

- Product/backend/frontend/runtime code changes.
- DB, Qdrant, news, memory, source-registry, production data, or canonical
  financial truth mutation.
- Parser routing, extraction prompt, gold-label, model/runtime/GPU/service
  config mutation.
- Branch cleanup, deletion, reset, stash, rebase, merge, cherry-pick, or prune.
- Broad rewrite of `AGENTS.md`, `CLAUDE.md`, or standing instruction files.
- Touching `docs/claude/STATE.md` while the active Financial Truth job owns it.
- Live GitHub issue closeout; PR creation is allowed by this task card.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/agent_markdown_codex_repo_docs_refresh_v1_20260525.md`
- `python3 scripts/agent_job_registry.py list-active --read-only`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/agent_markdown_codex_repo_docs_refresh_v1_20260525.md --repo-root .`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/agent_markdown_codex_repo_docs_refresh_v1_20260525.md --repo-root .`
- Instruction-surface inventory commands recorded in `validation.json`.
- JSON validation for report JSON files.
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/agent_markdown_codex_repo_docs_refresh_v1_20260525.md --repo-root .`
- Registry release and final status check.

## Final Report Requirements

- Files changed.
- Exact validation commands and results.
- Instruction surface inventory summary.
- Contradiction/bloat matrix.
- Agent instruction load map.
- Patch recommendations and explicit non-recommendations.
- Explicit statement that no product/runtime/data/default-instruction files were
  changed.
