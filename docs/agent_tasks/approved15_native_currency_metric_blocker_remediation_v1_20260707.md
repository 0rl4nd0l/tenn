---
job_id: approved15_native_currency_metric_blocker_remediation_v1_20260707
lane: Financial Truth
supporting_lanes:
  - Evaluation
  - Provenance
  - Reporting
owner: Codex
allowed_files:
  - docs/agent_tasks/approved15_native_currency_metric_blocker_remediation_v1_20260707.md
  - financial-engine_v2/backend/app/services/multipass_extraction.py
  - financial-engine_v2/backend/tests/test_multipass_extraction.py
  - reports/agent_jobs/approved15_native_currency_metric_blocker_remediation_v1_20260707/TASK_CARD.md
  - reports/agent_jobs/approved15_native_currency_metric_blocker_remediation_v1_20260707/README.md
  - reports/agent_jobs/approved15_native_currency_metric_blocker_remediation_v1_20260707/STATE.md
  - reports/agent_jobs/approved15_native_currency_metric_blocker_remediation_v1_20260707/DECISIONS.md
  - reports/agent_jobs/approved15_native_currency_metric_blocker_remediation_v1_20260707/VALIDATION.md
  - reports/agent_jobs/approved15_native_currency_metric_blocker_remediation_v1_20260707/NEXT_GOAL.md
  - reports/agent_jobs/approved15_native_currency_metric_blocker_remediation_v1_20260707/LEDGER_ENTRY.json
  - reports/agent_jobs/approved15_native_currency_metric_blocker_remediation_v1_20260707/guard_preflight.json
  - reports/agent_jobs/approved15_native_currency_metric_blocker_remediation_v1_20260707/registry_active_jobs.json
  - reports/agent_jobs/approved15_native_currency_metric_blocker_remediation_v1_20260707/task_ledger_validate.json
  - reports/agent_jobs/approved15_native_currency_metric_blocker_remediation_v1_20260707/task_card_validate.json
  - reports/agent_jobs/approved15_native_currency_metric_blocker_remediation_v1_20260707/diff-check.json
  - reports/agent_jobs/approved15_native_currency_metric_blocker_remediation_v1_20260707/diff-whitespace.log
  - reports/agent_jobs/approved15_native_currency_metric_blocker_remediation_v1_20260707/focused_unit_test_red.log
  - reports/agent_jobs/approved15_native_currency_metric_blocker_remediation_v1_20260707/focused_unit_test_green.log
  - reports/agent_jobs/approved15_native_currency_metric_blocker_remediation_v1_20260707/source_proof/BHP_CSL_WORKER_RESULT.md
  - reports/agent_jobs/approved15_native_currency_metric_blocker_remediation_v1_20260707/source_proof/FMG_QBE_WORKER_RESULT.md
  - reports/agent_jobs/approved15_native_currency_metric_blocker_remediation_v1_20260707/source_proof/source_proof_summary.json
  - reports/agent_jobs/approved15_native_currency_metric_blocker_remediation_v1_20260707/no_write_replay_red/input_manifest.json
  - reports/agent_jobs/approved15_native_currency_metric_blocker_remediation_v1_20260707/no_write_replay_red/replay_results.json
  - reports/agent_jobs/approved15_native_currency_metric_blocker_remediation_v1_20260707/no_write_replay_red/side_effect_audit.json
  - reports/agent_jobs/approved15_native_currency_metric_blocker_remediation_v1_20260707/no_write_replay_red/validation.json
  - reports/agent_jobs/approved15_native_currency_metric_blocker_remediation_v1_20260707/no_write_replay_red/logs/replay.log
  - reports/agent_jobs/approved15_native_currency_metric_blocker_remediation_v1_20260707/no_write_replay_green/input_manifest.json
  - reports/agent_jobs/approved15_native_currency_metric_blocker_remediation_v1_20260707/no_write_replay_green/replay_results.json
  - reports/agent_jobs/approved15_native_currency_metric_blocker_remediation_v1_20260707/no_write_replay_green/side_effect_audit.json
  - reports/agent_jobs/approved15_native_currency_metric_blocker_remediation_v1_20260707/no_write_replay_green/validation.json
  - reports/agent_jobs/approved15_native_currency_metric_blocker_remediation_v1_20260707/no_write_replay_green/logs/replay.log
  - reports/agent_jobs/approved15_native_currency_metric_blocker_remediation_v1_20260707/actual_payload_map_red.json
  - reports/agent_jobs/approved15_native_currency_metric_blocker_remediation_v1_20260707/payload_scorecard_red.json
  - reports/agent_jobs/approved15_native_currency_metric_blocker_remediation_v1_20260707/scorecard_gate_red.json
  - reports/agent_jobs/approved15_native_currency_metric_blocker_remediation_v1_20260707/failure_classes_red.json
  - reports/agent_jobs/approved15_native_currency_metric_blocker_remediation_v1_20260707/scorecard_build_red.log
  - reports/agent_jobs/approved15_native_currency_metric_blocker_remediation_v1_20260707/actual_payload_map_green.json
  - reports/agent_jobs/approved15_native_currency_metric_blocker_remediation_v1_20260707/payload_scorecard_green.json
  - reports/agent_jobs/approved15_native_currency_metric_blocker_remediation_v1_20260707/scorecard_gate_green.json
  - reports/agent_jobs/approved15_native_currency_metric_blocker_remediation_v1_20260707/failure_classes_green.json
  - reports/agent_jobs/approved15_native_currency_metric_blocker_remediation_v1_20260707/scorecard_build_green.log
  - reports/agent_jobs/approved15_native_currency_metric_blocker_remediation_v1_20260707/handoff/HANDOFF.md
  - reports/agent_jobs/approved15_native_currency_metric_blocker_remediation_v1_20260707/handoff/NEXT_GOAL.md
