# Health Snapshot Artifact Paths V1 Report

Status: DONE_WITH_RISK
Date: 2026-06-07
Task card: `docs/agent_tasks/health_snapshot_artifact_paths_v1_20260607.md`
Worktree: `/home/l4nd0/tenn-health-snapshot-artifact-paths-v1-20260607`
Branch: `safe/health-snapshot-artifact-paths-v1-20260607`
Baseline: `origin/main` at `7443d9f248346210ada834e1fd19ab923ace192f`

## Scope

This slice fixes a health-signal path mismatch. It does not build, copy, or
promote any SQLite DB artifacts.

## Current Evidence

- Production news DB exists:
  `/mnt/tenn-nvme2/tenn/financial-engine_v2/reports/qual_context/news.sqlite`
  size `27791360`.
- Production company DB is still absent:
  `/mnt/tenn-nvme2/tenn/financial-engine_v2/reports/qual_context/company.sqlite`.
- Live news DB corpus inventory:
  `news_newspaper4k=4397`.
- Before this fix, the snapshot default path was repo-local and the default
  exact `news` corpus filter would count zero rows for the live provider corpus.

## Changes

- `scripts/generate_engine_health_snapshot.py`
  - Defaults news/company DB paths to
    `/mnt/tenn-nvme2/tenn/financial-engine_v2/reports/qual_context`.
  - Preserves explicit CLI `--news-db-path` and `--company-db-path`.
  - Adds env default support aligned with Cockpit/news routing:
    `COCKPIT_NEWS_DB_PATH`, `TENN_NEWS_CONTEXT_DB`,
    `TENN_NEWS_ARTIFACT_ROOT`, `COCKPIT_COMPANY_DB_PATH`,
    `TENN_COMPANY_CONTEXT_DB`, and `TENN_QUAL_CONTEXT_ARTIFACT_ROOT`.
  - Treats default `news` as the news family:
    `corpus='news' OR corpus GLOB 'news_*'`.
  - Keeps explicit non-default `--news-corpus` exact.
  - Opens context/core SQLite databases with read-only SQLite URI connections.
  - Makes missing company DBs/tables/zero chunks visible through
    `company_rag.drift_flags` and includes them in warning status.
  - Makes `parse_args()` and `main()` accept optional argv for focused tests.
- `scripts/test_generate_engine_health_snapshot.py`
  - Adds tests for production-root defaults, env priority, CLI override, and
    provider-specific news corpora.
  - Adds a negative test that explicit non-default news corpus filters remain
    exact.
  - Adds regressions for missing company DB status, literal `news_` matching,
    and read-only SQLite missing-file behavior.

## Validation

```bash
python3 scripts/test_generate_engine_health_snapshot.py
python3 -m py_compile scripts/generate_engine_health_snapshot.py scripts/test_generate_engine_health_snapshot.py
git diff --check
python3 scripts/generate_engine_health_snapshot.py --out-json /tmp/.../health.json
```

Results:

```text
test_generate_engine_health_snapshot.py: Ran 12 tests, OK
py_compile: passed
git diff --check: passed
temp health run: exit 0
sidecar check: no news/company `-wal` or `-shm` files before or after temp run
```

Temp health run evidence:

```text
overall_status=warning
news_db_path=/mnt/tenn-nvme2/tenn/financial-engine_v2/reports/qual_context/news.sqlite
news_chunks=4397
news_max_doc_date=2026-06-04
company_db_exists=False
company_missing_db=True
company_chunks=0
```

Task-card validator:

```text
DATA_MISSING: scripts/agent_job_contract.py absent in clean main
```

## Unsafe Actions Avoided

- Did not write or copy `company.sqlite` or `news.sqlite`.
- Did not mutate Qdrant, Redis, source PDFs, runtime service config, crontab,
  timers, Docker config, or the dirty live checkout.
- Did not merge or close PRs.

## Remaining Gate

This improves health truthfulness, but the system remains incomplete because
the production company DB is still absent and PRs #314/#315 are still unmerged.
After this PR lands, health snapshots should inspect the same context artifact
root as Cockpit and nightly news by default.
