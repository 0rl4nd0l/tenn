worker_id: lane-f-gate
        task_tier: small
        model: deepseek/deepseek-chat
        decision_limit: evidence_only
        summary: OpenCode remote readonly permission enforcement could not be proven.
        findings:
        - DATA_MISSING: OpenCode worker did not produce a usable result.
        evidence_paths:
        - reports/agent_jobs/extraction_approved15_blocker_lanes_v1_20260629/workers/lane-f-gate/WORKER_META.json
- reports/agent_jobs/extraction_approved15_blocker_lanes_v1_20260629/workers/lane-f-gate/raw_output.txt
        confidence: low
        risks:
        - Worker output may be incomplete; Codex must inspect raw_output.txt and WORKER_META.json.
        recommended_next_action: revise
        stop_condition_hit: yes
