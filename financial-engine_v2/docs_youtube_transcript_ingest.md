# YouTube Transcript Ingest (Model Strategy DB)

This workflow pulls transcript text from YouTube videos and stores the results in a local strategy database index for model-iteration research.

## What it creates

- `data/model_strategy/youtube_transcripts/<video_id>.json`  
  Full metadata + timestamped transcript segments.
- `data/model_strategy/youtube_transcripts/<video_id>.md`  
  Human-readable transcript artifact for review.
- `data/model_strategy/youtube_transcripts_index.json`  
  Aggregated index used as the strategy database catalog.

## Run

```bash
python3 scripts/youtube_transcript_strategy_ingest.py \
  --url "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
```

Bulk ingest from seed file:

```bash
python3 scripts/youtube_transcript_strategy_ingest.py \
  --input-file data/model_strategy/youtube_seed_urls.txt
```

## Seed file format

One URL or video ID per line:

```text
# comments are ignored
https://www.youtube.com/watch?v=abcdefghijk
https://youtu.be/lmnopqrstuv
wxyz1234567
```

## Notes

- Existing indexed videos are skipped unless `--overwrite` is supplied.
- Language priority defaults to `en,en-US`; override with `--languages`.
- The transcript API may fail for videos with disabled transcripts or unavailable captions.
