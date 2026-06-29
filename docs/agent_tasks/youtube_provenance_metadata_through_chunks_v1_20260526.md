---
job_id: youtube_provenance_metadata_through_chunks_v1_20260526
lane: Provenance
supporting_lanes:
  - Memory
  - Query Orchestration
  - Reporting
owner: Codex
allowed_files:
  - docs/agent_tasks/youtube_provenance_metadata_through_chunks_v1_20260526.md
  - financial-engine_v2/backend/app/services/youtube_transcript_fetcher.py
  - financial-engine_v2/backend/app/services/transcript_watcher.py
  - financial-engine_v2/backend/app/services/commentary_ingest.py
  - financial-engine_v2/backend/app/api/commentary.py
  - financial-engine_v2/backend/tests/test_youtube_transcript_fetcher.py
  - financial-engine_v2/backend/tests/test_qdrant_resolution.py
  - financial-engine_v2/backend/tests/test_commentary_endpoints.py
  - financial-engine_v2/backend/tests/test_commentary_takeaways_endpoint.py
  - reports/agent_jobs/youtube_provenance_metadata_through_chunks_v1_20260526/
  - reports/agent_jobs/youtube_provenance_metadata_through_chunks_v1_20260526/README.md
  - reports/agent_jobs/youtube_provenance_metadata_through_chunks_v1_20260526/status.json
  - reports/agent_jobs/youtube_provenance_metadata_through_chunks_v1_20260526/validation.json
  - reports/agent_jobs/youtube_provenance_metadata_through_chunks_v1_20260526/diff-check.json
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/youtube_provenance_metadata_through_chunks_v1_20260526
mutation_mode: safe_extension
production_data_access: false
---

# YouTube Provenance Metadata Through Chunks

Issue: https://github.com/0rl4nd0l/tenn/issues/101

## Objective

Preserve YouTube video and timestamp provenance through staged commentary chunks,
approval, and takeaway citation payloads without changing financial truth or
bypassing the transcript review gate.

## Allowed Scope

- Add nullable YouTube provenance fields to commentary transcript staging payloads.
- Extend the transcript watcher metadata bridge so monitored-channel YouTube
  drop files preserve the same nullable provenance fields before review.
- Capture transcript segment timing before timestamp prefixes are stripped from
  cleaned text.
- Preserve backward compatibility for existing staged JSONL files without those
  fields.
- Surface provenance in deterministic takeaway citations when present.
- Add focused backend tests for propagation and backward compatibility.

## Forbidden Scope

- No production DB, Qdrant, news, or memory writes.
- No canonical financial truth, parser routing, extraction prompts, gold labels,
  runtime/model/GPU/service config, UI, or broad retrieval changes.
- No bypass of staged transcript review or automatic hot-source Qdrant approval.

## Acceptance Criteria

- Staged YouTube chunks preserve nullable `video_id`, `webpage_url`,
  `segment_start_seconds`, and `segment_end_seconds` where available.
- Existing staged JSONL without these fields remains readable.
- Approved commentary chunks retain the same fields through the backend-owned
  approval path.
- Takeaway/citation payloads surface video/timestamp provenance when present
  and return `null` when absent.
- Tests cover propagation and backward compatibility.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/youtube_provenance_metadata_through_chunks_v1_20260526.md`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/youtube_provenance_metadata_through_chunks_v1_20260526.md --repo-root .`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/youtube_provenance_metadata_through_chunks_v1_20260526.md --repo-root .`
- `PYTHONPATH=financial-engine_v2/backend uv run --python 3.10 --with-requirements financial-engine_v2/backend/requirements.txt --with-requirements financial-engine_v2/backend/requirements-dev.txt python -m pytest financial-engine_v2/backend/tests/test_youtube_transcript_fetcher.py financial-engine_v2/backend/tests/test_qdrant_resolution.py financial-engine_v2/backend/tests/test_commentary_endpoints.py financial-engine_v2/backend/tests/test_commentary_takeaways_endpoint.py -q`
- `PYTHONPATH=financial-engine_v2/backend uv run --python 3.10 --with-requirements financial-engine_v2/backend/requirements.txt --with-requirements financial-engine_v2/backend/requirements-dev.txt python -m ruff check financial-engine_v2/backend/app/services/youtube_transcript_fetcher.py financial-engine_v2/backend/app/services/transcript_watcher.py financial-engine_v2/backend/app/services/commentary_ingest.py financial-engine_v2/backend/app/api/commentary.py financial-engine_v2/backend/tests/test_youtube_transcript_fetcher.py financial-engine_v2/backend/tests/test_qdrant_resolution.py financial-engine_v2/backend/tests/test_commentary_endpoints.py financial-engine_v2/backend/tests/test_commentary_takeaways_endpoint.py`
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/youtube_provenance_metadata_through_chunks_v1_20260526.md`