approval_required: true
allow_unapproved_safe_extension: false
timeout_seconds: 21600
output_dir: reports/agent_jobs/approved15_native_currency_metric_blocker_remediation_v1_20260707
mutation_mode: safe_extension
production_data_access: false
github_mutation_allowed: false
live_ledger_mutation_allowed: false
docs_impact: DOCS_NOT_REQUIRED
docs_checked:
  - AGENTS.md
  - docs/README.md
  - .agents/skills/tenn-fix/SKILL.md
  - .agents/skills/tenn-git-guard/SKILL.md
  - .agents/skills/tenn-financial-metric-extraction/SKILL.md
docs_changed: []
docs_followup: "none"
reason: "Owner approved retargeting the stale approved15 native-currency continuation into a fresh current-canonical task worktree. Scope is limited to the four-case BHP/CSL/FMG/QBE native-currency scorecard blockers and at most one deterministic source-proven metric failure class at a time."
task_tier: critical
recommended_model: "high reasoning"
actual_model: "Codex GPT-5"
why_this_model: "Financial Truth metric remediation requires source-bound value/provenance reasoning, no-write replay discipline, and conservative stop states."
worker_model_allowed: "read-only evidence only"
worker_decision_limit: "Workers may classify source evidence and recommend a failure class; the orchestrator owns all integration and readiness decisions."
escalation_needed: false
task_scope: safe_extension
selected_family: approved15_native_currency_BHP_CSL_FMG_QBE_metric_blockers
base_commit: 94dedc2913d4dbfc1913ca6fae897ca2ce4a0579
source_handoff: /home/l4nd0/tenn-approved15-native-currency-status-policy-v1-20260702/reports/agent_jobs/approved15_low_confidence_status_policy_v1_20260701/handoff/remediation_orchestration_20260707/HANDOFF.md
---

# Approved-15 Native-Currency Metric Blocker Remediation

## Objective

Continue the approved15 native-currency four-case remediation on a fresh
current-canonical worktree:

- `BHP_A_2021-06-30`
- `CSL_H_2025-12-31`
- `FMG_H_2025-12-31`
- `QBE_H_2025-06-30`

The stale handoff reports that those four no-write replay cases reached
`status=ok`, but the focused payload scorecard still failed with
`present_correct=33`, `present_wrong_value=3`, and
`missing_expected_metric=4`.

