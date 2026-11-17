# Architecture Map

## Current Path

1. Channel discovery and registration
   - Backend commentary API exposes channel registration, channel listing, and
     recent-video preview routes.
   - `YoutubeTranscriptFetcher` uses `ChannelRegistry.enabled_channels()` and
     `yt-dlp` video listing helpers.

2. Transcript fetch and staging
   - `YoutubeTranscriptFetcher.poll_once()` fetches transcripts for recent
     channel videos and writes drop files through `TranscriptProcessor`.
   - Manual URL ingest also fetches metadata/transcripts and stages transcript
     chunks.
   - Staging writes reviewable chunks under the commentary staging path; staged
     chunks are not automatically approved into Qdrant.

3. Review and approval
   - `/api/commentary/transcripts/pending` lists staged items.
   - `/api/commentary/transcripts/{source_id}/review` lets operators adjust
     credibility and review takeaways.
   - `/api/commentary/transcripts/{source_id}/approve` upserts reviewed points
     into backend-owned Qdrant commentary collections.
   - `/api/commentary/transcripts/{source_id}/reject` removes staged material.

4. Takeaways and UI exposure
   - `/api/commentary/takeaways` returns deterministic takeaways, generated
     takeaways, review takeaways, outline, credibility weight, and watchlist
     suggestions for staged or memo-backed commentary sources.
   - Cockpit chat and Home source detail call the Next.js BFF proxy at
     `/api/cockpit/commentary/takeaways`.
   - Home currently shows source-detail takeaways for selected sources, not a
     dedicated queue of memory-commit candidates.

5. Memory writes
   - Company memory and market memory are qualitative stores and reject
     financial metric signal types.
   - User thesis memory is confirmation-gated through proposal, confirm, and
     apply.
   - The Memory UI can create, confirm, reject, and apply thesis proposals.
   - No current evidence shows YouTube takeaways are routed into this proposal
     queue automatically.

## Classification Policy

- Factual company/market takeaway:
  - Non-numeric, evidence-bound, non-speculative, and scoped to a company,
    sector, or macro topic.
  - Candidate route: existing company/market memory contracts after quality and
    provenance gates pass.

- Speculative takeaway:
  - Uses forecast, opinion, possibility, valuation thesis, or unverified causal
    language.
  - Candidate route: user-thesis proposal with status `pending`; never direct
    company/market memory.

- Strategy-mutating takeaway:
  - Changes or supports a user investment thesis, action, risk posture, or
    monitoring plan.
  - Candidate route: user-thesis proposal only; requires explicit confirm/apply
    before it becomes strategy memory.

- Financial-truth claim:
  - Numeric financial metric, reported canonical value, inferred metric, or
    canonical-period fact.
  - Candidate route: no memory write from YouTube commentary. It can remain
    cited commentary context but must not become canonical financial truth.

## Home Queue Shape

Home should expose pending YouTube/commentary memory candidates as a backend-owned
queue with:

- source id, source URL, channel, video title, published time, transcript method,
  chunk/timestamp citation, and confidence;
- classification: factual, speculative, strategy-mutating, or rejected;
- action controls: confirm, reject, edit, downgrade to speculative, or apply to
  strategy memory only after confirmation;
- `DATA_MISSING` state when provenance or runtime evidence is incomplete.

## Documentation Reconciliation

`docs/ops/youtube_channel_watch_verification.md` contains stale statements that
the daemon only wires `TranscriptWatcher` and does not construct
`YoutubeTranscriptFetcher`. Current code imports and constructs
`YoutubeTranscriptFetcher`, then calls `_poll_youtube_once()` in both one-shot
and loop modes. The doc should be updated after runtime service ownership is
proved.
