# News baseline policy

The canonical news context DB is guarded by a **committed baseline** and **drift detection** in CI.

## Baseline location

- **Path:** `reports/qual_context/news_baseline.json`
- **Committed:** Yes. The file is in git so CI can run drift detection without building the DB.

## When to update the baseline

Update only after a **deliberate full rebuild** and verification:

1. Rebuild and verify:
   ```bash
   python3 scripts/run_news_pipeline.py --full-rebuild --newspaper4k-jsonl default --verify
   ```
2. Save the new baseline:
   ```bash
   python3 scripts/detect_news_context_drift.py --save-baseline
   ```
3. Commit with a clear message:
   ```bash
   git add -f reports/qual_context/news_baseline.json
   git commit -m "chore(news): update baseline after rebuild"
   ```
   Use `-f` if `reports/` is in `.gitignore` or `.git/info/exclude` so the baseline can be tracked.

Do **not** update the baseline on every run. Only after a known-good full refresh when you intend to lock in counts and content hashes.

## CI enforcement

- **Workflow:** `.github/workflows/backend-ci.yml` job `news-substrate`
- **Baseline required:** CI fails if `reports/qual_context/news_baseline.json` is missing.
- **Drift:** When `reports/qual_context/news.sqlite` exists (e.g. from a prior artifact or local run), CI runs `detect_news_context_drift.py`. Drift (missing corpus, large drops, or hash mismatches) fails the job.
- **Schema:** CI validates a minimal JSONL fixture with `validate_news_jsonl_schema.py`.

## Drift defaults

- **New corpora:** Allowed by default (additive). Use `--fail-on-new-corpus` for strict releases.
- **Missing baseline corpus:** Fails by default. Use `--no-fail-on-missing-corpus` to allow.
- **Corpus count drop:** Fails when any baseline corpus drops by more than `--tolerance-pct` (default 25%).
- **Content hashes:** Baseline stores `chunk_id_sample_hash`, `doc_id_sample_hash`, `top_sources_hash`. Mismatch fails drift (same count but different content).

See `docs/architecture/15_news_substrate.md` and `scripts/detect_news_context_drift.py --help`.

## Nightly Runtime Guard

`financial-engine_v2/scripts/nightly_news.sh` is allowed to fetch daily RSS
articles, then sync them into Qdrant and `news.sqlite`. The wrapper must not
report a successful nightly run when the downstream sync cannot happen.

- Missing backend venv is a hard failure. Fetch-only is not a successful
  nightly automation result.
- Before live sync, the wrapper checks `NIGHTLY_NEWS_QDRANT_URL` or `QDRANT_URL`
  (default `http://127.0.0.1:6333`).
- If Qdrant is unavailable and `NIGHTLY_NEWS_QDRANT_AUTO_START=1` (default),
  the wrapper may start only the existing
  `NIGHTLY_NEWS_QDRANT_CONTAINER` (default `fe_qdrant`) and wait up to
  `NIGHTLY_NEWS_QDRANT_START_TIMEOUT_SECONDS` (default `45`).
- The sync summary must show `qdrant_sync.status=success`,
  `qdrant_sync.qdrant_diff.status=available`, and
  `sqlite_fallback.status=success`.
- The wrapper must not create containers, run Docker Compose, delete or recreate
  Qdrant collections, wipe DBs, broad reindex, or change cron/systemd/service
  configuration.
