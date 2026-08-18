---
job_id: issue97_wow_unicode_dash_heading_retarget_v1_20260711
lane: Financial Truth
supporting_lanes:
  - Evaluation
  - Provenance
  - Reporting
  - Repo Hygiene
owner: Codex
allowed_files:
  - docs/agent_tasks/issue97_wow_unicode_dash_heading_retarget_v1_20260711.md
  - financial-engine_v2/backend/app/services/multipass_extraction.py
  - financial-engine_v2/backend/tests/test_multipass_extraction.py
  - reports/agent_jobs/issue97_wow_unicode_dash_heading_retarget_v1_20260711/README.md
  - reports/agent_jobs/issue97_wow_unicode_dash_heading_retarget_v1_20260711/STATE.md
  - reports/agent_jobs/issue97_wow_unicode_dash_heading_retarget_v1_20260711/DECISIONS.md
  - reports/agent_jobs/issue97_wow_unicode_dash_heading_retarget_v1_20260711/VALIDATION.md
  - reports/agent_jobs/issue97_wow_unicode_dash_heading_retarget_v1_20260711/NEXT_GOAL.md
  - reports/agent_jobs/issue97_wow_unicode_dash_heading_retarget_v1_20260711/PR_REVIEW.md
  - reports/agent_jobs/issue97_wow_unicode_dash_heading_retarget_v1_20260711/PR_BODY.md
  - reports/agent_jobs/issue97_wow_unicode_dash_heading_retarget_v1_20260711/BOARD.md
  - reports/agent_jobs/issue97_wow_unicode_dash_heading_retarget_v1_20260711/BOARD_DECISION.json
  - reports/agent_jobs/issue97_wow_unicode_dash_heading_retarget_v1_20260711/architecture_review.md
  - reports/agent_jobs/issue97_wow_unicode_dash_heading_retarget_v1_20260711/code_review.json
  - reports/agent_jobs/issue97_wow_unicode_dash_heading_retarget_v1_20260711/preserved_worktrees_before.txt
  - reports/agent_jobs/issue97_wow_unicode_dash_heading_retarget_v1_20260711/preserved_worktrees_after.txt
  - reports/agent_jobs/issue97_wow_unicode_dash_heading_retarget_v1_20260711/task_card_validate.json
  - reports/agent_jobs/issue97_wow_unicode_dash_heading_retarget_v1_20260711/diff-check.json
  - reports/agent_jobs/issue97_wow_unicode_dash_heading_retarget_v1_20260711/report_artifacts_check.json
  - reports/agent_jobs/issue97_wow_unicode_dash_heading_retarget_v1_20260711/closeout_check.json
  - reports/agent_jobs/issue97_wow_unicode_dash_heading_retarget_v1_20260711/focused_unit_red.log
  - reports/agent_jobs/issue97_wow_unicode_dash_heading_retarget_v1_20260711/focused_unit_green.log
  - reports/agent_jobs/issue97_wow_unicode_dash_heading_retarget_v1_20260711/focused_unit_regression.log
  - reports/agent_jobs/issue97_wow_unicode_dash_heading_retarget_v1_20260711/ruff.log
  - reports/agent_jobs/issue97_wow_unicode_dash_heading_retarget_v1_20260711/diff-whitespace.log
  - reports/agent_jobs/issue97_wow_unicode_dash_heading_retarget_v1_20260711/focused_replay_green/input_manifest.json
  - reports/agent_jobs/issue97_wow_unicode_dash_heading_retarget_v1_20260711/focused_replay_green/replay_results.json
  - reports/agent_jobs/issue97_wow_unicode_dash_heading_retarget_v1_20260711/focused_replay_green/side_effect_audit.json
  - reports/agent_jobs/issue97_wow_unicode_dash_heading_retarget_v1_20260711/focused_replay_green/validation.json
  - reports/agent_jobs/issue97_wow_unicode_dash_heading_retarget_v1_20260711/focused_replay_green/logs/replay.log
  - reports/agent_jobs/issue97_wow_unicode_dash_heading_retarget_v1_20260711/full_replay_green/input_manifest.json
  - reports/agent_jobs/issue97_wow_unicode_dash_heading_retarget_v1_20260711/full_replay_green/replay_results.json
  - reports/agent_jobs/issue97_wow_unicode_dash_heading_retarget_v1_20260711/full_replay_green/side_effect_audit.json
  - reports/agent_jobs/issue97_wow_unicode_dash_heading_retarget_v1_20260711/full_replay_green/validation.json
  - reports/agent_jobs/issue97_wow_unicode_dash_heading_retarget_v1_20260711/full_replay_green/logs/replay.log
  - reports/agent_jobs/issue97_wow_unicode_dash_heading_retarget_v1_20260711/scripts/build_scorecard.py
  - reports/agent_jobs/issue97_wow_unicode_dash_heading_retarget_v1_20260711/actual_payload_map_green.json
  - reports/agent_jobs/issue97_wow_unicode_dash_heading_retarget_v1_20260711/payload_scorecard_green.json
  - reports/agent_jobs/issue97_wow_unicode_dash_heading_retarget_v1_20260711/scorecard_gate_green.json
  - reports/agent_jobs/issue97_wow_unicode_dash_heading_retarget_v1_20260711/failure_class_summary_green.json
  - reports/agent_jobs/issue97_wow_unicode_dash_heading_retarget_v1_20260711/row_level_failure_matrix_green.json
  - reports/agent_jobs/issue97_wow_unicode_dash_heading_retarget_v1_20260711/scorecard_build_green.log
  - reports/agent_jobs/issue97_wow_unicode_dash_heading_retarget_v1_20260711/final_guard_preflight.json
  - reports/agent_jobs/issue97_wow_unicode_dash_heading_retarget_v1_20260711/PR_OPENED.json
