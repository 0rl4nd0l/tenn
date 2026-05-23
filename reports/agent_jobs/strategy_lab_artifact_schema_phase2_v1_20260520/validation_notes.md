# Validation Notes

## What Was Validated In Phase 2

- Task card parsed and passed `scripts/agent_job_contract.py validate`.
- Registry `list-active` showed no active jobs before claim.
- Registry `check-overlap` passed in the isolated worktree.
- Registry claim succeeded.
- JSON schema file parsed as JSON with `python3 -m json.tool`.
- All JSON fixtures parsed as JSON with `python3 -m json.tool`.

## What Was Not Implemented

- No artifact store.
- No MCP/API adapter.
- No Cockpit UI/backend wiring.
- No Tenn runtime code.
- No DB, Qdrant, news, memory, or financial-truth writes.
- No parser, extraction, or gold-label changes.
- No Docker, systemd, env, or secrets changes.
- No QuantDinger startup.
- No token issuance.
- No broker/exchange, paper, or live execution config.
- No production data access.

## JSON Schema Dependency Note

The local Python environment did not have `jsonschema` installed:

```text
ModuleNotFoundError: No module named 'jsonschema'
```

No dependency was added and no runtime validator was implemented. Phase 2 validation is limited to parse checks, task-card/registry checks, `git diff --check`, and `agent_job_contract.py check-diff`.

## Future Offline Validator Contract

A future offline validator should:

1. Parse the candidate artifact JSON.
2. Validate against `docs/strategy_lab/artifact_schema_v1.schema.json`.
3. Recursively scan `payload`, `parameters`, `normalized_result`, and any nested object for forbidden credential or execution keys.
4. Require all safety/truth flags to be literal `false`.
5. Require `review_status` to be present.
6. Require `review_status=PENDING_REVIEW` for machine-generated sidecar artifacts unless a Tenn-owned `human_review_decision` artifact is being validated.
7. Require `raw_payload_ref.path` and `raw_payload_ref.source_report_path` for QuantDinger artifacts.
8. Require `benchmark` to be present; if benchmark is absent in source data, require a `DATA_MISSING` explanation.
9. Reject `financial_truth` and generic `source-backed` evidence labels.
10. Emit a report-only validation result without touching Tenn runtime, Cockpit, DB, Qdrant, news, memory, financial-truth, parser, extraction, gold labels, services, tokens, or execution surfaces.

## Parse Validation Command

Expected command shape:

```bash
python3 -m json.tool docs/strategy_lab/artifact_schema_v1.schema.json >/dev/null
for f in docs/strategy_lab/artifact_fixtures/*.json; do python3 -m json.tool "$f" >/dev/null || exit 1; done
```

## Final Validation

Final validation results are summarized in `README.md` after the registry release and final status checks.
