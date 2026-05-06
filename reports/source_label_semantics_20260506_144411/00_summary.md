# Summary

## Decision

Proceed and commit was safe after preflight because the only pre-existing dirty file was the known unrelated `tenn_prompt_contracts_response_guidelines.zip`, and the implementation stayed within allowed Provenance, Reporting, and Query Orchestration surfaces.

## Implemented

The source-label contract is now propagated through backend chat metadata, Cockpit API source normalization, agent-loop degraded runtime metadata, and the Cockpit chat UI trust label. Generic "Source-backed" rendering was replaced for the updated answer shell paths with evidence-role aware labels.

## Exact Files Changed

Runtime and serialization:

- `financial-engine_v2/backend/app/services/tenn_chat.py`
- `financial-engine_v2/backend/app/routes/cockpit_api.py`
- `financial-engine_v2/cockpit/core/agent_loop.py`
- `cockpit-ui/lib/cockpit-types.ts`
- `cockpit-ui/lib/api-client.ts`
- `cockpit-ui/components/cockpit/chat/chat-screen.tsx`
- `cockpit-ui/components/cockpit/chat/terminal-message.tsx`

Tests:

- `financial-engine_v2/backend/tests/test_build_ui_sources.py`
- `financial-engine_v2/backend/tests/test_cockpit_api_models.py`
- `financial-engine_v2/backend/tests/test_cockpit_api_chat_stream.py`
- `financial-engine_v2/backend/tests/test_news_retrieval_eval.py`
- `financial-engine_v2/cockpit/tests/test_agent_loop_synthesis_timeout.py`
- `cockpit-ui/components/cockpit/chat/terminal-message.test.tsx`

Report:

- `reports/source_label_semantics_20260506_144411/README.md`
- `reports/source_label_semantics_20260506_144411/00_summary.md`
- `reports/source_label_semantics_20260506_144411/01_preflight.md`
- `reports/source_label_semantics_20260506_144411/02_existing_label_paths.md`
- `reports/source_label_semantics_20260506_144411/03_label_taxonomy.md`
- `reports/source_label_semantics_20260506_144411/04_change_summary.md`
- `reports/source_label_semantics_20260506_144411/05_test_matrix.md`
- `reports/source_label_semantics_20260506_144411/06_validation.md`
- `reports/source_label_semantics_20260506_144411/07_remaining_risks.md`
- `reports/source_label_semantics_20260506_144411/08_next_codex_prompt_reporting_ui.md`

## Verdicts

- A2M case covered: yes. A2M recall news can be labelled `local_news_context` and `claim_verified` only when supporting evidence matches the retrieved local news source.
- Holdings label remained correct: yes. Holdings remains `local_personal_data` / `cockpit-local`, not financial truth or external source-backed.
- Runtime degraded state surfaced: yes. Degraded Tenn chat and agent-loop timeout/failure paths now emit degraded metadata.
- Source drawer changed: no. Source item metadata is serialized for the drawer, but the drawer component was intentionally not redesigned in this lane.
