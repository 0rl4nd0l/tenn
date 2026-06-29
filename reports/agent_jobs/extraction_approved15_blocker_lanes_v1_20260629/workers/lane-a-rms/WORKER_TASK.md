# Worker Task

            worker_id: lane-a-rms
            source_task_file: reports/agent_jobs/extraction_approved15_blocker_lanes_v1_20260629/workers/lane-a-rms/WORKER_TASK.md

            ## Task

            # Worker Task

worker_id: lane-a-rms
lane: A RMS cash-flow missing metrics
task_tier: small
decision_limit: evidence_only
permission_profile: readonly
agent: build
model: deepseek/deepseek-chat
workdir: /home/l4nd0/tenn-extraction-approved15-blocker-lanes-v1-20260629
branch: safe/extraction-approved15-blocker-lanes-v1-20260629
task_card: docs/agent_tasks/extraction_approved15_blocker_lanes_v1_20260629.md
allowed_files:
- reports/agent_jobs/extraction_approved15_blocker_lanes_v1_20260629/workers/lane-a-rms/WORKER_RESULT.md
validation_expected:
- read-only grep/jq only
result_path: reports/agent_jobs/extraction_approved15_blocker_lanes_v1_20260629/workers/lane-a-rms/WORKER_RESULT.md
stop_condition: Any finding requires source PDF/gold-label/runtime/DB mutation or cannot be proven from repo/report/source-text artifacts.

## Objective

Confirm the RMS missing cash-flow metric lineage from repo/report artifacts and
identify whether a single deterministic source-bound fix is eligible.

## Allowed Evidence And Files

- financial-engine_v2/backend/tests/eval_fixtures/RMS_H_2025-12-31.json
- financial-engine_v2/backend/app/services/multipass_extraction.py
- financial-engine_v2/backend/tests/test_multipass_extraction.py
- reports/agent_jobs/extraction_broad_approved15_current_canonical_v1_20260628/actual_payload_map_after_fix.json
- reports/agent_jobs/extraction_broad_approved15_current_canonical_v1_20260628/failure_classes_after_fix.json
- reports/agent_jobs/extraction_broad_approved15_current_canonical_v1_20260628/row_level_failure_matrix_after_fix.json

## Required Output

Return `WORKER_RESULT.md` content with source evidence, failure lineage,
remediation eligibility, validation plan, confidence, risks, and
recommended_next_action.
