---
job_id: approved15_replay_failure_lane_post_pr479_v1_20260701
lane: Financial Truth
supporting_lanes:
  - Evaluation
  - Provenance
  - Reporting
owner: Codex
allowed_files:
  - docs/agent_tasks/approved15_replay_failure_lane_post_pr479_v1_20260701.md
  - financial-engine_v2/backend/app/services/multipass_extraction.py
  - financial-engine_v2/backend/tests/test_multipass_extraction.py
  - reports/agent_jobs/approved15_replay_failure_lane_post_pr479_v1_20260701/TASK_CARD.md
  - reports/agent_jobs/approved15_replay_failure_lane_post_pr479_v1_20260701/README.md
  - reports/agent_jobs/approved15_replay_failure_lane_post_pr479_v1_20260701/STATE.md
  - reports/agent_jobs/approved15_replay_failure_lane_post_pr479_v1_20260701/DECISIONS.md
  - reports/agent_jobs/approved15_replay_failure_lane_post_pr479_v1_20260701/VALIDATION.md
  - reports/agent_jobs/approved15_replay_failure_lane_post_pr479_v1_20260701/NEXT_GOAL.md
  - reports/agent_jobs/approved15_replay_failure_lane_post_pr479_v1_20260701/guard_preflight.json
  - reports/agent_jobs/approved15_replay_failure_lane_post_pr479_v1_20260701/registry_active_jobs.json
  - reports/agent_jobs/approved15_replay_failure_lane_post_pr479_v1_20260701/task_card_validate.json
  - reports/agent_jobs/approved15_replay_failure_lane_post_pr479_v1_20260701/diff-check.json
  - reports/agent_jobs/approved15_replay_failure_lane_post_pr479_v1_20260701/report_artifacts_check.json
  - reports/agent_jobs/approved15_replay_failure_lane_post_pr479_v1_20260701/diff-whitespace.log
  - reports/agent_jobs/approved15_replay_failure_lane_post_pr479_v1_20260701/focused_unit_test.log
  - reports/agent_jobs/approved15_replay_failure_lane_post_pr479_v1_20260701/no_write_replay/input_manifest.json
  - reports/agent_jobs/approved15_replay_failure_lane_post_pr479_v1_20260701/no_write_replay/replay_results.json
  - reports/agent_jobs/approved15_replay_failure_lane_post_pr479_v1_20260701/no_write_replay/side_effect_audit.json
  - reports/agent_jobs/approved15_replay_failure_lane_post_pr479_v1_20260701/no_write_replay/validation.json
  - reports/agent_jobs/approved15_replay_failure_lane_post_pr479_v1_20260701/no_write_replay/logs/replay.log
  - reports/agent_jobs/approved15_replay_failure_lane_post_pr479_v1_20260701/actual_payload_map_anz.json
  - reports/agent_jobs/approved15_replay_failure_lane_post_pr479_v1_20260701/payload_scorecard_anz.json
  - reports/agent_jobs/approved15_replay_failure_lane_post_pr479_v1_20260701/scorecard_gate_anz.json
  - reports/agent_jobs/approved15_replay_failure_lane_post_pr479_v1_20260701/failure_classes_anz.json
  - reports/agent_jobs/approved15_replay_failure_lane_post_pr479_v1_20260701/row_level_failure_matrix_anz.json
  - reports/agent_jobs/approved15_replay_failure_lane_post_pr479_v1_20260701/scorecard_build.log
approval_required: true
timeout_seconds: 21600
output_dir: reports/agent_jobs/approved15_replay_failure_lane_post_pr479_v1_20260701
mutation_mode: safe_extension
production_data_access: false
github_mutation_allowed: false
docs_impact: DOCS_NOT_REQUIRED
docs_checked:
  - AGENTS.md
  - docs/README.md
  - .agents/skills/tenn-fix/SKILL.md
  - .agents/skills/tenn-git-guard/SKILL.md
  - .agents/skills/tenn-financial-metric-extraction/SKILL.md
docs_changed: []
docs_followup: "none"
reason: "Canonical integration of the already-validated ANZ scale magnitude repair from the sibling repair lane. The change is limited to source-bound ANZ bank row/provenance selection and focused tests; no prompt, model, source-PDF, gold-label, data, runtime, service config, DXS, low-confidence policy, GitHub, branch, or merge mutation is allowed."
task_tier: critical
recommended_model: "high reasoning"
actual_model: "Codex GPT-5"
why_this_model: "Financial Truth replay repair needs strict source-bound evidence, guard checks, focused replay, and conservative proof wording."
worker_model_allowed: false
worker_decision_limit: "No workers planned; canonical integration stays in the orchestrator lane."
escalation_needed: false
task_scope: safe_extension
selected_family: ANZ_scale_magnitude_risk
---

# Approved-15 Replay Failure Lane After PR #479

## Objective

Carry the already-validated `ANZ_scale_magnitude_risk` repair from the sibling
worktree into `/home/l4nd0/tenn`, then rerun only the focused ANZ replay and
scorecard needed for that family.

The selected family remains exactly `ANZ_scale_magnitude_risk`. Do not start
DXS mixed-scale work or low-confidence status policy work in this task.

## Scope

- Worktree: `/home/l4nd0/tenn`
- Branch: `local/home-tenn-canonical-current-v4-20260701`
- Starting HEAD: `15450c3c3bcaf0dc9119cbb46820ed68dcd5f449`
- Upstream: `origin/migration/clean-runtime-baseline-reconstruct-v1`
- Prior repair worktree:
  `/home/l4nd0/tenn-approved15-replay-failure-lane-v1-20260701`
- Prior selected family: `ANZ_scale_magnitude_risk`

The repair may adjust only source-bound ANZ bank handling needed for
`ANZ_H_2025-03-31`:

- prefer `Operating income` / `Total operating income` over the bank subline
  `Net interest income` for revenue;
- prefer `Profit before income tax` over pre-impairment profit for EBIT;
- bind `cash_end` to balance-sheet `Cash and cash equivalents` when the
  previous row evidence is weak;
- allow the accepted-output cash/revenue ratio only when bank `cash_end` is
  source-bound to balance-sheet `Cash and cash equivalents`;
- select `Net investments in other assets` as the ANZ capex row;
- reject dollar-denominated ordinary share-capital tables as
  `shares_outstanding` when no share-count evidence exists, allowing prose
  share-count recovery.

## Hard Stops

- No DB, Qdrant, Redis, news, memory, backfill, source-PDF, gold-label,
  prompt, model file, GPU config, count-24, count-32, DXS second extractor,
  service-config, or production-data mutation.
- No broad parser policy, ontology expansion, branch cleanup/deletion, merge,
  rebase, cherry-pick, push, reset, stash, clean, GitHub write, source-PDF
  mutation, or gold-label mutation.
- No DXS second extractor work.
- No low-confidence policy or manifest expectation changes.
- No broad accepted-output gate relaxation.

## Validation

- Repo identity checks and portable Tenn guard preflight.
- Task-card validation and allowed-file diff check.
- Read-only registry inspection.
- Focused backend unit tests for the ANZ bank row/provenance repair.
- Focused no-write replay for `ANZ_H_2025-03-31` only.
- Focused approved-15 scorecard/gate rebuild for ANZ only.
- `git diff --check` and report artifact checks.
