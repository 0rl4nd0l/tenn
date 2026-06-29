# Worker Task

            worker_id: lane-f-gate
            source_task_file: reports/agent_jobs/extraction_approved15_blocker_lanes_v1_20260629/workers/lane-f-gate/WORKER_TASK.md

            ## Task

            # Worker Task

worker_id: lane-f-gate
lane: F orchestrator integration gate
task_tier: small
decision_limit: evidence_only
permission_profile: readonly
agent: build
model: deepseek/deepseek-chat
workdir: /home/l4nd0/tenn-extraction-approved15-blocker-lanes-v1-20260629
branch: safe/extraction-approved15-blocker-lanes-v1-20260629
task_card: docs/agent_tasks/extraction_approved15_blocker_lanes_v1_20260629.md
allowed_files:
- reports/agent_jobs/extraction_approved15_blocker_lanes_v1_20260629/workers/lane-f-gate/WORKER_RESULT.md
validation_expected:
- read-only command discovery only
result_path: reports/agent_jobs/extraction_approved15_blocker_lanes_v1_20260629/workers/lane-f-gate/WORKER_RESULT.md
stop_condition: Any validation plan requires runtime services, production stores, count-24/count-32, GitHub mutation, or broad backfill.

## Objective

Identify the exact report-local validation sequence after any single fix:
focused no-write replay, payload scorecard rebuild, gate rebuild, side-effect
audit, task-card check-diff, and stop-state reporting.

## Allowed Evidence And Files

- scripts/extraction_no_write_replay.py
- financial-engine_v2/backend/app/services/extraction_gold_eval_scorecard.py
- reports/agent_jobs/extraction_broad_approved15_current_canonical_v1_20260628/no_write_replay_approved15/input_manifest.json
- reports/agent_jobs/extraction_broad_approved15_current_canonical_v1_20260628/validation.json
- reports/agent_jobs/extraction_broad_approved15_current_canonical_v1_20260628/scorecard_gate_after_fix.json

## Required Output

Return `WORKER_RESULT.md` content with command sequence, failure stop states,
scorecard/gate rebuild inputs, confidence, risks, and recommended_next_action.
