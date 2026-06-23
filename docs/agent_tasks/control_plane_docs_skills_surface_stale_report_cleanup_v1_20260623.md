---
job_id: control_plane_docs_skills_surface_stale_report_cleanup_v1_20260623
lane: Reporting
supporting_lanes:
  - Evaluation
  - Repo Hygiene
owner: Codex
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 3600
output_dir: reports/agent_jobs/control_plane_docs_skills_surface_stale_report_cleanup_v1_20260623
mutation_mode: safe_extension
production_data_access: false
task_scope: control_plane_only
closeout_scope: docs_only
allowed_files:
  - docs/agent_tasks/control_plane_docs_skills_surface_stale_report_cleanup_v1_20260623.md
  - reports/agent_jobs/control_plane_docs_skills_surface_stale_report_cleanup_v1_20260623/README.md
  - reports/agent_jobs/control_plane_docs_skills_surface_stale_report_cleanup_v1_20260623/status.json
  - reports/agent_jobs/control_plane_docs_skills_surface_stale_report_cleanup_v1_20260623/stale_reference_matrix.json
  - reports/agent_jobs/control_plane_docs_skills_surface_stale_report_cleanup_v1_20260623/skills_surface_freshness_audit.json
  - reports/agent_jobs/control_plane_docs_skills_surface_stale_report_cleanup_v1_20260623/changed_docs_summary.md
  - docs/dev_flow/SKILLS_SURFACE.md
  - docs/dev_flow/CONTROL_PLANE_PR_STATE_REFRESH.md
  - docs/dev_flow/CONTROL_PLANE_STATUS.md
  - docs/dev_flow/CONTROL_PLANE_OPEN_WORK.md
  - "**/SKILLS_SURFACE.md"
  - docs/**/*.md
  - docs/**/*.json
  - AGENTS.md
  - CLAUDE.md
  - docs/agent_registry/**/*ledger*.md
  - docs/agent_registry/**/*ledger*.json
forbidden_files:
  - financial-engine_v2/data/**
  - financial-engine_v2/reports/**
  - backend/product/runtime source code
  - extraction/parser/evaluator/gold-label/prompt code
  - .github/workflows/**
  - scripts/**
  - .codex/**
  - .claude/**
  - DB/Qdrant/news/memory stores
  - source PDFs / ASX docs / production documents
  - secrets, env files, runtime binding files, migrations
---

# Control Plane Docs Skills Surface Stale Report Cleanup V1

## Objective

Clean up the next narrow stale-state documentation surfaces identified by the
current control-plane documentation audit:

- `SKILLS_SURFACE.md` freshness metadata.
- Stale report-state references for PR #378, PR #380, PR #373, and PR #367.

Primary lane: Reporting. Supporting lanes: Evaluation and Repo Hygiene.

## Scope

Allowed:

- Update `docs/dev_flow/SKILLS_SURFACE.md` freshness metadata with current,
  evidence-backed verification details.
- Correct direct stale report-state references for PR #378, PR #380, PR #373,
  and PR #367 in allowed documentation surfaces.
- Mark unverifiable references as `DATA_MISSING` instead of guessing.
- Write the required report artifacts under this task's report directory.

Out of scope:

- `/goal` monitor implementation or repo wrapper work.
- Git hook install script fixes.
- Legacy `.codex/skills` or `.claude/monitors` cleanup.
- Broad older PR ledger backfill.
- Broad documentation normalization or deletion.
- Tenn product, runtime, data, extraction, financial-truth, parser, evaluator,
  DB, Qdrant, news, memory, migration, hook implementation, CI workflow, or
  production document changes.

## Required Preflight

- Confirm branch, HEAD, worktree path, `git status --short
  --untracked-files=all`, `git worktree list`, and recent commits.
- Confirm `origin/migration/clean-runtime-baseline-reconstruct-v1` has been
  fetched, or record `DATA_MISSING`.
- Validate this task card if the validator exists.
- Check registry/list-active/check-overlap if available. Claim only if safe.
- Locate the latest documentation audit report that produced the finding about:
  `SKILLS_SURFACE.md` stale freshness metadata, stale old report states for PR
  #378/#380/#373/#367, `/goal monitor` repo `NOT_FOUND`, stale hook install
  docs, stale legacy `.codex/skills` and `.claude/monitors` surfaces, and
  task-ledger older PR entry backfill gaps.
- Treat only `SKILLS_SURFACE.md` stale freshness metadata and stale old report
  states for PR #378/#380/#373/#367 as in-scope for edits. The rest are
  follow-up findings unless directly referenced by the stale docs being
  corrected.

## Required Audit Pass

- Inspect current `SKILLS_SURFACE.md` freshness metadata, evidence source, and
  whether it appears hand-maintained or generated.
- Search for PR #378, PR #380, PR #373, and PR #367 references and stale
  report-state phrases in docs, `AGENTS.md`, `CLAUDE.md`, task ledger, report
  indexes, and status docs.
- Check live GitHub state for PR #378, PR #380, PR #373, and PR #367 if `gh` is
  available. If `gh` is unavailable or unauthenticated, use current repo
  evidence where possible and mark live GitHub state `DATA_MISSING`.
- Build a stale-reference matrix with path, stale claim, current evidence,
  correction needed, corrected yes/no, and reason if not corrected.

## Required Report Artifacts

Write under
`reports/agent_jobs/control_plane_docs_skills_surface_stale_report_cleanup_v1_20260623/`:

- `README.md`
- `status.json`
- `stale_reference_matrix.json`
- `skills_surface_freshness_audit.json`
- `changed_docs_summary.md`

The owner request allowed the broad report directory
`reports/agent_jobs/control_plane_docs_skills_surface_stale_report_cleanup_v1_20260623/**`.
This active task-card YAML enumerates the exact report artifacts because the
repo validator treats broad report globs as literal required artifact paths.

## Validation

- Task-card validation if available.
- Registry `list-active --read-only` and overlap checks if available.
- Grep/search before and after for PR #378/#380/#373/#367 stale phrases.
- `gh pr view` checks if available.
- Markdown lint/check if available.
- Link/path sanity check for changed docs if available.
- JSON validation for report artifacts.
- `git diff --check`.
- Changed-files versus allowed-files check.
- Final `git status --short --untracked-files=all`.

## Definition Of Done

- `SKILLS_SURFACE.md` freshness metadata is accurate and evidence-backed.
- Stale report-state references for PR #378/#380/#373/#367 are corrected or
  explicitly marked `DATA_MISSING`.
- No runtime/product/code/system behavior changed.
- Follow-up stale areas remain listed but are not dragged into this cleanup.
- Final report gives the next narrow cleanup candidate.
