---
job_id: issue554_amcr_successor_corpus_v2_20260816
title: Admit the exact AMCR FY2025 PDF into an immutable successor corpus
lane: Financial Truth
supporting_lanes:
  - Evaluation
  - Provenance
owner: Codex
approval_required: true
allow_unapproved_safe_extension: false
timeout_seconds: 7200
mutation_mode: safe_extension
production_data_access: false
github_mutation_allowed: false
merge_allowed: false
output_dir: reports/agent_jobs/issue554_amcr_successor_corpus_v2_20260816
closeout_scope: owner_decision
allowed_files:
  - docs/agent_tasks/issue554_amcr_successor_corpus_v2_20260816.md
  - financial-engine_v2/data/asx/docs/AMCR/annual_reports/2025-09-23_amcor-plc-fy2025-annual-report-sec-ars.pdf
  - financial-engine_v2/data/broad_extraction_benchmark/v2/README.md
  - financial-engine_v2/data/broad_extraction_benchmark/v2/corpus.json
  - financial-engine_v2/data/broad_extraction_benchmark/v2/expectations.json
  - financial-engine_v2/data/broad_extraction_benchmark/v2/source_manifest.json
  - financial-engine_v2/data/extraction_no_write_cases/issue554_broad_corpus_v2.json
  - reports/agent_jobs/issue554_amcr_successor_corpus_v2_20260816/README.md
  - reports/agent_jobs/issue554_amcr_successor_corpus_v2_20260816/STATE.md
  - reports/agent_jobs/issue554_amcr_successor_corpus_v2_20260816/DECISIONS.md
  - reports/agent_jobs/issue554_amcr_successor_corpus_v2_20260816/VALIDATION.md
  - reports/agent_jobs/issue554_amcr_successor_corpus_v2_20260816/RUN_OUTCOME.json
  - reports/agent_jobs/issue554_amcr_successor_corpus_v2_20260816/guard_preflight_initial.json
  - reports/agent_jobs/issue554_amcr_successor_corpus_v2_20260816/guard_preflight_final.json
  - reports/agent_jobs/issue554_amcr_successor_corpus_v2_20260816/task_card_validate.json
  - reports/agent_jobs/issue554_amcr_successor_corpus_v2_20260816/task_ledger_validate.json
  - reports/agent_jobs/issue554_amcr_successor_corpus_v2_20260816/task_ledger_search.json
  - reports/agent_jobs/issue554_amcr_successor_corpus_v2_20260816/registry_active_jobs.json
  - reports/agent_jobs/issue554_amcr_successor_corpus_v2_20260816/LEDGER_ENTRY_CLAIMED.json
  - reports/agent_jobs/issue554_amcr_successor_corpus_v2_20260816/LEDGER_ENTRY_IMPLEMENTATION_STARTED.json
  - reports/agent_jobs/issue554_amcr_successor_corpus_v2_20260816/LEDGER_ENTRY_CLOSEOUT.json
  - reports/agent_jobs/issue554_amcr_successor_corpus_v2_20260816/source_admission.json
  - reports/agent_jobs/issue554_amcr_successor_corpus_v2_20260816/corpus_validation.json
  - reports/agent_jobs/issue554_amcr_successor_corpus_v2_20260816/hash_inventory.json
  - reports/agent_jobs/issue554_amcr_successor_corpus_v2_20260816/side_effect_summary.json
  - reports/agent_jobs/issue554_amcr_successor_corpus_v2_20260816/CODE_REVIEW.json
  - reports/agent_jobs/issue554_amcr_successor_corpus_v2_20260816/diff-check.json
  - reports/agent_jobs/issue554_amcr_successor_corpus_v2_20260816/git_status_final.log
docs_impact: DOCS_UPDATED
docs_checked:
  - AGENTS.md
  - docs/extraction/broad_extraction_benchmark_contract.md
docs_changed:
  - docs/agent_tasks/issue554_amcr_successor_corpus_v2_20260816.md
  - financial-engine_v2/data/broad_extraction_benchmark/v2/README.md
docs_followup: "A separately authorized one-shot score must record its exact interpreter preflight and must not overwrite the consumed v1 evidence."
reason: "The user approved selecting and proceeding with one exact official AMCR FY2025 PDF after the v1 corpus stopped source-less."
task_tier: critical
recommended_model: "high reasoning"
actual_model: "GPT-5 Codex"
why_this_model: "The task changes a Financial Truth source identity while preserving frozen corpus and one-shot evaluation boundaries."
worker_model_allowed: false
worker_decision_limit: "No workers or subagents may adjudicate issuer, document, metric, period, value, or evidence identity."
escalation_needed: false
task_scope: issue554_amcr_exact_source_successor_corpus_only
---

# Issue 554 AMCR successor corpus

## Authority

- On 2026-08-16 the user instructed Codex to pick an AMCR document, explicitly
  approved the bounded source-adjudication pass, and then instructed Codex to
  proceed.
- Canonical base is `2bd1033e6e202998be6db82858c75a8119f7ac40` on
  `origin/migration/clean-runtime-baseline-reconstruct-v1`.
- Issue #554 remains open.
- The selected source is the SEC-filed Amcor plc FY2025 Annual Report PDF,
  accession `0001140361-25-035853`, period `2025-06-30`, CIK `0001748790`,
  commission file `001-38932`, SHA-256
  `46601876d376a32caf81512b2dbd66f8a3c86a585736d8c2b9e811957e8bd73c`.

## Objective

Create a new immutable successor snapshot derived byte-for-byte from the
source-adjudicated v1 corpus, changing only AMCR document admission and the
version/provenance metadata required to bind the exact selected PDF. Preserve
all 200 cell identities and every existing expectation state. AMCR's ten cells
remain unresolved because this authority selects a source document; it does
not create or promote gold metric values.

## Hard boundaries

- Do not modify, replace, or reinterpret the frozen v1 corpus, its hashes, its
  reports, or its consumed baseline attempt.
- Do not rerun the v1 baseline or run any v2 extraction, score, repair,
  candidate comparison, or retry.
- Do not change extractor, parser, scorer, adapter, prompt, model, ontology,
  threshold, dependency, runtime, service, queue, DB, Redis, Qdrant, GPU,
  canonical Financial Truth, or production data.
- Do not infer AMCR metric values from the document, extractor output, HTML,
  XBRL, names, filenames, row order, or nearby filings.
- Do not mutate the shared registry or task ledger. Record intended lifecycle
  entries report-locally because `TENN_V2_REQUIRED=1` is not set.
- Do not push, open a PR, merge, deploy, close issue #554, or clean any prior
  worktree.

## Validation and stop states

- Rehash v1 inputs before and after deriving v2.
- Verify the selected PDF bytes, SEC accession, issuer, period, CIK, commission
  file, page count, encryption state, and rendered Form 10-K cover.
- Require exactly 20 distinct issuers, 20 documents, ten metrics, and 200 cells.
- Require 20 admitted source identities and exact source hashes; preserve the
  physical source path for every predecessor document.
- Prove that the only semantic v1-to-v2 change is AMCR admission plus explicit
  successor metadata, with all expectation cells byte-equivalent.
- Stop at `SUCCESSOR_CORPUS_FROZEN`, `DATA_MISSING`, or `EVIDENCE_CONFLICT`.

## Closeout

At `SUCCESSOR_CORPUS_FROZEN`, stop for an owner decision on whether to authorize
one new v2 baseline. A general "proceed" in this source-admission lane is not a
new one-shot scoring authorization.
