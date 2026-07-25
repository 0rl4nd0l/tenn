#!/usr/bin/env bash
set -euo pipefail

CODEX_X_STATE_ROOT=/home/l4nd0/codex-x-pilot/.state \
  /home/l4nd0/codex-x-pilot-transport-contract-v1-20260725/bin/codex-x-child \
  --run 20260725T041849Z-107c926930-e0e992 \
  --ticket-id ASXFP_01_SCORECARDS \
  --prompt-file /home/l4nd0/tenn-codex-x-extraction-supervisor-v1-20260724/reports/agent_jobs/tenn_codex_x_extraction_programme_20260724/proposed_run_package/revisions/asxfp01_response_schema_repair_20260725/prompts/ASXFP_01_SCORECARDS-implementer-transport-v3.txt \
  --prompt-sha256 1bbb5077adb1fbd0c57230d931197897e68204e534c05a09d9513bf3620ee9fc \
  --expected-head 107c926930ef5a14783a8293bac9b47c9046bfed \
  --expected-tree 9e43e6380c357e1a40a23bff6d4a07522c86ff98 \
  --allowed-scope /home/l4nd0/tenn-codex-x-extraction-supervisor-v1-20260724/reports/agent_jobs/tenn_codex_x_extraction_programme_20260724/proposed_run_package/revisions/asxfp01_response_schema_repair_20260725/allowed_scope.json \
  --model-output-schema /home/l4nd0/tenn-codex-x-extraction-supervisor-v1-20260724/reports/agent_jobs/tenn_codex_x_extraction_programme_20260724/proposed_run_package/revisions/asxfp01_response_schema_repair_20260725/schemas/model_output.schema.json \
  --child-result-schema /home/l4nd0/tenn-codex-x-extraction-supervisor-v1-20260724/reports/agent_jobs/tenn_codex_x_extraction_programme_20260724/proposed_run_package/revisions/asxfp01_response_schema_repair_20260725/schemas/child_result.schema.json \
  --model-output /home/l4nd0/tenn-codex-x-extraction-supervisor-v1-20260724/reports/agent_jobs/tenn_codex_x_extraction_programme_20260724/proposed_run_package/revisions/asxfp01_response_schema_repair_20260725/child_outputs/ASXFP_01_SCORECARDS-implementer-transport-v3.json \
  --child-result /home/l4nd0/tenn-codex-x-extraction-supervisor-v1-20260724/reports/agent_jobs/tenn_codex_x_extraction_programme_20260724/proposed_run_package/revisions/asxfp01_response_schema_repair_20260725/child_results/ASXFP_01_SCORECARDS-implementer-transport-v3.json \
  --events-output /home/l4nd0/tenn-codex-x-extraction-supervisor-v1-20260724/reports/agent_jobs/tenn_codex_x_extraction_programme_20260724/proposed_run_package/revisions/asxfp01_response_schema_repair_20260725/transport_events/ASXFP_01_SCORECARDS-implementer-transport-v3.jsonl
