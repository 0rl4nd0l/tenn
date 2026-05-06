# Next Codex Prompt

Task: Textual Sources or QueryOrchestrator Envelope Follow-Up

Lane: Query Orchestration
Supporting lane: Provenance
Execution mode: SAFE EXTENSION MODE after preflight

Mission:

Audit and, if safe, extend the remaining non-Cockpit or non-web-UI source
surfaces so they consume the same source-label/evidence-role contract:

- legacy `/api/chat` response envelopes
- QueryOrchestrator direct-result metadata envelope
- Textual/local TUI sources display
- any remaining source drawer edge cases not covered by Cockpit web UI tests

Do not:

- run ingestion
- reindex or mutate Qdrant
- mutate `news.sqlite`
- mutate memory stores
- change financial truth extraction
- change retrieval ranking
- redesign the source-label taxonomy
- expose raw chain-of-thought

Required preflight:

- Read `docs/architecture/SYSTEM_CONTRACT.md`
- Read `docs/architecture/21_cockpit_client_contract.md`
- Read `reports/tool_no_hit_runtime_semantics_20260506_162735/`
- Run branch/status/active-job checks
- Stop on HIGH overlap or any required DB/vector/memory mutation

Expected output:

- Minimal code changes, if needed
- Focused fixture tests only
- Report folder with validation and remaining gaps
