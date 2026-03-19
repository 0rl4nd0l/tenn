# Non-Destructive Optimization and Traceability

This workflow optimizes workspace responsiveness without deleting or offloading PDFs/system data.

## Guarantees

- No file deletion.
- No file moves/renames.
- Protected corpora stay in place:
  - `financial-engine_v2/data/asx/docs`
  - `financial-engine_v2/data/marketindex/pdfs`
  - `reports/qual_context`
  - `reports/review_packs`

## What was optimized

- Search/index excludes were added for heavy generated trees:
  - `.ignore`
  - `.rgignore`
  - `.fdignore`
  - `.vscode/settings.json` (`files.watcherExclude`, `search.exclude`)
- These settings only reduce indexing/watcher load. They do not change filesystem contents.

## Traceability Guard Workflow

Use `scripts/protected_data_guard.py` to snapshot and verify protected data integrity.

Create baseline:

```bash
python3 scripts/protected_data_guard.py snapshot \
  --baseline reports/traceability/protected_data_baseline.json \
  --hash-mode sample
```

Verify against baseline (fails on missing/changed files):

```bash
python3 scripts/protected_data_guard.py verify \
  --baseline reports/traceability/protected_data_baseline.json \
  --write-current reports/traceability/protected_data_current.json
```

Strict mode (also fail on newly added files):

```bash
python3 scripts/protected_data_guard.py verify \
  --baseline reports/traceability/protected_data_baseline.json \
  --strict-new
```

## Hash mode guidance

- `metadata`: fastest (size + mtime only).
- `sample`: recommended default (size + first/last 64KiB hash).
- `full`: strongest integrity signal (full SHA256 for every file).