Freeze this seven-row red set as the only target unless fresh replay evidence
on the same four cases proves a different current red set.

## Starting Evidence

The starting handoff is:

`/home/l4nd0/tenn-approved15-native-currency-status-policy-v1-20260702/reports/agent_jobs/approved15_low_confidence_status_policy_v1_20260701/handoff/remediation_orchestration_20260707/HANDOFF.md`

The reported seven blockers are:

| Fixture | Metric | Scorecard status | Expected | Actual |
| --- | --- | --- | --- | --- |
| `BHP_A_2021-06-30.json` | `np_attributable` | `present_wrong_value` | `11304000000.0` | `3451000000.0` |
| `CSL_H_2025-12-31.json` | `revenue` | `missing_expected_metric` | `8332000000.0` | `null` |
| `CSL_H_2025-12-31.json` | `np_attributable` | `present_wrong_value` | `401000000.0` | `286000000.0` |
| `CSL_H_2025-12-31.json` | `net_debt` | `present_wrong_value` | `9993000000.0` | `9276000000.0` |
| `FMG_H_2025-12-31.json` | `net_debt` | `missing_expected_metric` | `1013000000.0` | `null` |
| `FMG_H_2025-12-31.json` | `shares_outstanding` | `missing_expected_metric` | `3078964918.0` | `null` |
| `QBE_H_2025-06-30.json` | `net_debt` | `missing_expected_metric` | `1555000000.0` | `null` |

## Hard Stops

- No `/home/l4nd0/tenn` dirt mutation.
- No DB, Qdrant, Redis, news, memory, backfill, source-PDF, gold-label,
  prompt, model file, GPU config, service config, Docker volume, runtime
  state, or production-data mutation.
- No DXS, count-24, count-32, broad approved15 replay, metric ontology
  expansion, source/gold/manifest expectation mutation, or broad parser
  rewrite.
- No branch cleanup/deletion, merge, rebase, cherry-pick, push, reset, stash,
  clean, GitHub write, or parked-work mutation.
- Stop with `WAITING_ON_USER` if a fix requires any file outside the allowlist.
- Stop with `DATA_MISSING` if source proof cannot deterministically bind the
  metric value, period, currency, scale, and provenance.

## Allowed Repair Shape

This task permits at most one narrow deterministic code/test change at a time
inside the existing primary `multipass_extraction.py` path when source proof
shows a current failure class is caused by row selection, statement/section
binding, derivation/arithmetic, or an existing extraction coverage gap.

Do not loosen financial-truth validation gates or promote narrative/disclosure
values into canonical metrics without deterministic source-bound evidence.

## Worker Routing

Read-only source-proof workers are allowed only if useful:

- Worker A: BHP `np_attributable` plus CSL `revenue`,
  `np_attributable`, and `net_debt`.
- Worker B: FMG `net_debt`, FMG `shares_outstanding`, and QBE `net_debt`.

Workers must write only their assigned `WORKER_RESULT.md` file under
`source_proof/` and must not mutate code, task cards, source PDFs, gold labels,
runtime/data, GitHub, branches, or report artifacts outside their result file.

## Validation

- Repo identity checks and portable Tenn guard preflight.
- Task-card validation, task-ledger validation, active registry read-only
  inspection, and duplicate-work search.
- Focused red unit test or artifact-backed failure classification before code
  changes where practical.
- Focused unit tests for any changed function/path.
- Four-case no-write replay only for the listed BHP/CSL/FMG/QBE cases using
  `financial-engine_v2/data/extraction_no_write_cases/approved15_current_origin_cases_v1.json`
  and report-local output.
- Focused payload scorecard/gate rebuild from normalized replay payloads.
- `git diff --check`, task-card `check-diff`, report artifact checks, and
  current `git status --short --untracked-files=all`.

## Closeout

Close with a runtime functionality proof table. Use `PARTIAL`,
`DATA_MISSING`, or `WAITING_ON_USER` unless the focused replay and focused
scorecard gate both pass for the four-case target without forbidden side
effects.
