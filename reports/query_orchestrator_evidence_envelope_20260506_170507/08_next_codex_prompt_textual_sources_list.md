# Next Codex Prompt: Textual Sources List

You are Codex working on Tenn.

TASK
Textual `/sources list` Evidence Envelope Consumer v1.

LANE
Reporting

SUPPORTING LANE
Provenance

EXECUTION MODE
SAFE EXTENSION MODE after preflight.

MISSION
Fix G003 only: update Textual/Cockpit source-list formatting so it can preserve and display the backend-neutral evidence taxonomy envelope emitted by direct `QueryOrchestrator` results.

READ FIRST

- `CLAUDE.md`
- `docs/architecture/SYSTEM_CONTRACT.md`
- `docs/architecture/21_cockpit_client_contract.md`
- `reports/query_orchestrator_evidence_envelope_20260506_170507/`
- `reports/textual_sources_query_orchestrator_envelope_audit_20260506_164051/02_textual_sources_list_audit.md`
- `reports/textual_sources_query_orchestrator_envelope_audit_20260506_164051/06_gap_register.md`
- `financial-engine_v2/cockpit/core/sources.py`
- `financial-engine_v2/cockpit/core/chat.py`
- `financial-engine_v2/cockpit/tests/test_sources.py`

DO NOT

- mutate Qdrant, `news.sqlite`, memory, or session stores
- run ingestion or reindexing
- change retrieval ranking
- change financial truth extraction
- change source drawer UI
- change legacy `/api/chat`
- redesign deep research
- touch unrelated dirty Cockpit UI files
- expose raw chain-of-thought

REQUIREMENTS

- Consume existing `evidence_envelope` metadata when present.
- Preserve labels including `no_hit`, `degraded_runtime`, `missing_required_evidence`, `memory_context`, `local_news_context`, `external_web_context`, `local_personal_data`, `financial_truth`, and `unknown_unclassified`.
- Do not treat context/no-hit/degraded/unknown sources as claim verified.
- Keep legacy source payload display working.
- Add focused Textual source formatter tests.

VALIDATION

Run focused tests:

```text
PYTHONPATH=financial-engine_v2/backend:financial-engine_v2 financial-engine_v2/.venv/bin/python -m pytest financial-engine_v2/cockpit/tests/test_sources.py -q
financial-engine_v2/.venv/bin/python -m ruff check <changed_python_files>
git diff --check
```

FINAL RESPONSE

Return lane, execution mode, files changed, validation, commit hash if committed, G003 verdict, remaining gaps, and next safe step.
