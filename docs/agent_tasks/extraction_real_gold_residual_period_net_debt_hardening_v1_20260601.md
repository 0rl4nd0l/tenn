---
job_id: extraction_real_gold_residual_period_net_debt_hardening_v1_20260601
lane: Financial Truth
supporting_lanes:
  - Evaluation
  - Provenance
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_real_gold_residual_period_net_debt_hardening_v1_20260601.md
  - docs/claude/STATE.md
  - financial-engine_v2/backend/app/services/multipass_extraction.py
  - financial-engine_v2/backend/tests/test_multipass_extraction.py
  - reports/agent_jobs/extraction_real_gold_residual_period_net_debt_hardening_v1_20260601/README.md
  - reports/agent_jobs/extraction_real_gold_residual_period_net_debt_hardening_v1_20260601/status.json
  - reports/agent_jobs/extraction_real_gold_residual_period_net_debt_hardening_v1_20260601/validation.json
  - reports/agent_jobs/extraction_real_gold_residual_period_net_debt_hardening_v1_20260601/diff-check.json
  - reports/agent_jobs/extraction_real_gold_residual_period_net_debt_hardening_v1_20260601/preflight.json
  - reports/agent_jobs/extraction_real_gold_residual_period_net_debt_hardening_v1_20260601/source_evidence.json
  - reports/agent_jobs/extraction_real_gold_residual_period_net_debt_hardening_v1_20260601/focused_test_stdout.txt
  - reports/agent_jobs/extraction_real_gold_residual_period_net_debt_hardening_v1_20260601/ruff_stdout.txt
  - reports/agent_jobs/extraction_real_gold_residual_period_net_debt_hardening_v1_20260601/py_compile_stdout.txt
  - reports/agent_jobs/extraction_real_gold_residual_period_net_debt_hardening_v1_20260601/runtime_startup.json
  - reports/agent_jobs/extraction_real_gold_residual_period_net_debt_hardening_v1_20260601/runtime_shutdown.json
  - reports/agent_jobs/extraction_real_gold_residual_period_net_debt_hardening_v1_20260601/queue_before.json
  - reports/agent_jobs/extraction_real_gold_residual_period_net_debt_hardening_v1_20260601/queue_after.json
  - reports/agent_jobs/extraction_real_gold_residual_period_net_debt_hardening_v1_20260601/review_session_inventory_before.json
  - reports/agent_jobs/extraction_real_gold_residual_period_net_debt_hardening_v1_20260601/review_session_inventory_after.json
  - reports/agent_jobs/extraction_real_gold_residual_period_net_debt_hardening_v1_20260601/real_gold_eval_stdout.txt
  - reports/agent_jobs/extraction_real_gold_residual_period_net_debt_hardening_v1_20260601/real_gold_eval_results.json
  - reports/agent_jobs/extraction_real_gold_residual_period_net_debt_hardening_v1_20260601/real_gold_eval_results_summary.json
  - reports/agent_jobs/extraction_real_gold_residual_period_net_debt_hardening_v1_20260601/real_gold_eval_results_canonical_scorecard.json
  - reports/agent_jobs/extraction_real_gold_residual_period_net_debt_hardening_v1_20260601/real_gold_eval_results_documents.csv
  - reports/agent_jobs/extraction_real_gold_residual_period_net_debt_hardening_v1_20260601/real_gold_eval_results_metrics.csv
  - reports/agent_jobs/extraction_real_gold_residual_period_net_debt_hardening_v1_20260601/real_gold_eval_results_trust_triggers.csv
  - reports/agent_jobs/extraction_real_gold_residual_period_net_debt_hardening_v1_20260601/real_gold_eval_summary.md
approval_required: true
timeout_seconds: 14400
output_dir: reports/agent_jobs/extraction_real_gold_residual_period_net_debt_hardening_v1_20260601
mutation_mode: safe_extension
requested_mutation_mode: residual_real_gold_period_and_net_debt_hardening
production_data_access: false
github_mutation_allowed: none
related_issue: 96
operator_approval_source: "User approved full production runtime necessary to complete the extraction goal. This card is bounded to current real-gold residual period-end and net-debt semantics hardening plus optional backend real-gold eval validation."
---

# Extraction Real-Gold Residual Period Net-Debt Hardening V1

## Objective

Fix the current canonical real-gold residual blockers without narrowing the
full extraction objective:

- `14d_q_2021-03-31`: missing `period_end` despite explicit Appendix 4C
  quarter-end source wording.
- `29m_a_2025-12-31`: missing `net_debt` where the source explicitly reports
  a period-end net-debt-equivalent row.
