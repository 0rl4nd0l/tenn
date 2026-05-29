---
job_id: extraction_aau_period_fixture_integration_v1_20260529
lane: Financial Truth
supporting_lanes:
  - Evaluation
  - Provenance
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_aau_period_fixture_integration_v1_20260529.md
  - docs/agent_tasks/extraction_period_semantics_aau_missing_period_end_v1_20260529.md
  - docs/agent_tasks/extraction_aau_canary_failure_gold_fixture_v1_20260529.md
  - docs/claude/STATE.md
  - financial-engine_v2/backend/app/services/multipass_extraction.py
  - financial-engine_v2/backend/tests/test_multipass_extraction.py
  - financial-engine_v2/backend/tests/test_extraction_pre_canary_truth_gates.py
  - financial-engine_v2/backend/tests/fixtures/extraction_gold/aau_a_2025-12-31_canary_regression.json
  - financial-engine_v2/backend/tests/test_extraction_gold_eval.py
  - reports/agent_jobs/extraction_period_semantics_aau_missing_period_end_v1_20260529/README.md
  - reports/agent_jobs/extraction_period_semantics_aau_missing_period_end_v1_20260529/status.json
  - reports/agent_jobs/extraction_period_semantics_aau_missing_period_end_v1_20260529/diff-check.json
  - reports/agent_jobs/extraction_aau_canary_failure_gold_fixture_v1_20260529/README.md
  - reports/agent_jobs/extraction_aau_canary_failure_gold_fixture_v1_20260529/source_verification.json
  - reports/agent_jobs/extraction_aau_canary_failure_gold_fixture_v1_20260529/status.json
  - reports/agent_jobs/extraction_aau_canary_failure_gold_fixture_v1_20260529/diff-check.json
  - reports/agent_jobs/extraction_aau_period_fixture_integration_v1_20260529/README.md
  - reports/agent_jobs/extraction_aau_period_fixture_integration_v1_20260529/status.json
  - reports/agent_jobs/extraction_aau_period_fixture_integration_v1_20260529/diff-check.json
  - reports/agent_jobs/extraction_aau_period_fixture_integration_v1_20260529/integration_manifest.json
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/extraction_aau_period_fixture_integration_v1_20260529
mutation_mode: safe_extension
production_data_access: false
github_mutation_allowed: none
related_issue: 96
---

# Extraction AAU Period Fixture Integration V1

## Objective

Integrate the two already-published AAU follow-up branches onto the current
clean baseline so the source-period fix and the hand-verified AAU eval fixture
can be validated together before any further #96 canary run.

Source commits to absorb:

- `cb496fc1` — `milestone(extraction): harden explicit period-end semantics`
- `eb6ba6a5` — `milestone(extraction): record period-semantics claim release`
- `365bbef7` — `milestone(extraction): capture AAU canary failure fixture`
- `1be18324` — `milestone(extraction): record AAU fixture claim release`

## Scope

- Primary lane: Financial Truth.
- Supporting lanes: Evaluation and Provenance.
- Mode: SAFE EXTENSION.
- Branch: `safe/extraction-aau-integrated-baseline-v1-20260529`.
- Worktree: `/home/l4nd0/tenn-extraction-aau-integration-v1-20260529`.
- Base: `migration/clean-runtime-baseline-reconstruct-v1` at
  `d55a515376e2bd065be9c94843d07ccca06f99f2`.

## Contract Check

Target system layer: Extraction and Evaluation.

Relevant contract rules: backend remains the sole authority; metric extraction
must use explicit source values only; ambiguity and missing source context must
fail visibly; evaluation changes must remain deterministic; no parallel pipeline
or datastore write path may be introduced.

What must not change: production DB/Qdrant/news/memory stores, source PDFs,
parser routing, extraction prompts, gold labels outside the test-only fixture,
schemas/migrations, runtime/model/GPU/service config, Cockpit UI, GitHub state,
or the approved canary packet.

Why safe: this task integrates source-backed fixes and test-only eval evidence
from isolated branches into a new isolated baseline-derived branch, then runs
focused validation. It does not start services, run canaries, backfill, or write
canonical financial truth.

GPU process check required: no. This task must not spawn, restart, stop, or
depend on `llama-server`.

Architecture check: `.cursor/rules/*` files are DATA_MISSING in this checkout,
so compliance is enforced against `docs/architecture/SYSTEM_CONTRACT.md`.

## Hard Stops

- Do not edit the shared baseline branch.
- Do not run a third canary or AAU live extraction.
- Do not run broad backfill.
- Do not perform production DB writes or direct SQL mutation.
- Do not mutate Qdrant, news, or memory stores.
- Do not edit, move, copy, delete, or commit source PDFs.
- Do not change parser routing, prompts, schemas, runtime/model/GPU config,
  services, Cockpit UI, or GitHub state.
- Stop on unresolved merge conflict that would require semantic redesign beyond
  combining the two source branches.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/extraction_aau_period_fixture_integration_v1_20260529.md`
- `python3 scripts/agent_job_registry.py list-active --read-only --repo-root .`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/extraction_aau_period_fixture_integration_v1_20260529.md --repo-root .`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/extraction_aau_period_fixture_integration_v1_20260529.md --repo-root .`
- Cherry-pick source commits with `-n` into this worktree.
- Focused pytest for the new AAU period/eval regressions.
- `test_extraction_pre_canary_truth_gates.py`.
- `test_multipass_extraction.py`.
- `test_extraction_gold_eval.py` with the known unrelated 10X asset-path test
  deselected.
- Targeted Ruff and `py_compile` for touched Python files.
- JSON validation for all fixture/report artifacts.
- `git diff --check`.
- Source PDF/rendered-image staging check.
- Credential-pattern scan.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/extraction_aau_period_fixture_integration_v1_20260529.md --repo-root .`
- Code-reviewer pass.
- Registry release and final read-only active-job check.

## Final Report Requirements

Report branch, HEAD, worktree, source commits absorbed, conflicts if any,
validation commands/results, registry release state, files changed, known
unrelated validation gaps, whether runtime/datastore/source-PDF mutation
occurred, and the next safe step toward the #96 third canary.
