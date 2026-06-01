# YouTube Transcription Strategy Memory Audit

Issue: https://github.com/0rl4nd0l/tenn/issues/100

## Result

Audit complete. The current code has most ingestion and review primitives, but
the end-to-end YouTube-to-strategy-memory workflow is not proven live and does
not yet expose a dedicated Home memory-commit queue.

## Key Findings

- Implemented: `run_transcript_daemon.py` constructs both `TranscriptWatcher`
  and `YoutubeTranscriptFetcher`, then calls watcher and YouTube polling in the
  loop.
- Implemented: YouTube URL ingest, channel registration/listing/recent-video
  preview, transcript staging, deterministic takeaways, review edit/weight, and
  approve/reject endpoints exist under backend commentary APIs.
- Implemented: user thesis memory has proposal states `pending`, `confirmed`,
  `rejected`, and `applied`; Memory UI can create, confirm, reject, and apply
  thesis proposals.
- Implemented: Home source detail can fetch commentary takeaways for a selected
  source via the Cockpit BFF proxy.
- Not proven live: backend health returned connection refused, no transcript
  daemon or YouTube poller process was visible, and no systemd user service for
  transcript polling was visible.
- Stale documentation: `docs/ops/youtube_channel_watch_verification.md` still
  says the daemon does not construct `YoutubeTranscriptFetcher`, which conflicts
  with current code.
- Missing product workflow: no current evidence routes YouTube takeaways into a
  dedicated pending memory-commit queue on Home before strategy-memory mutation.

## Recommendation

Use existing user-thesis proposals for speculative and strategy-mutating
takeaways. Do not add a separate speculative memory store until the proposal
queue has been exercised. Company/market memory can receive non-numeric factual
signals only through existing backend memory contracts, with explicit
provenance and no financial-truth writes.

## Existing Follow-Ups

- #101: persist YouTube source metadata and transcript timing through
  commentary chunks.
- #102: add YouTube intake quality gates for low-signal and speculative
  transcripts.
- #103: add Home memory-candidate queue for commentary takeaways.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/youtube_transcription_strategy_memory_audit_v1_20260526.md`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/youtube_transcription_strategy_memory_audit_v1_20260526.md --repo-root .`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/youtube_transcription_strategy_memory_audit_v1_20260526.md --repo-root .`
- Read-only repo inspection with `rg` and `sed`
- Read-only runtime probes with `ps`, `curl`, and `systemctl --user list-units`
- `git diff --check`
- `jq` validation for report JSON artifacts
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/youtube_transcription_strategy_memory_audit_v1_20260526.md`
