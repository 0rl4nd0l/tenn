---
job_id: reporting_textual_sources_list_v1
lane: Reporting
owner: Codex
allowed_files:
  - docs/agent_tasks/reporting_textual_sources_list_v1.md
  - financial-engine_v2/backend/app/services/query_orchestrator.py
  - financial-engine_v2/backend/app/services/tenn_chat.py
  - financial-engine_v2/backend/app/routes/cockpit_api.py
  - financial-engine_v2/cockpit/core/chat.py
  - financial-engine_v2/cockpit/core/agent_loop.py
  - financial-engine_v2/cockpit/core/tool_executor.py
  - financial-engine_v2/cockpit/core/response_classification.py
  - financial-engine_v2/backend/tests/
  - financial-engine_v2/cockpit/tests/
  - financial-engine_v2/cockpit/tests/test_slash_commands.py
  - financial-engine_v2/cockpit/tests/test_chat_orchestrator_integration.py
  - reports/textual_sources_list_envelope_consumption_*/
  - reports/textual_sources_list_envelope_consumption_20260506_172946/README.md
  - reports/textual_sources_list_envelope_consumption_20260506_172946/00_summary.md
  - reports/textual_sources_list_envelope_consumption_20260506_172946/01_preflight.md
  - reports/textual_sources_list_envelope_consumption_20260506_172946/02_existing_gap.md
  - reports/textual_sources_list_envelope_consumption_20260506_172946/03_change_summary.md
  - reports/textual_sources_list_envelope_consumption_20260506_172946/04_textual_output_contract.md
  - reports/textual_sources_list_envelope_consumption_20260506_172946/05_test_matrix.md
  - reports/textual_sources_list_envelope_consumption_20260506_172946/06_validation.md
  - reports/textual_sources_list_envelope_consumption_20260506_172946/07_remaining_gaps.md
  - reports/textual_sources_list_envelope_consumption_20260506_172946/08_next_codex_prompt_legacy_api_chat_audit.md
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 1800
output_dir: reports/agent_jobs/reporting_textual_sources_list_v1
mutation_mode: safe_extension
production_data_access: false
---

# Textual Sources List Envelope Consumption v1

## Task

Implement G003 Textual `/sources list` v1.

Use the new `QueryOrchestrator.evidence_envelope` from commit `998d103d26c1` so textual source displays preserve evidence-role taxonomy instead of collapsing roles into generic source-backed language.

## Lane

Reporting

Supporting lanes: Provenance, Query Orchestration

## Branch / Worktree

Branch: `preserve/dirty-work-20260430T065748Z`

Worktree: `/mnt/sdb2/home/l4nd0/tenn`

## Execution Mode

SAFE EXTENSION MODE after preflight.

## Collision Assessment

MEDIUM.

Reason:

- `998d103d26c1 fix(query): add evidence taxonomy envelope to orchestrator` landed.
- G005 is fixed.
- Remaining gap G003 is textual `/sources list` / textual source display still not consuming the evidence taxonomy envelope.
- This task should adapt textual source display to consume the existing envelope, not invent a second mapping.

## Do Not

- mutate Qdrant
- mutate `news.sqlite`
- mutate company/market/thesis/session memory
- run ingestion
- reindex news
- run memory cleanup
- change retrieval ranking
- change financial truth extraction
- change source drawer UI
- change legacy `/api/chat`
- redesign deep research
- expose raw chain-of-thought
- touch unrelated dirty files
- touch `tenn_prompt_contracts_response_guidelines.zip`
- touch Cockpit home/design export files
- fix watchlist/commentary/marketplace/agent-hook dirty work

## Mission

Make textual `/sources list` or equivalent local textual source display taxonomy-safe by consuming the `QueryOrchestrator.evidence_envelope`.

The textual source output must distinguish evidence roles such as:

- `claim_verified`
- `context_only`
- `no_hit`
- `operational_trace`
- `local_personal_data`
- `memory_context`
- `external_web_context`
- `local_news_context`
- `financial_truth`
- `degraded_runtime`
- `missing_required_evidence`
- `unknown_unclassified`

It must not collapse roles into vague `source-backed`.

## Source Context

Inspect first:

- `reports/query_orchestrator_evidence_envelope_20260506_170507/`
- `reports/textual_sources_query_orchestrator_envelope_audit_20260506_164051/`
- `reports/source_label_semantics_20260506_144411/`
- `reports/source_label_propagation_drawer_honesty_20260506_154915/`
- `reports/tool_no_hit_runtime_semantics_20260506_162735/`
- `docs/architecture/SYSTEM_CONTRACT.md`
- `docs/architecture/21_cockpit_client_contract.md`

Relevant files to inspect:

- `financial-engine_v2/backend/app/services/query_orchestrator.py`
- `financial-engine_v2/backend/app/services/tenn_chat.py`
- `financial-engine_v2/backend/app/routes/cockpit_api.py`
- `financial-engine_v2/cockpit/core/chat.py`
- `financial-engine_v2/cockpit/core/agent_loop.py`
- `financial-engine_v2/cockpit/core/tool_executor.py`
- `financial-engine_v2/cockpit/core/response_classification.py`
- `financial-engine_v2/backend/tests/test_query_orchestrator.py`
- `financial-engine_v2/backend/tests/test_sources.py`

