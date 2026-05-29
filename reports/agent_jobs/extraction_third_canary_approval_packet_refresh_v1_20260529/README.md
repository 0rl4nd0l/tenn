# Extraction Third Canary Approval Packet Refresh

## Summary

- Job: `extraction_third_canary_approval_packet_refresh_v1_20260529`
- Related issue: #96
- Generated: `2026-05-29T07:24:50Z`
- Branch: `migration/clean-runtime-baseline-reconstruct-v1`
- HEAD: `26ca0c4a0e017837b02b969a6a0bf5617eae566c`
- Mode: SAFE EXTENSION, report-local approval packet only
- Third canary run: no
- Broad backfill run: no
- DB/Qdrant/news/memory/canonical truth writes: no
- Source PDF edits/copies/deletes/commits: no
- Runtime/model/GPU/service changes: no

The previous #96 approval packet from 2026-05-27 is no longer safe to use as-is.
It included advisory-only PLS/SFR candidates, and the first two orders were
already submitted in the stopped retry. This refresh keeps only the still
unsubmitted, non-advisory prior-primary candidates whose source paths currently
exist.

## Current Candidate Decision

Eligible for a future approval-gated third canary, in order:

1. AAU `508fc892-ae88-45ec-981f-cd9e124c8375`
2. ATM `96e9aabd-44dc-4c2c-be8c-74248a0a9025`
3. AM5 `aacc4c29-3089-48cf-8b82-8004134f9387`
4. AQX `0ed0104f-f29a-4068-8ff7-370f14fead98`
5. CRS `b43a16fb-7660-4bf7-96ab-0db641cd4032`
6. CLV `da9f9ea5-6596-464f-af14-5acf12f9b050`
7. CTM `035c6758-7aed-41a6-9e84-ad154125d431`

Excluded from the prior primary list:

- BHP `2fa98e79-9d34-4cc6-9977-bfc8e9b7eeb7`: already submitted; completed
  `ok_low_confidence` in the stopped retry and wrote one financial row.
- PLS `918f0b4a-563b-4e53-962a-82f43882d667`: already submitted and current
  source-document policy classifies its title as `advisory_only_document`.
- SFR `789130bc-b2db-45b3-a8e0-46d8c71588f1`: not submitted, but current
  source-document policy classifies its title as `advisory_only_document`.

## Approval Question

This packet does not approve execution. A future canary requires this exact
operator approval string:

`APPROVE #96 THIRD CANARY extraction_third_canary_approval_packet_refresh_v1_20260529`

Approval scope is only the seven eligible document IDs in
`canary_approval_packet.json`, in that order, one document at a time. Optional
failed-parser retry candidates from the old 2026-05-27 packet are not included.

## Required Pre-Run Gates

Immediately before any approved canary execution:

- Validate this task card and check registry overlap.
- Claim a runtime canary task card with `approval_required: true`.
- Confirm no active extraction/backfill/runtime job overlaps these document IDs.
- Run `scripts/gpu_process_guard.sh --check`.
- Confirm backend health at `/api/health`.
- Confirm the live backend and worker are serving the intended commit or a
  documented descendant.
- Confirm each source path still exists and no source PDF sidecar will be
  written.
- Confirm no candidate is queued/running/orphaned.
- Confirm the command path is only
  `POST /api/process/document/{document_id}` for the seven approved IDs.
- Submit one document at a time and stop on the first failed hard gate, source
  side effect, queue orphan, or unexpected datastore effect.

## Expected Future Command Shape

Use the existing backend-owned single-document route only:

```bash
curl -sS -X POST "http://127.0.0.1:8000/api/process/document/${DOCUMENT_ID}" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: ${LOCAL_API_KEY}" \
  -d '{"method":"auto","strict_method":false}'
```

Do not use `/process/ticker`, a bulk route, a direct Celery enqueue, direct SQL,
or any broad backfill command.

## Scorecard And Review Gates

After any approved run produces actual payloads:

- Build #97 confirmed-metric payload actuals and run the pre-persistence
  scorecard gate before any promotion decision.
- Apply #98 metric ontology/contract parity before interpreting unsupported or
  persisted-only metric families.
- Keep #99 source asset reviewability separate from metric correctness.
- Treat `ok_low_confidence` rows as native-currency/no-FX review items, not
  cross-currency comparable facts.

## DATA_MISSING

- Operator approval for this exact packet.
- Live DB terminal state for these candidates immediately before execution.
- Queue/scheduler ownership immediately before execution.
- Runtime loaded-code proof immediately before execution.
- Future actual payloads and #97 scorecard results.
- Full graduation evidence for broad accurate extraction.

## Validation

Passed:

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/extraction_third_canary_approval_packet_refresh_v1_20260529.md`
- `python3 scripts/agent_job_registry.py list-active --read-only`: no active jobs before claim.
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/extraction_third_canary_approval_packet_refresh_v1_20260529.md --repo-root .`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/extraction_third_canary_approval_packet_refresh_v1_20260529.md --repo-root .`
- Current source-path existence checks for all seven eligible candidates and the three excluded prior-primary candidates.
- Current source-document title classification check: PLS and SFR classify as `advisory_only_document`; the seven carried candidates are canary-candidate allowed by title-only policy.
- `python3 -m json.tool` for `canary_approval_packet.json`, `status.json`, and `diff-check.json`.
- CSV field-count sanity check: `11` rows, `14` fields.
- Packet/CSV consistency check: `packet_csv_consistency ok`.
- `git diff --check` and `git diff --cached --check`.
- Raw PDF/source-data staging check: no source PDF or source-data paths staged.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/extraction_third_canary_approval_packet_refresh_v1_20260529.md --repo-root .`
- Code-reviewer pass over the report-only diff: no critical, warning, or suggestion findings.

## Files Changed

- `docs/agent_tasks/extraction_third_canary_approval_packet_refresh_v1_20260529.md`
- `reports/agent_jobs/extraction_third_canary_approval_packet_refresh_v1_20260529/README.md`
- `reports/agent_jobs/extraction_third_canary_approval_packet_refresh_v1_20260529/canary_approval_packet.json`
- `reports/agent_jobs/extraction_third_canary_approval_packet_refresh_v1_20260529/canary_candidates.csv`
- `reports/agent_jobs/extraction_third_canary_approval_packet_refresh_v1_20260529/status.json`
- `reports/agent_jobs/extraction_third_canary_approval_packet_refresh_v1_20260529/diff-check.json`
- `docs/claude/STATE.md`

## Files Intentionally Not Touched

- Production DB, Qdrant, news, memory, and canonical financial truth stores.
- Source PDFs and source-data fixtures.
- Parser routing and extraction prompts.
- Runtime/model/GPU/service configuration.
- Cockpit UI.
- Schema and Alembic migrations.
- GitHub issue state.

## Next Safe Step

Wait for exact operator approval. If approved, create a new approval-required
runtime task card for the seven-document third canary, rerun all immediate
pre-run gates, then submit one document at a time through the backend route.
