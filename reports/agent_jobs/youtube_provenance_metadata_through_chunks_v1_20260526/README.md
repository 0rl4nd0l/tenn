# YouTube Provenance Metadata Through Chunks

Issue: https://github.com/0rl4nd0l/tenn/issues/101

## Outcome

Implemented a safe Provenance-lane extension so YouTube video provenance and transcript segment timing survive the backend commentary path:

- URL ingestion passes `video_id`, `webpage_url`, and transcript segment timing into `ingest_transcript()`.
- Monitored-channel ingestion writes and re-reads the same provenance through transcript drop-file front matter.
- Staged commentary chunk payloads include nullable `video_id`, `webpage_url`, `segment_start_seconds`, and `segment_end_seconds`.
- Approval preserves staged payload fields when backend-owned approval upserts to Qdrant.
- Takeaway citations return the provenance fields when present and `null` when absent.

## Scope Correction

A read-only contract-enforcer pass blocked the original URL-only implementation scope because full issue #101 also covers monitored YouTube channel ingestion. The task card was corrected before product edits to include `transcript_watcher.py` and the focused staging test file. The corrected task card passed validation and registry overlap checks before implementation resumed.

## Safety

- No production DB, Qdrant, news, or memory stores were mutated.
- The staged transcript review gate remains intact; hot YouTube chunks are still staged, not auto-approved.
- Canonical financial truth, extraction prompts, parser routing, gold labels, runtime/model/GPU/service config, and UI files were not touched.
- Segment timing is used for chunk construction only when normalized segment text matches the cleaned transcript text; otherwise existing full-transcript chunking wins with nullable timing fields.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/youtube_provenance_metadata_through_chunks_v1_20260526.md` - passed
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/youtube_provenance_metadata_through_chunks_v1_20260526.md --repo-root .` - passed
- `PYTHONPATH=financial-engine_v2/backend uv run --python 3.10 --with-requirements financial-engine_v2/backend/requirements.txt --with-requirements financial-engine_v2/backend/requirements-dev.txt python -m ruff check financial-engine_v2/backend/app/services/youtube_transcript_fetcher.py financial-engine_v2/backend/app/services/transcript_watcher.py financial-engine_v2/backend/app/services/commentary_ingest.py financial-engine_v2/backend/app/api/commentary.py financial-engine_v2/backend/tests/test_youtube_transcript_fetcher.py financial-engine_v2/backend/tests/test_qdrant_resolution.py financial-engine_v2/backend/tests/test_commentary_endpoints.py financial-engine_v2/backend/tests/test_commentary_takeaways_endpoint.py` - passed
- `PYTHONPATH=financial-engine_v2/backend uv run --python 3.10 --with-requirements financial-engine_v2/backend/requirements.txt --with-requirements financial-engine_v2/backend/requirements-dev.txt python -m pytest financial-engine_v2/backend/tests/test_youtube_transcript_fetcher.py financial-engine_v2/backend/tests/test_qdrant_resolution.py financial-engine_v2/backend/tests/test_commentary_endpoints.py financial-engine_v2/backend/tests/test_commentary_takeaways_endpoint.py -q` - 116 passed
- `git diff --check` - passed
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/youtube_provenance_metadata_through_chunks_v1_20260526.md` - passed
