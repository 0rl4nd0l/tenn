---
job_id: pr39_backend_architecture_invariant_reconciliation_v1_20260527
lane: Evaluation
supporting_lanes:
  - Repo Hygiene
  - Reporting
owner: Codex
allowed_files:
  - docs/agent_tasks/pr39_backend_architecture_invariant_reconciliation_v1_20260527.md
  - reports/agent_jobs/pr39_backend_architecture_invariant_reconciliation_v1_20260527/**
  - docs/architecture/06_embeddings_and_vector_store.md
  - docs/architecture/22_memory_ownership_map.md
  - financial-engine_v2/backend/tests/test_architecture_invariants.py
  - financial-engine_v2/backend/tests/test_cursor_rule_compliance.py
approval_required: true
timeout_seconds: 14400
output_dir: reports/agent_jobs/pr39_backend_architecture_invariant_reconciliation_v1_20260527
mutation_mode: safe_extension
requested_mutation_mode: audit_first_safe_extension
production_data_access: false
github_mutation_allowed: false
related_issue: 105
related_pr: 39
cluster_id: C01
operator_approval_source: "User goal request in Codex session 2026-05-27 for PR #39 C01 architecture-invariant reconciliation"
---

# PR #39 Backend Architecture Invariant Reconciliation

## Objective

Execute C01 from the preserved PR #39 / issue #105 failure-cluster audit:
`[CI] Reconcile backend sqlite3/uuid4/vector invariant failures for PR #39`.

This task is audit-first. Implementation is allowed only if the audit proves an
exact, low-risk contract, code, or focused-test fix. Before editing any
implementation, architecture-doc, or test file outside this card/report bundle,
this card must be updated with the exact repo-relative file paths to edit.
Broad globs are allowed only for the report output directory.

## Scope

- Primary lane: Evaluation.
- Supporting lanes: Repo Hygiene, Reporting.
- Mode: AUDIT_FIRST with SAFE_EXTENSION only after an explicit audit decision.
- Risk: HIGH because the invariant could hide backend safety regressions or
  over-block documented SQLite-backed memory and operational stores.
- Related issue: #105 remains open.
- Related PR: #39 remains open, draft, unmerged, and not merge-ready.
- Cluster: C01 only. Do not implement or audit C02-C13 except as needed to
  avoid confusing C01 evidence.

## Initial Allowed Writes

- `docs/agent_tasks/pr39_backend_architecture_invariant_reconciliation_v1_20260527.md`
- `reports/agent_jobs/pr39_backend_architecture_invariant_reconciliation_v1_20260527/**`

## Read-Only Inspection Scope

- `reports/agent_jobs/pr39_lint_and_test_failure_cluster_split_v1_20260526/**`
- `docs/architecture/SYSTEM_CONTRACT.md`
- `docs/architecture/06_embeddings_and_vector_store.md`
- `docs/architecture/10_failure_model.md`
- `docs/architecture/22_memory_ownership_map.md`
- Architecture invariant and cursor-rule tests found by repo search.
- Vector-store tests found by repo search.
- Exact code files named by the failing invariant output.

## Candidate Safe-Extension Files

Approved after audit decision:

- `docs/architecture/06_embeddings_and_vector_store.md`
- `docs/architecture/22_memory_ownership_map.md`
- `financial-engine_v2/backend/tests/test_architecture_invariants.py`
- `financial-engine_v2/backend/tests/test_cursor_rule_compliance.py`

Audit decision: C01 is a contract/test mismatch, not a production-code removal
task. The safe extension may clarify that SQLite is forbidden as a vector store
or canonical financial-truth store while documented qualitative memory,
operational state, feedback, and news projection stores remain explicit
exceptions. It may also narrow UUID checks to vector/chunk/canonical artifact
ID construction while preserving allowed operational/task/session ID usage.

## Forbidden Surfaces

- Production DB, Qdrant, news, or memory mutation.
- Canonical financial truth.
- Parser routing.
- Extraction prompts.
- Gold labels.
- Runtime/model/GPU/service config.
- Docker/runtime/service rebinding.
- Broad test relaxation.
- Deleting or weakening architecture invariants without a documented
  replacement contract.
- Removing documented SQLite-backed memory or operational-store ownership
  without a separate migration.
- One-off patches that only make a test green without resolving the architecture
  contract.
- Unrelated dirty work.
- PR #39 merge, rebase, cherry-pick, push, or update.
- GitHub issue closeout or PR comments.

## Required Audit Questions

- What exact C01 failures are current?
- Are the failures inherited from baseline, introduced by PR #39, or
  `DATA_MISSING`?
- Which invariant is failing: sqlite3 import policy, uuid4 deterministic-ID
  policy, vector ID contract, or something else?
- Does the repo intentionally support SQLite-backed qualitative memory or
  operational stores?
- If yes, how should the invariant encode that exception without weakening
  runtime/backend safety?
- Are any sqlite3 imports in forbidden runtime paths that should use an
  abstraction or different store?
- Are any uuid4 uses generating canonical/vector IDs that should be
  deterministic?
- Are vector IDs expected to be `document_id:chunk_index`, content hash, or
  another deterministic scheme?
- What tests prove the contract after remediation?

## Required Outputs

Write all outputs under
`reports/agent_jobs/pr39_backend_architecture_invariant_reconciliation_v1_20260527/`:

- `README.md`
- `status.json`
- `invariant_matrix.json`
- `c01_decision_record.md`
- `validation.log` or `validation_summary.md`

## Validation

Run focused, non-production checks only:

- Task-card validate.
- Registry list-active, check-overlap, claim, and release if safe.
- Focused architecture invariant tests found by audit.
- Focused vector-store ID tests found by audit.
- Focused cursor-rule compliance tests found by audit.
- Targeted ruff/format checks on changed Python files when applicable.
- JSON parse validation for generated JSON.
- `git diff --check`.
- `git diff --cached --check` only if staging occurs.
- Task-card check-diff.

Do not run production services or any broad refetch, reindex, backfill, news,
memory, extraction, parser, gold-label, canonical-truth, runtime-config, or PR
mutation workflow.

## Commit Policy

If a minimal safe-extension fix lands and validation passes, commit only if the
repo workflow allows committing and the staged set is exactly within
`allowed_files`. If unrelated dirty work prevents a clean commit, do not clean
it; write a report-local parking recommendation.

Suggested commit message:
`fix(evaluation): reconcile pr39 backend architecture invariants`
