---
job_id: extraction_whc_openability_runtime_endpoint_rerun_v1_20260611
lane: Financial Truth
supporting_lanes:
  - Evaluation
  - Provenance
  - Repo Hygiene
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_whc_openability_runtime_endpoint_rerun_v1_20260611.md
  - reports/agent_jobs/extraction_whc_openability_runtime_endpoint_rerun_v1_20260611/README.md
  - reports/agent_jobs/extraction_whc_openability_runtime_endpoint_rerun_v1_20260611/status.json
  - reports/agent_jobs/extraction_whc_openability_runtime_endpoint_rerun_v1_20260611/live_git_status.json
  - reports/agent_jobs/extraction_whc_openability_runtime_endpoint_rerun_v1_20260611/runtime_probe.json
  - reports/agent_jobs/extraction_whc_openability_runtime_endpoint_rerun_v1_20260611/replay_result.json
  - reports/agent_jobs/extraction_whc_openability_runtime_endpoint_rerun_v1_20260611/validation.json
  - reports/agent_jobs/extraction_whc_openability_runtime_endpoint_rerun_v1_20260611/diff-check.json
approval_required: false
allow_unapproved_safe_extension: false
allow_audit_code_changes: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/extraction_whc_openability_runtime_endpoint_rerun_v1_20260611
mutation_mode: audit_only
production_data_access: false
github_mutation_allowed: false
---

# WHC Openability Runtime Endpoint Rerun

## Objective

Resolve the previous exact WHC replay blocker:

`pass1:OLLAMA_URL must be set when provider is 'ollama'`

Probe local runtime endpoints read-only, then rerun the exact WHC openability
selected-table replay only if a live endpoint is already available and can be
used through process-local environment variables.

## Scope

- Exact ticker: WHC
- Exact document id: `9640d9f1-a45b-492d-8df5-9bad0f46431c`
- Exact source PDF:
  `/mnt/tenn-nvme2/tenn/financial-engine_v2/data/asx/docs/WHC/financial_performance/2022-09-21_2022-annual-report_9640d9f1-a45b-492d-8df5-9bad0f46431c.pdf`
- Parser backend: `pymupdf`
- Openability pages: 57, 58, 60, 61

## Allowed Actions

- Read-only local endpoint probes, including localhost Ollama and llama.cpp
  model-list/health endpoints with short timeouts.
- One exact WHC replay with temporary `DATA_ROOT`.
- Process-local env overrides for the replay only, such as `OLLAMA_URL`,
  `LLAMACPP_URL`, or `EXTRACTION_LLAMACPP_URL`, when a live endpoint is proven.
- Report artifacts only.

## Hard Stops

- Do not start services.
- Do not edit `.env`, runtime config, model config, prompts, gold labels,
  schemas, source PDFs, or code.
- Do not run count-24, count-32, random samples, broad extraction, backfill, full
  ticker-universe extraction, service routes, or production DB writes.
- Do not mutate DB, Qdrant, Redis, news, memory, source PDFs, production data,
  runtime state, model config, or GPU config.
- Do not use PR #318 as a patch source.
- Stop report-only if no live local endpoint is available.

## Validation

- Task card validate.
- Registry `list-active --read-only`.
- Runtime endpoint probe JSON.
- Exact replay command exit status if run.
- JSON validation for report artifacts.
- `git diff --check`.
- Task-card `check-diff`.
- Forbidden-surface audit.

## Final Report Requirements

Report branch/HEAD/worktree, PR #340 status, registry state, endpoint probe
results, replay command/env overrides, status/error, accepted non-null metrics
if any, validation gates, `DATA_MISSING`, forbidden actions not run, and the
next recommended task.
