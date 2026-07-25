#!/usr/bin/env bash
set -euo pipefail

# PROPOSED ONLY. Execute only after separate owner launch authorization. This
# file was syntax-checked but was not run.
CODEX_X_STATE_ROOT=/home/l4nd0/codex-x-pilot/.state \
  /home/l4nd0/codex-x-pilot-transport-contract-v1-20260725/bin/codex-x-child \
  --run 20260725T050234Z-107c926930-7bfbc3 \
  --ticket-id ASXFP_01_SCORECARDS \
  --prompt-file /home/l4nd0/tenn-codex-x-worktree-resolution-v1-20260725/reports/agent_jobs/tenn_codex_x_extraction_programme_20260724/proposed_run_package/revisions/asxfp01_worktree_resolution_repair_20260725/prompts/ASXFP_01_SCORECARDS-implementer-transport-v4.txt \
  --prompt-sha256 b28ccf846b744a17abdd5bc91c5961314505252d058b1f3876a0cc0ba8e9bb91 \
  --expected-head 107c926930ef5a14783a8293bac9b47c9046bfed \
  --expected-tree 9e43e6380c357e1a40a23bff6d4a07522c86ff98 \
  --allowed-scope /home/l4nd0/tenn-codex-x-worktree-resolution-v1-20260725/reports/agent_jobs/tenn_codex_x_extraction_programme_20260724/proposed_run_package/revisions/asxfp01_worktree_resolution_repair_20260725/allowed_scope.json \
  --model-output-schema /home/l4nd0/tenn-codex-x-worktree-resolution-v1-20260725/reports/agent_jobs/tenn_codex_x_extraction_programme_20260724/proposed_run_package/revisions/asxfp01_worktree_resolution_repair_20260725/schemas/model_output.schema.json \
  --child-result-schema /home/l4nd0/tenn-codex-x-worktree-resolution-v1-20260725/reports/agent_jobs/tenn_codex_x_extraction_programme_20260724/proposed_run_package/revisions/asxfp01_worktree_resolution_repair_20260725/schemas/child_result.schema.json \
  --model-output /home/l4nd0/tenn-codex-x-worktree-resolution-v1-20260725/reports/agent_jobs/tenn_codex_x_extraction_programme_20260724/proposed_run_package/revisions/asxfp01_worktree_resolution_repair_20260725/child_outputs/ASXFP_01_SCORECARDS-implementer-transport-v4.json \
  --child-result /home/l4nd0/tenn-codex-x-worktree-resolution-v1-20260725/reports/agent_jobs/tenn_codex_x_extraction_programme_20260724/proposed_run_package/revisions/asxfp01_worktree_resolution_repair_20260725/child_results/ASXFP_01_SCORECARDS-implementer-transport-v4.json \
  --events-output /home/l4nd0/tenn-codex-x-worktree-resolution-v1-20260725/reports/agent_jobs/tenn_codex_x_extraction_programme_20260724/proposed_run_package/revisions/asxfp01_worktree_resolution_repair_20260725/transport_events/ASXFP_01_SCORECARDS-implementer-transport-v4.jsonl
