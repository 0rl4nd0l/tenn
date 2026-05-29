---
job_id: extraction_period_semantics_aau_missing_period_end_v1_20260529
lane: Financial Truth
supporting_lanes:
  - Evaluation
  - Provenance
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_period_semantics_aau_missing_period_end_v1_20260529.md
  - financial-engine_v2/backend/app/services/multipass_extraction.py
  - financial-engine_v2/backend/tests/test_multipass_extraction.py
  - financial-engine_v2/backend/tests/test_extraction_pre_canary_truth_gates.py
  - reports/agent_jobs/extraction_period_semantics_aau_missing_period_end_v1_20260529/README.md
  - reports/agent_jobs/extraction_period_semantics_aau_missing_period_end_v1_20260529/status.json
  - reports/agent_jobs/extraction_period_semantics_aau_missing_period_end_v1_20260529/diff-check.json
  - docs/claude/STATE.md
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/extraction_period_semantics_aau_missing_period_end_v1_20260529
mutation_mode: safe_extension
requested_mutation_mode: implementation
production_data_access: false
github_mutation_allowed: none
related_issue: 96
---

# Extraction Period Semantics AAU Missing Period End V1

## Objective

Diagnose and fix the #96 third-canary AAU failure where the approved single
document run persisted `validation_gate:missing_period_end` even though the
source PDF explicitly contains `FOR THE YEAR ENDED 31 DECEMBER 2025`.

## Scope

- Primary lane: Financial Truth.
- Supporting lanes: Evaluation and Provenance.
- Mode: SAFE EXTENSION.
- Branch: `safe/extraction-period-semantics-aau-v1-20260529`.
- Worktree: `/home/l4nd0/tenn-period-semantics-aau-v1-20260529`.

## Contract Check

Target system layer: Extraction / Metric Extraction.

Relevant contract rules: backend is the sole authority; extraction must use
only explicit source values; ambiguity must fail visibly; no alternate pipeline,
fallback truth source, direct datastore mutation, parser-route mutation, prompt
mutation, schema change, or runtime/model/GPU/service change is allowed.

What must not change: validation hard-stop semantics, scale gates, source
document classification policy, parser routing, extraction prompts, gold labels,
schemas/migrations, runtime/model/GPU/service config, source PDFs, Cockpit UI,
GitHub state, direct DB/Qdrant writes, or broad canary/backfill behavior.

Why safe: the only allowed fix is a deterministic explicit-period extraction
from source text already produced by the canonical parser, used to fill a
missing `period_end` before the existing validation gate runs. It must not infer
from publication date, ticker, filename, or prior runs.

GPU process check required: no. This task must not start, restart, or spawn
llama-server and must not run live extraction jobs.

## Evidence

- Approved #96 third canary stopped after AAU run
  `523e018f-d342-4d1d-b239-8e92ecc4c5ce`.
- Persisted payload has `period_type=A`, `period_end=null`,
  `error=validation_gate:missing_period_end`.
- PDF text contains explicit source period wording:
  `FOR THE YEAR ENDED 31 DECEMBER 2025`.

## Implementation Rules

- Build a deterministic regression test before changing code.
- Use only explicit source-period wording.
- Do not infer from document publication date or file path.
- Preserve the existing validation gate rejecting missing or invalid period end.
- Preserve ambiguous-period fail-visible behavior.
- Do not run any canary, broad backfill, direct SQL mutation, or direct Qdrant
  mutation.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/extraction_period_semantics_aau_missing_period_end_v1_20260529.md`
- `python3 scripts/agent_job_registry.py list-active --read-only --repo-root .`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/extraction_period_semantics_aau_missing_period_end_v1_20260529.md --repo-root .`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/extraction_period_semantics_aau_missing_period_end_v1_20260529.md --repo-root .`
- Focused pytest for the new period semantics regression.
- Focused existing extraction truth-gate pytest.
- Targeted Ruff for changed Python files.
- `git diff --check`
- JSON validation for report artifacts.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/extraction_period_semantics_aau_missing_period_end_v1_20260529.md --repo-root .`
- Code-reviewer pass.
- Registry release and final `list-active`.

## Final Report Requirements

Report the branch, worktree, task card, exact root cause, files changed,
validation commands/results, registry release state, whether any runtime or
datastore mutation occurred, and the next safe step for the #96 canary.
