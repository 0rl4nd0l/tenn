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