## Preflight

Run and record:

```bash
pwd
git branch --show-current
git rev-parse HEAD
git status --short
git log --oneline -n 45
git merge-base --is-ancestor 998d103d26c1 HEAD && echo query_orchestrator_envelope_present
```

Classify dirty files. Stop if dirty/untracked files overlap textual source display, QueryOrchestrator, source/evidence helpers, or tests needed here.

## Hard Stops

Stop and report only if:

- `reports/query_orchestrator_evidence_envelope_20260506_170507/` is missing
- HEAD does not contain `998d103d26c1`
- dirty files overlap this task's required files
- implementation requires source drawer UI changes
- implementation requires legacy `/api/chat` changes
- implementation requires retrieval ranking changes
- implementation requires DB/Qdrant/memory mutation
- implementation requires ingestion/reindexing
- implementation requires broad synthesis prompt rewrite
- tests require live external services

## Required Behavior

Textual `/sources list` or equivalent textual display must read from the evidence envelope where available.
It must preserve evidence roles and source status.
It must distinguish:

- claim-verified evidence
- context-only evidence
- local holdings / personal data
- memory context
- local news
- financial truth
- external web
- no-hit
- degraded runtime
- missing evidence
- unknown/unclassified

Unknown/unclassified must not render as claim-verified.
No-hit must not render as source-backed.
Degraded runtime must be visible.
If envelope is unavailable, use safe fallback wording, not generic verified wording.
Existing Cockpit chat path must not regress.
Existing A2M ticker-news, holdings, memory-context, and attached-source behavior must not regress.

## Implementation Guidance

Prefer:

- minimal formatting helper
- reuse envelope fields from QueryOrchestrator
- tests around output text/metadata
- no UI/source drawer change

Avoid:

- new provenance framework
- duplicate taxonomy mapping
- hardcoded A2M-specific logic
- broad chat-route refactor

## Allowed Files

Only if needed:

- `financial-engine_v2/backend/app/services/query_orchestrator.py`
- `financial-engine_v2/backend/app/services/tenn_chat.py`
- `financial-engine_v2/backend/app/routes/cockpit_api.py`
- `financial-engine_v2/cockpit/core/chat.py`
- `financial-engine_v2/cockpit/core/agent_loop.py`
- `financial-engine_v2/cockpit/core/tool_executor.py`
- `financial-engine_v2/cockpit/core/response_classification.py`
- `financial-engine_v2/backend/tests/`
- `financial-engine_v2/cockpit/tests/`
- `reports/textual_sources_list_envelope_consumption_<timestamp>/`

If other files are required, stop and explain before editing.

## Required Tests

Add or update focused tests proving:

- Textual sources display includes claim_verified sources distinctly.
- Textual sources display includes context_only sources distinctly.
- `no_hit` does not render as source-backed.
- `degraded_runtime` is visible.
- `local_personal_data` holdings are not financial truth.
- `memory_context` is not claim-verified.
- `financial_truth` remains distinguishable.
- `local_news_context` remains distinguishable.
- Unknown source type falls back safely.
- No envelope fallback is safe and non-verified.

## Validation

Run:

```bash
financial-engine_v2/.venv/bin/python -m pytest financial-engine_v2/backend/tests/test_query_orchestrator.py financial-engine_v2/backend/tests/test_sources.py -q
financial-engine_v2/.venv/bin/python -m pytest financial-engine_v2/backend/tests -k "sources or textual or evidence or envelope or no_hit or degraded or holdings or memory or financial_truth or local_news" -q
financial-engine_v2/.venv/bin/python -m ruff check <changed_python_files>
git diff --check
```

Record unrelated failures and do not fix them.

## Report Output

Create:

`reports/textual_sources_list_envelope_consumption_<timestamp>/`

Required files:

- `README.md`
- `00_summary.md`
- `01_preflight.md`
- `02_existing_gap.md`
- `03_change_summary.md`
- `04_textual_output_contract.md`
- `05_test_matrix.md`
- `06_validation.md`
- `07_remaining_gaps.md`
- `08_next_codex_prompt_legacy_api_chat_audit.md`

## Commit Policy

If and only if:

- preflight is clean enough
- only allowed files changed
- no DB/Qdrant/memory/ingestion mutation occurred
- no UI/source drawer/legacy chat/deep research implementation occurred
- focused validation passed
- `git diff --check` passed

then create one commit:

```text
fix(reporting): render textual sources from evidence envelope
```

If commit is unsafe because of unrelated dirty work, leave changes uncommitted and report why.

## Final Verdict Required

Answer:

- Was ingestion touched?
- Was Qdrant mutated?
- Was `news.sqlite` mutated?
- Was memory mutated?
- Was retrieval ranking changed?
- Was source drawer/UI changed?
- Was legacy `/api/chat` changed?
- Was textual `/sources list` changed?
- Does it consume the evidence envelope?
- Can no-hit still appear source-backed?
- Can degraded runtime be hidden?
- Are holdings/memory/news/financial truth roles distinct?
- Did Cockpit chat regress?
- What remains blocked?

## Final Response

Return:

- lane
- execution mode
- commit hash if committed
- report folder
- files changed
- validation results
- G003 verdict
- role-rendering verdict
- remaining gaps
- next recommended lane
