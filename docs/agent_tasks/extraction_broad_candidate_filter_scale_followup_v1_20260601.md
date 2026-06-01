---
job_id: extraction_broad_candidate_filter_scale_followup_v1_20260601
lane: Financial Truth
supporting_lanes:
  - Evaluation
  - Provenance
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_broad_candidate_filter_scale_followup_v1_20260601.md
  - docs/claude/STATE.md
  - financial-engine_v2/backend/app/services/multipass_extraction.py
  - financial-engine_v2/backend/tests/test_multipass_extraction.py
  - financial-engine_v2/scripts/test_broad_extraction_test.py
  - reports/agent_jobs/extraction_broad_candidate_filter_scale_followup_v1_20260601/README.md
  - reports/agent_jobs/extraction_broad_candidate_filter_scale_followup_v1_20260601/status.json
  - reports/agent_jobs/extraction_broad_candidate_filter_scale_followup_v1_20260601/validation.json
  - reports/agent_jobs/extraction_broad_candidate_filter_scale_followup_v1_20260601/diff-check.json
approval_required: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/extraction_broad_candidate_filter_scale_followup_v1_20260601
mutation_mode: safe_extension
production_data_access: false
github_mutation_allowed: none
operator_approval_source: "Continuation of full extraction hardening goal after post-hardening broad sample a2ec9449 exposed narrower non-runtime blockers."
---

# Extraction Broad Candidate Filter And Scale Followup V1

## Objective

Harden the next broad-sample blockers from
`extraction_broad_robustness_post_hardening_sample_v1_20260601` without running
runtime extraction or mutating data:

1. Exclude AGM/proxy meeting notices before broad candidate sampling and metric
   extraction.
2. Exclude non-financial customer/contract/revenue-update announcements that
   lack formal Appendix/statement evidence.
3. Recognize explicit Appendix 4C cash-flow units such as `$USD'000` or
   `$USD’000` as `scale=thousands`.

This is a bounded source-document and source-unit hardening slice. It is not a
gold accuracy run, runtime canary, broad backfill, or full extraction
graduation.

## Session Declaration

Agent: Codex

Branch: `migration/clean-runtime-baseline-reconstruct-v1`

Worktree: `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`

Lane: Financial Truth

Execution mode: SAFE EXTENSION MODE

Intended files: this task card, `docs/claude/STATE.md`, multipass extraction
service, focused multipass/broad-helper tests, and this report bundle.

Contested surfaces touched: none from AGENTS.md.

Collision risk: MEDIUM/HIGH by financial-truth semantics; resolved by exact
allowlist, deterministic source classification, no runtime/data-store
mutation, and focused tests.

Decision: proceed after validation, active-job check, overlap check, and
registry claim.

## Contract Check

Target system layers: Extraction and Evaluation.

Relevant contract rules: backend remains the sole authority; metric extraction
may only use explicit source values; normalization may convert explicit source
units but must not infer or fabricate; source PDFs and stores are read-only in
this task.

What must not change: parser prompts, schema/migrations, backend routes,
canary/process-document runtime, direct datastore contents, source PDFs, Qdrant,
news/memory stores, Cockpit UI, GitHub state, and broad backfill authorization.

Why safe: the classifier only blocks source-document classes that are not
formal financial reports or Appendix cash-flow reports, and the scale rule
uses explicit `$<currency>'000` source-unit text already present in the source
header. Validation gates remain fail-closed.

GPU process check required: no. This task must not spawn, restart, or depend on
llama-server.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/extraction_broad_candidate_filter_scale_followup_v1_20260601.md --write-report`
- `python3 scripts/agent_job_registry.py list-active --read-only`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/extraction_broad_candidate_filter_scale_followup_v1_20260601.md --repo-root .`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/extraction_broad_candidate_filter_scale_followup_v1_20260601.md --repo-root .`
- Focused multipass and broad-helper tests for the new classifiers and scale rule.
- Relevant touched test files.
- Targeted Ruff and `py_compile`.
- `git diff --check` and `git diff --cached --check`.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/extraction_broad_candidate_filter_scale_followup_v1_20260601.md --repo-root .`
- Registry release after commit.
