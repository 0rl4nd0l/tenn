---
job_id: extraction_real_gold_source_path_resolver_v1_20260601
lane: Financial Truth
supporting_lanes:
  - Evaluation
  - Provenance
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_real_gold_source_path_resolver_v1_20260601.md
  - docs/claude/STATE.md
  - financial-engine_v2/backend/app/main.py
  - financial-engine_v2/backend/tests/test_extraction_gold_eval.py
  - reports/agent_jobs/extraction_real_gold_source_path_resolver_v1_20260601/README.md
  - reports/agent_jobs/extraction_real_gold_source_path_resolver_v1_20260601/status.json
  - reports/agent_jobs/extraction_real_gold_source_path_resolver_v1_20260601/validation.json
  - reports/agent_jobs/extraction_real_gold_source_path_resolver_v1_20260601/diff-check.json
  - reports/agent_jobs/extraction_real_gold_source_path_resolver_v1_20260601/source_path_probe_before.json
  - reports/agent_jobs/extraction_real_gold_source_path_resolver_v1_20260601/source_path_probe_after.json
approval_required: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/extraction_real_gold_source_path_resolver_v1_20260601
mutation_mode: safe_extension
requested_mutation_mode: real_gold_eval_source_path_resolver_fix
production_data_access: false
github_mutation_allowed: none
related_issue: 96
operator_approval_source: "User requested continuation of /tmp/tenn_metric_extraction_handoff_2026-05-31.md toward full extraction graduation. This task is bounded to a backend real-gold eval source-path resolver fix and does not run runtime extraction."
---

# Extraction Real-Gold Source Path Resolver V1

## Objective

Fix the backend real-gold eval source-file resolver so current local runtime
bindings can open the canonical real-gold fixture PDFs before a broader
graduation eval run.

The current blocker is that `app.main._resolve_real_gold_source_path()` only
checks the repo root and `financial-engine_v2/` parent paths. In this checkout,
the real source PDFs are available through the existing `/data/asx/docs`
binding, and the confirmed-metric coverage resolver already handles that
allowlisted root.

This task enables a future real-gold eval run. It does not run extraction.

## Approved Scope

Approved edits:

- Reuse the existing allowlisted confirmed-metric coverage source resolver for
  real-gold eval source paths.
- Keep existing local-path validation and fail-closed behavior.
- Add tests proving real-gold eval resolves `/data/asx/docs`-style source
  bindings without accepting unsafe paths.
- Record before/after source-path probe artifacts.
- Update `docs/claude/STATE.md` with the bounded result.

Not approved:

- Runtime startup or backend reload.
- `POST /api/extraction-eval/real-gold`.
- `POST /api/process/document/{document_id}`.
- Broad backfill or `/process/ticker`.
- Direct SQL mutation.
- Source PDF copy, mutation, deletion, or symlink changes.
- Parser routing, prompts, schemas, migrations, Qdrant/news/memory writes,
  Cockpit UI, or GitHub mutation.

## Session Declaration

Agent: Codex

Branch: `migration/clean-runtime-baseline-reconstruct-v1`

Worktree: `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`

Lane: Financial Truth

Execution mode: SAFE EXTENSION.

Intended files: this task card, `financial-engine_v2/backend/app/main.py`,
`financial-engine_v2/backend/tests/test_extraction_gold_eval.py`,
`docs/claude/STATE.md`, and this report bundle.

Contested surfaces touched: backend real-gold eval source-path implementation.

Collision risk: HIGH because this touches backend financial-truth evaluation
readiness. Proceed only after registry overlap checks and claim succeed.

Decision: proceed after validation, active-job check, overlap check, and claim.

## Contract Check

Target system layers: Evaluation/Provenance around backend-owned extraction
evaluation. The change only affects how real-gold eval opens already-declared
source PDF paths before extraction.

Relevant contract rules: `SYSTEM_CONTRACT.md` §1.1 backend source of truth,
§2 mandatory flow, §3.3 explicit-only metric extraction, §3.5 normalization,
and §4 data preservation.

What must not change: extraction logic, metric values, fixture labels, source
PDFs, parser routing, prompts, schemas/migrations, canonical financial rows,
Qdrant/news/memory stores, runtime services, and Cockpit UI.

Why safe: this reuses an existing allowlisted local PDF resolver and keeps
missing or unsafe paths fail-closed. It removes a local path-binding blocker
without weakening metric truth or running extraction.

GPU process check required: no, this task does not start llama.cpp, backend,
worker, or run extraction.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/extraction_real_gold_source_path_resolver_v1_20260601.md --write-report`
- `python3 scripts/agent_job_registry.py list-active --read-only --repo-root .`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/extraction_real_gold_source_path_resolver_v1_20260601.md --repo-root .`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/extraction_real_gold_source_path_resolver_v1_20260601.md --repo-root .`
- Before/after source-path probes over all canonical real-gold fixtures.
- Focused real-gold eval tests.
- Targeted Ruff on touched files.
- `py_compile` for touched Python files.
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/extraction_real_gold_source_path_resolver_v1_20260601.md --repo-root .`
- Registry release and final active-job read-only check.
