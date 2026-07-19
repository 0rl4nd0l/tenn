---
job_id: news_memo_completion_gate_v1_20260719
lane: Evaluation
supporting_lanes:
  - Extraction
  - Reporting
owner: Codex
approval_required: true
allow_unapproved_safe_extension: false
allow_audit_code_changes: false
timeout_seconds: 10800
output_dir: reports/agent_jobs/news_memo_completion_gate_v1_20260719
mutation_mode: safe_extension
production_data_access: false
allowed_files:
  - docs/agent_tasks/news_memo_completion_gate_v1_20260719.md
  - docs/architecture/09_worker_and_celery_contract.md
  - financial-engine_v2/backend/app/services/news_memo_outcomes.py
  - financial-engine_v2/backend/app/services/news_memo_extractor.py
  - financial-engine_v2/backend/app/tasks/news_tasks.py
  - financial-engine_v2/backend/tests/test_news_memo_extractor.py
  - financial-engine_v2/backend/tests/test_news_tasks.py
  - scripts/load_news_to_qdrant.py
  - scripts/test_load_news_qdrant_preflight.py
  - reports/agent_jobs/news_memo_completion_gate_v1_20260719/TASK_CARD.md
  - reports/agent_jobs/news_memo_completion_gate_v1_20260719/STATE.md
  - reports/agent_jobs/news_memo_completion_gate_v1_20260719/DECISIONS.md
  - reports/agent_jobs/news_memo_completion_gate_v1_20260719/APPROVAL_MANIFEST.md
  - reports/agent_jobs/news_memo_completion_gate_v1_20260719/APPROVAL_MANIFEST.json
  - reports/agent_jobs/news_memo_completion_gate_v1_20260719/EXECUTION_PLAN_FOR_SHOT_2.md
  - reports/agent_jobs/news_memo_completion_gate_v1_20260719/RED_TEST_PLAN.md
  - reports/agent_jobs/news_memo_completion_gate_v1_20260719/WORKER_OUTCOME_DESIGN.md
  - reports/agent_jobs/news_memo_completion_gate_v1_20260719/WORKER_GATE_TDD.md
  - reports/agent_jobs/news_memo_completion_gate_v1_20260719/WORKER_SCOPE_REVIEW.md
  - reports/agent_jobs/news_memo_completion_gate_v1_20260719/DOCS_IMPACT.md
  - reports/agent_jobs/news_memo_completion_gate_v1_20260719/CODE_REVIEW.md
  - reports/agent_jobs/news_memo_completion_gate_v1_20260719/VALIDATION.md
  - reports/agent_jobs/news_memo_completion_gate_v1_20260719/RUNTIME_FUNCTIONALITY_PROOF.md
  - reports/agent_jobs/news_memo_completion_gate_v1_20260719/HANDOFF.md
  - reports/agent_jobs/news_memo_completion_gate_v1_20260719/LEDGER_ENTRY_INTENDED.json
  - reports/agent_jobs/news_memo_completion_gate_v1_20260719/RUN_OUTCOME.json
  - reports/agent_jobs/news_memo_completion_gate_v1_20260719/DECISION_ENTRY.json
  - reports/agent_jobs/news_memo_completion_gate_v1_20260719/status.json
github_writes_allowed: []
closeout_scope: code_only
control_contract_version: 2
project_id: tenn
claim_id: durable_news_memo_completion_and_substantive_gate
proof_question: Can each accepted news-memo task be reconciled to a durable source-bound terminal attempt outcome while low-information output remains retryable and is never persisted as a completed memo?
hypothesis_id: per_source_attempt_ledger_and_grounded_content_gate_v1
program_track: offline_development
entry_state: async_dispatch_is_not_source_bound_to_terminal_attempts_and_low_information_rows_can_become_terminal_memos
target_transition: durable_attempt_reconciliation_and_non_substantive_output_remains_retryable
exit_predicate: Focused tests prove accepted, completed, needs-retry, failed, and dispatch-failed attempt evidence is durable and source-bound; ticker/sentiment/impact-only output is not persisted or signal-routed; candidate, prompt, model, skip-ledger, and runtime behavior outside this contract remain unchanged.
source_class: july19_news_memo_quality_audit_and_canonical_news_memo_source
dataset_version: july19_news_memo_quality_audit_canonical_301a5590
evidence_hash: sha256:296c0e55d0d8e88d13ec5fbc2f45c4200e57541c02ba824a58c9cc8c7d260472
capabilities:
  - READ
  - REPORT_WRITE
  - CODE_EDIT
