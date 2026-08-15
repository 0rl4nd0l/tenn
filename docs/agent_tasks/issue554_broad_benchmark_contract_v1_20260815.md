---
job_id: issue554_broad_benchmark_contract_v1_20260815
title: Add the fail-closed broad extraction benchmark contract for issue 554
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
github_mutation_allowed: true
merge_allowed: false
output_dir: reports/agent_jobs/issue554_broad_benchmark_contract_v1_20260815
closeout_scope: draft_pr
allowed_files:
  - docs/agent_tasks/issue554_broad_benchmark_contract_v1_20260815.md
  - docs/extraction/broad_extraction_benchmark_contract.md
  - financial-engine_v2/backend/app/services/broad_extraction_benchmark.py
  - financial-engine_v2/backend/tests/test_broad_extraction_benchmark.py
docs_impact: DOCS_UPDATED
docs_checked:
  - AGENTS.md
  - docs/extraction
docs_changed:
  - docs/agent_tasks/issue554_broad_benchmark_contract_v1_20260815.md
  - docs/extraction/broad_extraction_benchmark_contract.md
docs_followup: "Document the runner and frozen data artifacts only after a separately approved no-write corpus lane establishes their exact shape."
reason: "Issue 554 needs a deterministic scoring and validation seam before any source-bound corpus run or failure-class repair can make a defensible delta claim."
task_tier: medium
recommended_model: "high reasoning"
actual_model: "GPT-5 Codex"
why_this_model: "The code is small, but Financial Truth denominators, identity, provenance, and fail-closed gate semantics require careful review."
worker_model_allowed: false
worker_decision_limit: "No workers or subagents; the contract and focused tests remain in one local lane."
escalation_needed: false
task_scope: pure_broad_benchmark_contract_only
---

# Issue 554 broad benchmark contract

## Authority

- Live issue: `https://github.com/0rl4nd0l/tenn/issues/554`.
- Canonical base: `7a28721deb93dfefa3859a2d79bfca81453b54c5` on
  `origin/migration/clean-runtime-baseline-reconstruct-v1`.
- Reusable predecessor commit: `a4498cacbd844ceee26c4b798d1cc1f33538f8d1`.
- The predecessor's pure benchmark seam may be adopted and revised; the old
  unreviewed extractor branch and its generated report bundle must not be
  adopted wholesale.

## Objective

Add a pure, deterministic, fail-closed contract that validates the frozen
20-document, ten-metric evaluation shape and scores supplied observations for
correct recovery, incorrect values, abstentions, unsupported or unresolved
cells, period identity, currency, scale, source binding, and regressions.

This milestone supplies the scoring seam only. It does not claim that the
source-adjudicated corpus denominator exists or that extraction improved.

## Required behavior

- Require exactly 20 distinct issuers and all 200 document/metric expectation
  cells.
- Keep DATA_MISSING documents explicit and prevent their observations from
  improving quality gates.
- Require verified applicable expectations to carry raw value, raw unit,
  normalized value, period, currency where applicable, and source evidence.
- Score raw and normalized identity separately and expose currency, scale,
  period, provenance, and regression failures.
- Keep coverage over every predeclared applicable cell; compute accepted
  accuracy and identity rates from admitted observations, while unresolved or
  DATA_MISSING applicable cells remain visible in the coverage denominator.
- Reject malformed, duplicate, partial, or out-of-contract inputs before
  producing a score.
- Keep returned score structures immutable and deterministic.

## Hard stops

- Do not read, fetch, copy, create, modify, or adjudicate source PDFs, gold
  labels, corpus manifests, expected-value matrices, or production data.
- Do not run extraction, OCR, LLMs, the no-write corpus replay, services,
  queues, databases, Qdrant, Redis, backfills, migrations, or runtime commands.
- Do not modify extractor behavior, ontology, prompts, models, dependencies,
  canonical Financial Truth, or the merged PR #565 files.
- Do not copy the predecessor branch's 13 MB PDF or generated replay reports.
- Do not merge, deploy, activate, close the issue, or claim issue completion.

## Validation

- Task-card validation and changed-path allowlist check.
- Focused RED/GREEN benchmark-contract tests using synthetic in-memory data.
- Ruff for the two changed Python files when available.
- Python compilation for the two changed Python files.
- `git diff --check`.
- Independent final diff review.

## Closeout

Prepare at most a draft PR. Report the exact base, branch, commit, focused
validation, docs impact, and the remaining Tier-2 approval/data boundary for a
real frozen-corpus run and one source-proven repair.
