---
job_id: issue97_anz_bank_capex_publication_v1_20260710
lane: Financial Truth
supporting_lanes:
  - Evaluation
  - Provenance
  - Reporting
  - Repo Hygiene
owner: Codex
allowed_files:
  - docs/agent_tasks/issue97_anz_bank_capex_publication_v1_20260710.md
  - financial-engine_v2/backend/app/services/multipass_extraction.py
  - financial-engine_v2/backend/tests/test_multipass_extraction.py
  - reports/agent_jobs/issue97_anz_bank_capex_publication_v1_20260710/TASK_CARD.md
  - reports/agent_jobs/issue97_anz_bank_capex_publication_v1_20260710/README.md
  - reports/agent_jobs/issue97_anz_bank_capex_publication_v1_20260710/STATE.md
  - reports/agent_jobs/issue97_anz_bank_capex_publication_v1_20260710/DECISIONS.md
  - reports/agent_jobs/issue97_anz_bank_capex_publication_v1_20260710/VALIDATION.md
  - reports/agent_jobs/issue97_anz_bank_capex_publication_v1_20260710/NEXT_GOAL.md
  - reports/agent_jobs/issue97_anz_bank_capex_publication_v1_20260710/PR_REVIEW.md
  - reports/agent_jobs/issue97_anz_bank_capex_publication_v1_20260710/PR_BODY.md
  - reports/agent_jobs/issue97_anz_bank_capex_publication_v1_20260710/baseline_identity.json
  - reports/agent_jobs/issue97_anz_bank_capex_publication_v1_20260710/code_fixer.json
  - reports/agent_jobs/issue97_anz_bank_capex_publication_v1_20260710/code_review.json
  - reports/agent_jobs/issue97_anz_bank_capex_publication_v1_20260710/task_card_validate.json
  - reports/agent_jobs/issue97_anz_bank_capex_publication_v1_20260710/diff-check.json
  - reports/agent_jobs/issue97_anz_bank_capex_publication_v1_20260710/report_artifacts_check.json
  - reports/agent_jobs/issue97_anz_bank_capex_publication_v1_20260710/closeout_check.json
  - reports/agent_jobs/issue97_anz_bank_capex_publication_v1_20260710/focused_unit_red.log
  - reports/agent_jobs/issue97_anz_bank_capex_publication_v1_20260710/focused_unit_green.log
  - reports/agent_jobs/issue97_anz_bank_capex_publication_v1_20260710/focused_unit_regression.log
  - reports/agent_jobs/issue97_anz_bank_capex_publication_v1_20260710/ruff.log
  - reports/agent_jobs/issue97_anz_bank_capex_publication_v1_20260710/diff-whitespace.log
  - reports/agent_jobs/issue97_anz_bank_capex_publication_v1_20260710/full_replay_green/input_manifest.json
  - reports/agent_jobs/issue97_anz_bank_capex_publication_v1_20260710/full_replay_green/replay_results.json
  - reports/agent_jobs/issue97_anz_bank_capex_publication_v1_20260710/full_replay_green/side_effect_audit.json
  - reports/agent_jobs/issue97_anz_bank_capex_publication_v1_20260710/full_replay_green/validation.json
  - reports/agent_jobs/issue97_anz_bank_capex_publication_v1_20260710/full_replay_green/logs/replay.log
  - reports/agent_jobs/issue97_anz_bank_capex_publication_v1_20260710/scripts/build_scorecard.py
  - reports/agent_jobs/issue97_anz_bank_capex_publication_v1_20260710/actual_payload_map_green.json
  - reports/agent_jobs/issue97_anz_bank_capex_publication_v1_20260710/payload_scorecard_green.json
  - reports/agent_jobs/issue97_anz_bank_capex_publication_v1_20260710/scorecard_gate_green.json
  - reports/agent_jobs/issue97_anz_bank_capex_publication_v1_20260710/failure_class_summary_green.json
  - reports/agent_jobs/issue97_anz_bank_capex_publication_v1_20260710/row_level_failure_matrix_green.json
  - reports/agent_jobs/issue97_anz_bank_capex_publication_v1_20260710/scorecard_build_green.log
  - reports/agent_jobs/issue97_anz_bank_capex_publication_v1_20260710/final_guard_preflight.json
  - reports/agent_jobs/issue97_anz_bank_capex_publication_v1_20260710/LEDGER_ENTRY_CLAIMED.json
  - reports/agent_jobs/issue97_anz_bank_capex_publication_v1_20260710/LEDGER_ENTRY_IMPLEMENTATION_STARTED.json
  - reports/agent_jobs/issue97_anz_bank_capex_publication_v1_20260710/LEDGER_ENTRY_PR_OPENED.json
  - reports/agent_jobs/issue97_anz_bank_capex_publication_v1_20260710/PR_OPENED.json
