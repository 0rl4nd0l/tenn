---
job_id: cockpit_home_narrative_readonly_adapter_v1_20260601
lane: Reporting
owner: Codex
allowed_files:
  - docs/agent_tasks/cockpit_home_narrative_readonly_adapter_v1_20260601.md
  - reports/agent_jobs/cockpit_home_narrative_readonly_adapter_v1_20260601/README.md
  - reports/agent_jobs/cockpit_home_narrative_readonly_adapter_v1_20260601/status.json
  - reports/agent_jobs/cockpit_home_narrative_readonly_adapter_v1_20260601/validation.json
  - reports/agent_jobs/cockpit_home_narrative_readonly_adapter_v1_20260601/diff-check.json
  - financial-engine_v2/backend/app/services/cockpit_home.py
  - financial-engine_v2/backend/app/routes/cockpit_api.py
  - financial-engine_v2/backend/tests/test_cockpit_home_attention_queue.py
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 21600
output_dir: reports/agent_jobs/cockpit_home_narrative_readonly_adapter_v1_20260601
mutation_mode: safe_extension
production_data_access: false
---

# Cockpit Home Narrative Read-Only Adapter

Safe-extension task for issue #151.

## Lane

Primary lane: Reporting.

## Objective

Wire Cockpit Home narrative `session_summary` to a read-only, backend-owned
operational source when one exists. Preserve explicit `DATA_MISSING` semantics
when no source row exists.

## Scope

Allowed:

- Create this task card and report artifacts.
- Update `financial-engine_v2/backend/app/services/cockpit_home.py` to derive
  a deterministic, non-financial session summary from existing read-only
  operational follow-up rows.
- Update `/api/cockpit/home/narrative` route wiring only to pass the existing
  Cockpit state store into the service.
- Add focused backend tests for empty and populated narrative cases.

Forbidden:

- Do not mutate DB, Qdrant, news, memory, or production data stores.
- Do not change canonical financial truth, parser routing, extraction prompts,
  gold labels, model/runtime/GPU/service config, Docker, cron, or service
  lifecycle.
- Do not use LLM generation or synthesis for narrative fields.
- Do not fabricate market state, news summaries, source-backed labels, or
  financial claims.
- Do not touch unrelated dirty work or the active extraction task.

## Acceptance Criteria

- Empty operational state still returns `DATA_MISSING` with existing missing
  narrative signals.
- Populated operational follow-up state returns a deterministic `session_summary`
  with clear operational provenance.
- `theme_candidates` and `tomorrow_prep` remain `DATA_MISSING` unless a
  deterministic source is identified and tested.
- No data-store mutation, ingestion, Qdrant access, memory write, or LLM
  synthesis is required.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/cockpit_home_narrative_readonly_adapter_v1_20260601.md --write-report`
- `python3 scripts/agent_job_registry.py list-active`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/cockpit_home_narrative_readonly_adapter_v1_20260601.md`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/cockpit_home_narrative_readonly_adapter_v1_20260601.md`
- focused backend Home narrative tests
- focused frontend Home BFF tests for `DATA_MISSING` vs populated narrative behavior
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/cockpit_home_narrative_readonly_adapter_v1_20260601.md`
- release the registry claim before final report
