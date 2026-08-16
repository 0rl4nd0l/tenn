---
job_id: issue554_v2_execution_support_20260816
title: Add fail-closed v2 broad-corpus execution support without invoking it
lane: Financial Truth
supporting_lanes:
  - Evaluation
  - Provenance
owner: Codex
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 7200
mutation_mode: safe_extension
production_data_access: false
github_mutation_allowed: false
merge_allowed: false
output_dir: reports/agent_jobs/issue554_v2_execution_support_20260816
closeout_scope: ready_for_review
allowed_files:
  - docs/agent_tasks/issue554_v2_execution_support_20260816.md
  - docs/extraction/broad_extraction_benchmark_contract.md
  - scripts/extraction_no_write_replay.py
  - scripts/test_extraction_no_write_replay.py
  - scripts/run_broad_extraction_benchmark_v2.py
  - scripts/test_run_broad_extraction_benchmark_v2.py
  - reports/agent_jobs/issue554_v2_execution_support_20260816/README.md
  - reports/agent_jobs/issue554_v2_execution_support_20260816/STATE.md
  - reports/agent_jobs/issue554_v2_execution_support_20260816/DECISIONS.md
  - reports/agent_jobs/issue554_v2_execution_support_20260816/VALIDATION.md
  - reports/agent_jobs/issue554_v2_execution_support_20260816/RUN_OUTCOME.json
  - reports/agent_jobs/issue554_v2_execution_support_20260816/PR_REVIEW.md
  - reports/agent_jobs/issue554_v2_execution_support_20260816/CODE_REVIEW.json
docs_impact: DOCS_UPDATED
docs_checked:
  - AGENTS.md
  - docs/extraction/broad_extraction_benchmark_contract.md
docs_changed:
  - docs/extraction/broad_extraction_benchmark_contract.md
docs_followup: "The separately authorized execution gate must record the real receipt and published output hashes."
reason: "The v2 runner introduces a new operator command, artifact contract, and one-shot safety boundary."
task_tier: large
recommended_model: "high reasoning"
actual_model: "GPT-5 Codex"
why_this_model: "One-shot receipt placement, source identity, atomic publication, and v1 compatibility are coupled correctness concerns."
worker_model_allowed: false
worker_decision_limit: "No delegated source, corpus, execution-authority, or scoring decisions."
escalation_needed: false
task_scope: issue554_v2_execution_support_only
---

# Issue 554 v2 execution support

## Authority

The user authorized Tier 1 implementation and focused validation for the exact
v2 successor corpus, while explicitly withholding extraction and scoring
authority. The implementation base is audited HEAD
`bc901dd531498645b772ca840fd81871a3ac6b02`, whose merge-base is canonical
commit `2bd1033e6e202998be6db82858c75a8119f7ac40` and whose canonical tree is
`cb66c5961b78cc2d6a35b35e70e3b9f4685215db`.

## Objective

Add a separate v2 benchmark runner and the smallest replay extension needed to
accept only the exact hash-bound v2 manifest/corpus, require all twenty declared
sources and results, consume one-shot authority atomically immediately before
launch, and publish complete staged outputs atomically.

## Hard boundaries

- Do not run extraction or scoring, create a real invocation receipt, or create
  real v2 benchmark outputs.
- Leave the predecessor v1 benchmark runner, corpus, reports, and consumed
  evidence unchanged.
- Do not change source PDFs, v2 corpus/expectation/source-manifest/case files,
  parser or extractor behavior, canonical Financial Truth, dependencies,
  runtime, services, queues, DB, Redis, Qdrant, models, prompts, or GPUs.
- Do not mutate GitHub, the shared registry, or the shared task ledger.
- Do not merge, deploy, clean, reset, stash, overwrite, unlink, retry, or
  substitute missing evidence.

## Validation

Use synthetic temporary fixtures and mocks only. Tests may exercise receipt and
publication mechanics in temporary directories but must never point at the real
v2 output root or launch the real replay command. Run focused unittest/pytest,
Ruff when available, Python compilation, JSON/YAML validation where applicable,
and `git diff --check`.

## Stop states

Stop at `READY_FOR_REVIEW`, `DATA_MISSING`, or `EVIDENCE_CONFLICT`. Any need for
real v2 execution, source-content change, dependency installation, shared-state
mutation, or a different base requires new authority.
