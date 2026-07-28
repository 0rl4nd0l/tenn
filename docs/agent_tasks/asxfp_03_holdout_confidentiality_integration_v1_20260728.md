---
job_id: asxfp_03_holdout_confidentiality_integration_v1_20260728
title: Enforce aggregate-only Ticket 03 holdout outputs across development surfaces
lane: Evaluation
supporting_lanes:
  - Financial Truth
  - Provenance
owner: Codex
approval_required: false
allow_unapproved_safe_extension: true
allow_audit_code_changes: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/asxfp_03_holdout_confidentiality_integration_v1_20260728
mutation_mode: safe_extension
production_data_access: false
github_mutation_allowed: true
allowed_files:
  - docs/agent_tasks/asxfp_03_holdout_confidentiality_integration_v1_20260728.md
  - cockpit-ui/components/cockpit/verification/verification-screen.tsx
  - cockpit-ui/tests/verification.spec.ts
  - financial-engine_v2/backend/app/services/asx_holdout_confidentiality.py
  - financial-engine_v2/backend/app/services/extraction_eval.py
  - financial-engine_v2/backend/app/services/extraction_gold_eval.py
  - financial-engine_v2/backend/app/main.py
  - financial-engine_v2/scripts/extraction_gold_eval_scorecard.py
  - financial-engine_v2/scripts/run_prompt_model_matrix.py
  - scripts/extraction_gold_eval_scorecard.py
  - scripts/run_real_extraction_eval.py
  - scripts/analyze_real_extraction_eval_duckdb.py
  - scripts/run_real_extraction_eval_mlflow.py
  - financial-engine_v2/backend/tests/test_asx_holdout_confidentiality.py
  - financial-engine_v2/backend/tests/test_extraction_eval.py
  - financial-engine_v2/backend/tests/test_extraction_eval_harness.py
  - financial-engine_v2/backend/tests/test_extraction_gold_eval.py
  - financial-engine_v2/backend/tests/test_prompt_model_matrix.py
  - scripts/test_extraction_gold_eval_scorecard.py
  - scripts/test_run_real_extraction_eval.py
  - scripts/test_analyze_real_extraction_eval_duckdb.py
  - scripts/test_run_real_extraction_eval_mlflow.py
  - reports/agent_jobs/asxfp_03_holdout_confidentiality_integration_v1_20260728/README.md
  - reports/agent_jobs/asxfp_03_holdout_confidentiality_integration_v1_20260728/VALIDATION.md
docs_impact: DOCS_UPDATED
docs_checked:
  - AGENTS.md
  - docs/README.md
  - docs/agent_tasks/asxfp_03_holdout_confidentiality_integration_v1_20260728.md
docs_changed:
  - docs/agent_tasks/asxfp_03_holdout_confidentiality_integration_v1_20260728.md
docs_followup: NONE
reason: "The confidentiality integration changes the Real-Gold request schema. This task card now documents the required explicit non-holdout development request from Cockpit and its regression gate."
task_tier: medium
recommended_model: "Codex X implementation worker"
actual_model: "Codex GPT-5.6"
why_this_model: "The repair is cross-surface but bounded by the reviewed product/test allowlist expanded by exactly two Cockpit caller-regression paths."
worker_model_allowed: true
worker_decision_limit: "Implementation is limited to the explicit confidentiality contract and exact allowed files. The existing draft PR #527 may be updated; no corpus, runtime, merge, or other GitHub action."
escalation_needed: false
---

# ASXFP Ticket 03 Holdout Confidentiality Integration

## Objective

Make the existing Ticket 03 aggregate-only confidentiality contract authoritative
for every development/public extraction-evaluation output path.

## Evidence

Codex X audit run `20260728T030258Z-b45a9b5dd7-3367cb` at exact source HEAD
`b45a9b5dd7446778a33caa1d241282ed5d578a6c` and tree
`3cadc78d824f8a4a1591628d43c6460fb00912ba` returned
`INTEGRATION_GAP_WITH_NARROW_ALLOWLIST`.

The audit proved:

- `DevelopmentAggregateResult` is only consumed by `asx_release_corpus.py`.
- Evaluators still return per-document `fixture_summaries`.
- API sync, background progress, and polling responses expose document details.
- CLI/stdout, JSON, CSV, Markdown, prompt-matrix, DuckDB analysis, and MLflow
  artifact surfaces serialize identifying per-document details.

## Required contract

- Every evaluator result carries an explicit corpus classification and access
  mode.
- Any development/public result involving holdout data must pass a fail-closed
  serializer that emits exactly `DevelopmentAggregateResult.ALLOWED_FIELDS`.
- The aggregate-only rule applies recursively to sync responses, background
  results and progress, stdout, JSON, CSV, Markdown, matrix reports, analysis
  reports, and uploaded artifact payloads.
- Development/public outputs must omit document IDs, tickers, paths, filenames,
  expected/actual values, per-document metrics, errors, triggers, provenance,
  and identifying manifests.
- Detailed output requires explicit `ProtectedAccessMode.PROTECTED`.
- Unknown or omitted access modes fail closed whenever holdout classification is
  present.
- Non-holdout legacy behavior remains compatible unless the same explicit
  confidentiality contract applies.

## Allowed work

- Add one reusable fail-closed result/output policy to
  `asx_holdout_confidentiality.py`.
- Thread explicit corpus classification and access mode through the allowed
  evaluator/API/CLI surfaces.
- Keep the Cockpit Real-Gold caller compatible by explicitly declaring
  `non_holdout` classification and `development` access.
- Serialize aggregate-only development/public holdout outputs at every allowed
  sink.
- Add synthetic tests proving all public/development formats omit identifying
  details and protected mode retains the existing detailed behavior.

## Forbidden work

- No source PDF, gold-label, manifest, baseline, protected review-record, or
  production-data access or mutation.
- No extraction, OCR/model, prompt/model configuration, service, runtime,
  database, queue, Qdrant, GPU, backfill, or deployment action.
- No GitHub issue mutation, merge, activation, or branch deletion. Owner
  approval permits a normal push updating only existing draft PR #527.
- No ontology expansion, metric-definition change, score-threshold change, or
  broad evaluator redesign.
- No file outside `allowed_files`.

## Required validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/asxfp_03_holdout_confidentiality_integration_v1_20260728.md`
- Focused synthetic/unit tests for every changed evaluator/API/CLI output path.
- Cockpit Playwright regression proving the Real-Gold POST body declares
  `corpus_classification=non_holdout` and `access_mode=development`.
- Existing Ticket 02 and Ticket 03 corpus contract tests.
- Changed-file Ruff check and format check.
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/asxfp_03_holdout_confidentiality_integration_v1_20260728.md --repo-root .`

## Done criteria

- Development/public holdout output cannot expose per-document details through
  any allowed evaluator, API, progress, CLI, file-format, matrix, analysis, or
  MLflow path.
- Detailed holdout output is reachable only through explicit protected mode.
- Unknown or omitted holdout access mode fails closed.
- Non-holdout compatibility tests remain green.
- Cockpit's Real-Gold request satisfies the explicit confidentiality schema.
- Diff is confined to `allowed_files`.
- Independent exact-head Codex X review accepts the integration checkpoint.
- Protected corpus availability remains separately `DATA_MISSING`; this task
  does not claim actual 48-document corpus completion.
