---
job_id: extraction_gpt_appendix4d_payload_construction_repair_v1_20260604
lane: Financial Truth
supporting_lanes:
  - Evaluation
  - Provenance
  - Query Orchestration
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_gpt_appendix4d_payload_construction_repair_v1_20260604.md
  - reports/agent_jobs/extraction_gpt_appendix4d_payload_construction_repair_v1_20260604/README.md
  - reports/agent_jobs/extraction_gpt_appendix4d_payload_construction_repair_v1_20260604/status.json
  - reports/agent_jobs/extraction_gpt_appendix4d_payload_construction_repair_v1_20260604/targeted_result.json
  - reports/agent_jobs/extraction_gpt_appendix4d_payload_construction_repair_v1_20260604/validation.json
  - reports/agent_jobs/extraction_gpt_appendix4d_payload_construction_repair_v1_20260604/diff-check.json
  - financial-engine_v2/backend/app/services/multipass_extraction.py
  - financial-engine_v2/backend/tests/test_multipass_extraction.py
  - financial-engine_v2/backend/tests/test_extraction_capability_guards.py
  - financial-engine_v2/backend/tests/test_extraction_gold_eval_scorecard.py
  - docs/extraction/metric_extraction_contract.md
  - docs/architecture/12_evaluation_and_drift_monitoring.md
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/extraction_gpt_appendix4d_payload_construction_repair_v1_20260604
mutation_mode: safe_extension
production_data_access: false
---

# GPT Appendix 4D Payload Construction Repair

## Objective

Audit and, only if a narrow source-bound extension is sufficient, repair full
multipass payload construction for the exact GPT Appendix 4D target after PR
#294.

Target PDF:
`/data/asx/docs/GPT/financial_performance/2024-08-19_appendix-4d-gpt-management-holdings-limited_c10a88ab-4290-4395-9521-7f96c50b03c4.pdf`

Expected source-bound gate payload:

- `period_type=H`
- `period_end=2024-06-30`
- `scale=thousands`
- `currency=AUD`
- `revenue=150804000`
- `np_attributable=15463000`
- Appendix 4D wrapper disclosure evidence present

## Lane

Primary lane: Financial Truth.

Supporting lanes: Evaluation, Provenance, and Query Orchestration.

## Execution Mode

AUDIT FIRST. SAFE EXTENSION only if the fix is narrow, source-bound, tested, and
limited to Appendix 4D/4E wrapper payload construction.

Risk: MEDIUM/HIGH because this changes financial extraction payload assembly.

## Preflight

- Confirm repo path, branch, HEAD, and remote.
- Confirm canonical includes PR #294 merge commit
  `2f9a2607630c93f828baab8a63cedc068a485585` or a descendant.
- Run `git status --short --untracked-files=all`.
- Run `git worktree list`.
- Check registry/list-active.
- Use an isolated worktree if unrelated dirt exists.
- Validate this task card and claim the registry before implementation.
- Confirm the target PDF exists.
- Read prior artifacts for the targeted and end-to-end Appendix 4D PR #294
  checks and the wrapper gate current-origin rebuild where present.

## Audit Questions

- Why does full multipass set `period_type=Q` instead of `H`?
- Why is `period_end` null despite source evidence?
- Why is revenue missing?
- Why is `np_attributable` `15462000` instead of `15463000`?
- Why are wrapper disclosure fields absent?
- Which stage loses the source-bound Appendix 4D evidence: source classifier,
  source period detector, table locator, metric extractor, pass4 reconciler, or
  validation payload assembly?
- Does the full multipass path see the Appendix 4D title/wrapper evidence but
  fail to propagate it?
- Is the problem specific to GPT Appendix 4D or a generic Appendix 4D/4E wrapper
  payload construction issue?

## Safe Extension Rules

- Carry source-bound evidence forward rather than infer missing fields.
- Do not loosen general validation gates.
- Do not promote NTA, dividends, record date, associates, or other disclosure
  rows to canonical metrics.
- Do not alter ordinary annual or half-year report behavior.
- Fail closed if source-bound period, scale, currency, or wrapper evidence is
  missing.

## Hard Stops

- Do not run random samples, count-16/count-24 samples, broad extraction,
  backfill, canaries, or production DB writes.
- Do not mutate Qdrant, news, memory stores, source PDFs, prompts, gold labels,
  runtime/model/GPU config, service processes, or schemas.
- Do not perform unrelated cleanup, stash, reset, delete, merge, rebase, or
  broad validation outside this task.
- Stop if a necessary implementation file is outside `allowed_files`.

## Required Tests

- GPT-style Appendix 4D payload construction carries `period_type=H`,
  `period_end=2024-06-30`, `scale=thousands`, `currency=AUD`, revenue,
  `np_attributable`, and wrapper disclosure evidence.
- NTA, dividends, and record date remain disclosure-only.
- Ordinary annual and half-year reports still use the normal metric minimum.
- Wrapper documents fail closed if period, scale, currency, or wrapper
  disclosure evidence is missing.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/extraction_gpt_appendix4d_payload_construction_repair_v1_20260604.md`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/extraction_gpt_appendix4d_payload_construction_repair_v1_20260604.md --repo-root .`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/extraction_gpt_appendix4d_payload_construction_repair_v1_20260604.md --repo-root .`
- Focused pytest for touched extraction tests.
- `python3 -m py_compile financial-engine_v2/backend/app/services/multipass_extraction.py`
- Ruff on touched Python files if available.
- Targeted GPT Appendix 4D verification only, using the safest available full
  multipass or report-local multipass-equivalent path.
- JSON validation for report artifacts.
- `git diff --check`.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/extraction_gpt_appendix4d_payload_construction_repair_v1_20260604.md --repo-root .`
- No source PDFs staged.
- Registry release and final `list-active`.
- Final git status.

## Final Report

Write `reports/agent_jobs/extraction_gpt_appendix4d_payload_construction_repair_v1_20260604/README.md`,
`status.json`, `validation.json`, and `targeted_result.json` if targeted
verification runs.

The final report must include root cause, fix made if any, before/after payload
comparison, targeted GPT final status, canonical metrics, wrapper disclosure
evidence, period/scale/currency proof, validation commands and results, whether
a count-16 bounded rerun is now justified, remaining `DATA_MISSING`, and an
explicit statement that no broad extraction/backfill/sample was run.
