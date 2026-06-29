# Worker Task

            worker_id: lane-e-ambiguous
            source_task_file: reports/agent_jobs/extraction_approved15_blocker_lanes_v1_20260629/workers/lane-e-ambiguous/WORKER_TASK.md

            ## Task

            # Worker Task

worker_id: lane-e-ambiguous
lane: E ambiguous_quarantined grouping
task_tier: small
decision_limit: evidence_only
permission_profile: readonly
agent: build
model: deepseek/deepseek-chat
workdir: /home/l4nd0/tenn-extraction-approved15-blocker-lanes-v1-20260629
branch: safe/extraction-approved15-blocker-lanes-v1-20260629
task_card: docs/agent_tasks/extraction_approved15_blocker_lanes_v1_20260629.md
allowed_files:
- reports/agent_jobs/extraction_approved15_blocker_lanes_v1_20260629/workers/lane-e-ambiguous/WORKER_RESULT.md
validation_expected:
- read-only jq grouping only
result_path: reports/agent_jobs/extraction_approved15_blocker_lanes_v1_20260629/workers/lane-e-ambiguous/WORKER_RESULT.md
stop_condition: Any finding requires scorecard policy, gold-label, source evidence, or ambiguity semantics mutation.

## Objective

Group the 73 `ambiguous_quarantined` rows by document, metric family, and
support status, and identify whether any subgroup is eligible for this run.

## Allowed Evidence And Files

- reports/agent_jobs/extraction_broad_approved15_current_canonical_v1_20260628/failure_classes_after_fix.json
- reports/agent_jobs/extraction_broad_approved15_current_canonical_v1_20260628/row_level_failure_matrix_after_fix.json
- financial-engine_v2/backend/app/services/extraction_gold_eval_scorecard.py

## Required Output

Return `WORKER_RESULT.md` content with grouping evidence, remediation
eligibility, validation plan, confidence, risks, and recommended_next_action.
