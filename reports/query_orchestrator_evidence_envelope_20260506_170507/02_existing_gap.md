# Existing Gap

Source audit: `reports/textual_sources_query_orchestrator_envelope_audit_20260506_164051/03_query_orchestrator_envelope_audit.md`.

G005 finding: direct `QueryOrchestrator` results exposed source plan, raw evidence, missing categories, statuses, and sufficiency, but no taxonomy version, role labels, label counts, coverage status, or conservative per-source evidence-role metadata.

Risk before this patch: direct consumers could interpret source presence or `source_status=ok` as generic support, even when financial truth rows were missing, memory was context-only, or a provider had degraded.

Fix scope chosen: add a backend-neutral envelope directly to the orchestrator result, without changing downstream consumers in this task.