resume_only_if: Orlando replies `APPROVE SHOT 2 GROUPS A+B+C+D FOR sha256:ed045409a14d347607caeaafb5a8f7173c49fba6dccff206220dd2d125772906`, or canonical source or July 19 audit evidence changes and Shot 1 is rerun.
---

# Durable News Memo Completion Outcomes And Substantive Gate

## Objective

Implement only the two July 19 quality-audit priorities:

1. durable per-source dispatch and terminal-attempt outcomes with later
   reconciliation; and
2. a substantive-output gate that prevents low-information output from being
   persisted as a completed memo.

## Approved Behavior

- Derive `news_memo_outcomes.jsonl` beside the configured memo JSONL; do not add
  a new runtime setting.
- Give each dispatch attempt a correlation ID and persist source ID, Celery task
  ID when available, broker-acceptance state/time, terminal attempt state,
  reason or error class, and completion time.
- Merge concurrent lifecycle updates under an inter-process sidecar lock and
  atomically replace the outcome JSONL.
- Reconcile the latest attempt per candidate source as accepted-pending,
  completed, needs-retry, failed, or dispatch-failed without using attempt
  outcomes as candidate-suppression state.
- Treat an extracted memo as substantive only when at least one normalized
  `key_event`, `claim`, or `risk` is present.
- Treat ticker, sentiment, and impact-magnitude alone as non-substantive.
- Return `needs_retry` for non-substantive output, persist no memo, route no
  signals, and record a durable terminal attempt outcome.
- Preserve the existing memo and terminal-skip files and their coverage meaning.

## Hard Boundaries

- No backfill, re-extraction, production run, worker invocation, broker call,
  service start/restart, or live memo/outcome/data write.
- No candidate-predicate, prompt, model, article-character-cap, ticker,
  provenance, Qdrant, Redis, SQLite, DB, source-PDF, or gold-label change.
- No new terminal skip for non-substantive output; it must remain eligible for a
  later normal retry because no memo or terminal skip exists.
- No commit, push, PR, merge, rebase, reset, stash, branch cleanup, standalone
  ledger append, or GitHub write.
- No registry mutation in Shot 1. Shot 2 may claim and release only this exact
  V2 card; release may append only its validated decision entry as required by
  the V2 contract. No other registry or ledger state is authorized.
- Product edits are forbidden in Shot 1. Shot 2 begins only after the owner
  approves all exact manifest groups against the manifest SHA-256.

## Test-First Contract

- Add one failing public-behavior test at a time.
- Run each new test and record the expected RED failure before implementation.
- Implement only enough production behavior to make that slice GREEN.
- Keep all persistence tests under temporary directories; never point tests at
  the live research-memory root.
- Run focused regressions only after all vertical slices are green.

## Validation

- task-card validation and portable guard with this card
- recorded RED then GREEN tests for each vertical slice
- focused extractor, task, and loader regression suites
- candidate-predicate regression assertions showing unchanged classification
- `git diff --check`
- task-card `check-diff` and final code review
- final clean-room proof must remain offline; live functionality is
  `DATA_MISSING` until separately authorized runtime evidence exists

## Definition Of Done

- The exact outcome schema and reconciliation classifications are test-proven.
- Every normal accepted task can be joined by source, correlation ID, and task
  ID to its durable terminal attempt when the worker completes.
- A rank-8-shaped memo containing only ticker, sentiment, and impact is rejected
  before memo persistence and signal routing and remains retryable.
- Existing candidate predicates, prompts, models, and terminal skip semantics
  are byte-identical.
- No runtime or production data was touched.
- Offline focused validation and skeptical code review pass; the result is not
  called runtime-working without a separate Runtime Functionality Proof.
