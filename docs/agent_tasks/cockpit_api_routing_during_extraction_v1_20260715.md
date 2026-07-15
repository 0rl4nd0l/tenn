---
job_id: cockpit_api_routing_during_extraction_v1_20260715
lane: Query Orchestration
supporting_lanes:
  - Extraction
  - Evaluation
  - Reporting
owner: Codex
approval_required: true
allow_unapproved_safe_extension: false
allow_audit_code_changes: false
timeout_seconds: 7200
output_dir: reports/agent_jobs/cockpit_api_routing_during_extraction_v1_20260715
mutation_mode: safe_extension
production_data_access: false
allowed_files:
  - docs/agent_tasks/cockpit_api_routing_during_extraction_v1_20260715.md
  - docs/architecture/SYSTEM_CONTRACT.md
  - financial-engine_v2/cockpit/core/chat.py
  - financial-engine_v2/cockpit/core/config.py
  - financial-engine_v2/cockpit/core/agent/anthropic_client.py
  - financial-engine_v2/cockpit/tests/test_chat_keyword_api_routing.py
  - financial-engine_v2/cockpit/tests/test_anthropic_client.py
  - financial-engine_v2/cockpit/tests/test_chat_ticker_detection.py
  - financial-engine_v2/cockpit/tests/test_llm_backend_readonly_format.py
  - financial-engine_v2/config/cockpit_llm.yaml
  - financial-engine_v2/backend/app/services/llm.py
  - financial-engine_v2/backend/app/services/news_memo_extractor.py
  - financial-engine_v2/backend/tests/test_llm_fallback_policy.py
  - financial-engine_v2/backend/tests/test_news_memo_extractor.py
  - reports/agent_jobs/cockpit_api_routing_during_extraction_v1_20260715/README.md
  - reports/agent_jobs/cockpit_api_routing_during_extraction_v1_20260715/STATE.md
  - reports/agent_jobs/cockpit_api_routing_during_extraction_v1_20260715/DECISIONS.md
  - reports/agent_jobs/cockpit_api_routing_during_extraction_v1_20260715/VALIDATION.md
  - reports/agent_jobs/cockpit_api_routing_during_extraction_v1_20260715/CODE_REVIEW.json
  - reports/agent_jobs/cockpit_api_routing_during_extraction_v1_20260715/RUNTIME_FUNCTIONALITY_PROOF.md
  - reports/agent_jobs/cockpit_api_routing_during_extraction_v1_20260715/RUN_OUTCOME.json
  - reports/agent_jobs/cockpit_api_routing_during_extraction_v1_20260715/DECISION_ENTRY.json
  - reports/agent_jobs/cockpit_api_routing_during_extraction_v1_20260715/LEDGER_ENTRY.json
  - reports/agent_jobs/cockpit_api_routing_during_extraction_v1_20260715/NEXT_GOAL.md
  - reports/agent_jobs/cockpit_api_routing_during_extraction_v1_20260715/
github_writes_allowed: []
closeout_scope: code_only
control_contract_version: 2
project_id: tenn
claim_id: cockpit_api_routing_during_extraction
proof_question: Can Cockpit and non-metric LLM tool work avoid the shared local router while metric extraction owns it, without changing metric extraction semantics?
hypothesis_id: extraction_exclusive_routes_nonmetric_llm_to_claude_v1
program_track: offline_development
entry_state: keyword_chat_and_news_memo_llm_can_contend_with_metric_extraction
target_transition: metric_extraction_local_nonmetric_llm_claude_during_extraction
exit_predicate: Focused tests prove keyword chat and non-metric JSON LLM calls avoid local generation during active metric extraction, metric extraction remains local, provenance is truthful, and the stateless Claude smoke succeeds.
source_class: tenn_canonical_backend_source
dataset_version: migration_clean_runtime_baseline_af1b33eb2a5e
evidence_hash: sha256:c122730efc0d35c6dae380a8341d3b8e1d25afe4a439d19580b4718aebae32cd
capabilities:
  - READ
  - REPORT_WRITE
  - CODE_EDIT
resume_only_if: Canonical routing code, Anthropic availability, or focused regression evidence changes after closeout.
---

# Cockpit API Routing During Extraction

## Objective

Prevent interactive Cockpit chat and non-metric LLM tool work from contending
with metric extraction on the shared local llama.cpp router.

## Approved Behavior

- Keep metric extraction pinned to its deterministic local instruct model.
- Construct Cockpit's HybridRouter in both keyword and structured chat modes.
- Replace the retired Cockpit Claude model default with Anthropic's canonical
  `claude-sonnet-4-6` model ID.
- Route keyword news, action, and tool synthesis through Claude when configured.
- While metric extraction is active, route non-metric JSON LLM calls, including
  news memo work, to Claude before touching the local router.
- Fail fast instead of falling back to the protected local router when Claude is
  unavailable during active metric extraction.
- Preserve truthful provider, model, endpoint, and routing-reason provenance.

## Hard Boundaries

- Do not change extraction prompts, metric schemas, gold labels, source PDFs,
  embedding behavior, vector stores, DB contents, Qdrant, Redis data, or news
  stores.
- Do not start a metric extraction, backfill, ingestion, or production job.
- Do not restart live services or modify live runtime environment files.
- Do not push, merge, rebase, stash, reset, clean, or mutate GitHub.
- After the owner-approved credential, payload-shape, and retired-model
  diagnostics, one final stateless Claude API smoke call is allowed against the
  repaired model default; do not persist chat.
- Create one local commit only after focused validation and review are green.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/cockpit_api_routing_during_extraction_v1_20260715.md`
- focused RED/GREEN pytest for keyword chat routing
- focused RED/GREEN pytest for extraction-active backend LLM routing
- focused Cockpit and backend routing regression tests
- one isolated stateless Claude API smoke call
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/cockpit_api_routing_during_extraction_v1_20260715.md --repo-root .`
- code review of the final diff

## Definition Of Done

- Tests prove keyword-mode chat uses HybridRouter/Claude rather than direct
  llama.cpp.
- Tests prove active metric extraction sends non-metric JSON LLM work to Claude
  and never invokes local generation.
- Tests prove metric extraction itself remains local.
- News memo provenance identifies the effective provider and model.
- Cockpit configuration and the standalone Anthropic adapter default to
  `claude-sonnet-4-6`.
- Stateless Claude smoke succeeds without chat persistence.
- Approved files are committed locally; nothing is pushed or activated live.