approval_required: true
approval_context: "USER_APPROVED_2026-07-10: create a fresh live-current-canonical sibling, port only the existing ANZ-income plus bank-capex two-file baseline, repair the non-financial-asset predicate boundary, validate, commit, push, and open a draft PR; do not merge."
timeout_seconds: 21600
output_dir: reports/agent_jobs/issue97_anz_bank_capex_publication_v1_20260710
mutation_mode: safe_extension
production_data_access: false
github_mutation_allowed: true
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
reason: "Preservation publication of an already source-proven ANZ income and bank cash-flow capex baseline, plus one same-family predicate-boundary correction and regression. No durable operator, schema, API, runtime, or architecture contract changes."
task_tier: critical
recommended_model: "high reasoning"
actual_model: "Codex GPT-5"
why_this_model: "Financial Truth source-class semantics, full replay interpretation, overlapping preserved worktrees, and GitHub publication require strict final judgment."
worker_model_allowed: false
worker_decision_limit: "No workers; all source/test mutation and publication decisions remain serialized in the primary worktree."
escalation_needed: false
task_scope: safe_extension
selected_issue: 97
deferred_issue: 96
base_ref: origin/migration/clean-runtime-baseline-reconstruct-v1
base_head: 1b1919346da84e5dea74226ba787359e69348f36
---

# Issue #97 ANZ Income And Bank Capex Publication

## Objective

Publish the already validated ANZ-income and bank cash-flow capex two-file
baseline from a fresh live-current-canonical worktree. Before publication,
correct only the confirmed semantic false positive where normalized
`financialasset` matching also rejects `non-financial assets`, with a focused
positive/negative regression.

## Exact Source

- Read-only baseline worktree:
  `/home/l4nd0/tenn-issue97-bank-cashflow-capex-source-selection-v1-20260709`
- Port only its working diff for:
  - `financial-engine_v2/backend/app/services/multipass_extraction.py`
  - `financial-engine_v2/backend/tests/test_multipass_extraction.py`
- Exclude the later WOW-only delta from
  `/home/l4nd0/tenn-issue97-wow-net-debt-current-canonical-v1-20260710`.

## Hard Stops

- Preserve `/home/l4nd0/tenn` and both named dirty Issue #97 worktrees
  unchanged.
- No WOW NPAT, WOW net-debt, AZJ, SEG, TLS, missing-evidence, or ANZ
  magnitude-gate retargeting.
- No source PDF, gold label, prompt, manifest, accepted-output gate, DB,
  Qdrant, Redis, news, memory, runtime/data, service, registry, model/GPU,
  dependency, or unrelated branch-history mutation.
- Commit only the exact task-card publication files; push only this new branch;
  open a draft PR only; never merge.

## Validation

- Red/green focused predicate regression.
- Affected capex and income regressions.
- Ruff and `git diff --check`.
- Complete approved15 no-write replay without an aggregate-suite timeout.
- Current-replay-only payload scorecard and pre-persistence gate.
- Final code review, PR review, task contract checks, and Git guard.

## Closeout

Open a draft PR when the bounded bundle is coherent. Keep the extraction result
`PARTIAL` if the inherited ANZ magnitude gate or non-target scorecard blockers
remain.