approval_required: true
approval_context: "USER_APPROVED_2026-07-11: preserve and retarget exactly the validated WOW grouped-balance-sheet Unicode-dash heading family from canonical merge 174844e6; validate, commit only task-card/source/test, push, and open a draft PR; do not merge."
timeout_seconds: 21600
output_dir: reports/agent_jobs/issue97_wow_unicode_dash_heading_retarget_v1_20260711
mutation_mode: safe_extension
production_data_access: false
github_mutation_allowed: true
live_ledger_mutation_allowed: false
docs_impact: DOCS_NOT_REQUIRED
docs_checked:
  - AGENTS.md
  - docs/README.md
  - docs/architecture/SYSTEM_CONTRACT.md
  - .agents/skills/tenn-fix/SKILL.md
  - .agents/skills/tenn-git-guard/SKILL.md
  - .agents/skills/tenn-financial-metric-extraction/SKILL.md
docs_changed: []
docs_followup: "none"
reason: "Retarget one already validated parser-alignment family without changing operator commands, schema, API, runtime topology, or architecture boundaries."
task_tier: critical
recommended_model: "high reasoning"
actual_model: "Codex GPT-5"
why_this_model: "Financial Truth row alignment, current-only scorecard interpretation, preserved dirty worktrees, and GitHub publication require strict source and scope judgment."
worker_model_allowed: false
worker_decision_limit: "No workers; the two-file delta is coupled and all financial-truth and publication decisions remain serialized in the primary lane."
escalation_needed: false
task_scope: safe_extension
selected_issue: 97
deferred_issue: 96
base_ref: origin/migration/clean-runtime-baseline-reconstruct-v1
base_head: 174844e6fca6e843feabbbe2214ed6efc9af6156
---

# Issue #97 WOW Unicode-Dash Heading Retarget

## Objective

Retarget exactly the validated WOW grouped-balance-sheet Unicode-dash heading
alignment family from the preserved WOW worktree onto canonical merge commit
`174844e6fca6e843feabbbe2214ed6efc9af6156`. Preserve the PR #501
financial/non-financial-asset boundary fix already present in the base.

## Exact Source And Delta

- Read-only WOW source:
  `/home/l4nd0/tenn-issue97-wow-net-debt-current-canonical-v1-20260710`
- Read-only pre-WOW comparison:
  `/home/l4nd0/tenn-issue97-bank-cashflow-capex-source-selection-v1-20260709`
- Port only:
  - Unicode dash normalization in `_is_balance_sheet_group_heading`.
  - The exact 93-line grouped-debt regressions.
- Commit only this task card and the two source/test files.

## Required Sequence

1. Tenn Git guard, task-card validation, registry/ledger read-only checks.
2. Add the 93-line regression delta and capture RED on the exact Unicode test.
3. Add only the 3-insertion/1-deletion source delta and capture GREEN.
4. Run affected regression selection, Ruff, and `git diff --check`.
5. Run focused WOW and full approved15 no-write replay.
6. Build the scorecard from current replay payloads only.
7. Review the diff and scope, commit only approved files, push, and open a
   draft PR against `migration/clean-runtime-baseline-reconstruct-v1`.

## Hard Stops

- Preserve `/home/l4nd0/tenn` and all three named Issue #97 worktrees unchanged.
- No WOW NPAT, AZJ, SEG, TLS, missing-evidence, or ANZ magnitude-gate repair.
- No source PDF, gold label, extraction prompt, manifest, accepted-output gate,
  DB, Qdrant, Redis, news, memory, runtime/data store, service, registry,
  model/GPU, dependency, cleanup, or unrelated branch-history mutation.
- Do not merge the draft PR.
- Stop if the exact PR #501 boundary fix is absent from the base, the 93-line
  test delta does not fail before the source change, or the current-only replay
  evidence shows a target-family regression.

## Done Criteria

- Exact base and PR #501 ancestry are verified.
- RED proves Unicode U+2011 shifts the grouped non-current debt value before
  normalization; GREEN recovers total debt `5686000000` while excluding leases
  and avoiding total double-counting.
- Focused WOW replay returns net debt `4397000000` from
  `total_debt(5686000000)-cash_end(1289000000)` with clean side effects.
- Full approved15 replay and current-payload-only scorecard complete; inherited
  non-target blockers remain explicitly out of scope.
- The three-file commit is pushed and a draft PR is open and unmerged.