- `a2m_h_2025-12-31`: false non-null `net_debt` caused by derived debt/cash
  logic using non-current-period debt evidence.

This is not a broad ticker-universe backfill and does not by itself prove full
extraction graduation.

## Approved Scope

Approved code edits:

- Harden typed source-period-end detection for explicit Appendix 4C quarter-end
  wording only.
- Harden net-debt explicit row recognition for source-present net-debt-equivalent
  labels without accepting movement, ratio, glossary, or combined equity rows.
- Harden derived `net_debt = total_debt - cash_end` so derivation only uses
  current-period debt evidence.
- Add focused regression tests for the three current residual failure patterns.
- Record source evidence and validation artifacts in this report bundle.
- Update `docs/claude/STATE.md` with bounded status.

Approved optional runtime validation after focused tests pass:

- Start or reload the backend on `:8000` with `DATABASE_URL=sqlite:////data/fe_local.db`.
- Start or reload the llama.cpp router on `:8001` only if health is down and
  GPU/VRAM gates pass.
- Register GPU-exclusive activity for the validation runtime.
- Use the router model-load API for `model:qwen2.5-14b-instruct` if needed.
- Run backend real-gold eval through `POST /api/extraction-eval/real-gold?background=true`
  with canonical settings: dataset `financial-engine_v2/data/extraction_gold_real`,
  parser `docling`, strict mode `true`, limit `0`, tolerance `0.01`.
- Stop dedicated runtime units after validation and record shutdown evidence.

Approved external runtime side effects:

- Backend-owned extraction-review artifacts under `/data/reports/extraction_review`
  if the real-gold eval creates review sessions. Inventory before/after; do not
  delete or rewrite unrelated prior review artifacts.

Not approved:

- `POST /api/process/document/{document_id}`.
- Broad backfill or `/process/ticker`.
- Direct SQL mutation or direct Celery enqueue.
- Source PDF copy, mutation, deletion, or symlink changes.
- Fixture/gold-label changes.
- Parser routing, extraction prompts, schemas/migrations, canonical financial
  rows, Qdrant/news/memory writes, Cockpit UI, or GitHub mutation.

## Session Declaration

Agent: Codex

Branch: `migration/clean-runtime-baseline-reconstruct-v1`

Worktree: `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`

Lane: Financial Truth

Execution mode: SAFE EXTENSION with optional bounded runtime validation.

Intended files: this task card,
`financial-engine_v2/backend/app/services/multipass_extraction.py`,
`financial-engine_v2/backend/tests/test_multipass_extraction.py`,
`docs/claude/STATE.md`, and this report bundle.

Contested surfaces touched: backend extraction period and net-debt semantics.

Collision risk: HIGH because this touches financial-truth extraction behavior.
Proceed only after registry overlap checks and claim succeed.

Decision: proceed after validation, active-job check, overlap check, and claim.

## Contract Check

Target system layers: Extraction, with Evaluation/Provenance for validation
artifacts.

Relevant contract rules: `SYSTEM_CONTRACT.md` §1.1 backend source of truth,
§2 mandatory flow, §3.3 explicit-only metric extraction, §3.5 normalization,
§4 data preservation, §9.4 GPU process topology, §9.5 agent spawn protocol, and
§9.6 shared-router mutual exclusion if runtime eval is run.

What must not change: source PDFs, fixture labels, parser routing, prompts,
schemas/migrations, canonical stored financial rows, Qdrant/news/memory stores,
Cockpit UI, GitHub state, and broad ticker-universe processing.

Why safe: the allowed code changes only accept explicit typed period text and
explicit source metric labels, while making weak or non-current debt evidence
abstain. Any runtime eval uses the backend-owned eval endpoint and report-only
diagnostic artifacts.

GPU process check required: yes only for optional runtime eval; no for code and
unit-test edits.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/extraction_real_gold_residual_period_net_debt_hardening_v1_20260601.md --write-report`
- `python3 scripts/agent_job_registry.py list-active --read-only --repo-root .`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/extraction_real_gold_residual_period_net_debt_hardening_v1_20260601.md --repo-root .`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/extraction_real_gold_residual_period_net_debt_hardening_v1_20260601.md --repo-root .`
- Source-evidence probes for the three residual documents.
- Focused multipass regression tests.
- Targeted Ruff on touched Python files.
- `py_compile` for touched Python files.
- Optional backend real-gold eval if runtime gates pass.
- JSON validation for generated report artifacts.
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/extraction_real_gold_residual_period_net_debt_hardening_v1_20260601.md --repo-root .`
- Registry release and final active-job read-only check.
