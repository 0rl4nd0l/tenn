# News Context Path Alignment v1 - 2026-06-07

## Status

DONE_WITH_RISK

## Scope

Task card: `docs/agent_tasks/news_context_path_alignment_v1_20260607.md`

Clean worktree:
`/home/l4nd0/tenn-news-context-path-alignment-v1-20260607`

Baseline:
`origin/main` at `5d7b8d6a01bf534c611598923c5dd3c1905a59bc`

## Current-Turn Evidence

Cockpit `repo_root` is `financial-engine_v2` from
`financial-engine_v2/cockpit/main.py`.

Default Cockpit config uses:

```text
rag.news_context.db_path=reports/qual_context/news.sqlite
```

Before this change, the resolver selected the stale repo-local ignored DB:

```text
/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/reports/qual_context/news.sqlite
context_chunks=915
max_published_at=2026-05-27T00:00:00Z
```

The successful nightly cron validation produced the fresher DB at:

```text
/mnt/tenn-nvme2/tenn/financial-engine_v2/reports/qual_context/news.sqlite
context_chunks=4397
max_published_at=2026-06-04T00:00:00Z
```

After this change, a default resolver smoke returned:

```text
/mnt/tenn-nvme2/tenn/financial-engine_v2/reports/qual_context/news.sqlite
exists True
```

## Changes

- `financial-engine_v2/cockpit/core/config.py`
  - Keeps `COCKPIT_NEWS_DB_PATH` as highest-priority Cockpit override.
  - Adds support for the nightly wrapper surfaces:
    `TENN_NEWS_CONTEXT_DB` and `TENN_NEWS_ARTIFACT_ROOT/news.sqlite`.

- `financial-engine_v2/cockpit/integrations/qual_context_bootstrap.py`
  - Adds default news context path constants.
  - For the default relative `reports/qual_context/news.sqlite`, chooses the
    newest existing file among the nightly artifact-root DB and repo-local
    default candidates.
  - Leaves explicit absolute DB paths deterministic.

- `financial-engine_v2/scripts/test_cockpit_news_context_path.py`
  - Covers env precedence and fresher artifact-root selection with temp files.

## Validation

```text
python3 financial-engine_v2/scripts/test_cockpit_news_context_path.py
exit 0
Ran 5 tests in 0.002s
OK
```

```text
python3 financial-engine_v2/scripts/test_cockpit_news_qual_context.py
exit 0
Ran 2 tests in 0.020s
OK
```

```text
python3 - <<'PY'
from pathlib import Path
import sys
sys.path.insert(0, str(Path('financial-engine_v2').resolve()))
from cockpit.integrations.qual_context_bootstrap import resolve_news_context_db_path
rag_cfg={'news_context': {'enabled': True, 'db_path': 'reports/qual_context/news.sqlite'}}
p=resolve_news_context_db_path(repo_root=Path('/home/l4nd0/tenn/financial-engine_v2'), rag_cfg=rag_cfg)
print(p)
print('exists', p.exists() if p else None)
PY
exit 0
/mnt/tenn-nvme2/tenn/financial-engine_v2/reports/qual_context/news.sqlite
exists True
```

```text
git diff --check
exit 0
```

Task-card validator:

```text
DATA_MISSING: scripts/agent_job_contract.py is absent from merged origin/main.
```

Task-card check-diff:

```text
DATA_MISSING: scripts/agent_job_contract.py is absent from merged origin/main.
```

## Unsafe Actions Avoided

- Did not edit crontab, timers, host env files, Docker runtime config, or
  symlinks.
- Did not run live ingestion during this task.
- Did not mutate Qdrant, Redis, production DBs, memory stores, source PDFs, gold
  labels, extraction prompts, parser routing, model/GPU config, backfills, or
  migrations.
- Did not clean or modify the dirty live checkout.
- Did not push, merge, or mutate GitHub.

## Remaining Risk

This fixes path selection, not source relevance. The latest successful bounded
nightly run inserted one Guardian article and had `entity_link_filtered=1`, so
news source relevance and ticker linking remain separate quality risks.

## Next Recommended Prompt

Review and merge the local branch
`safe/news-context-path-alignment-v1-20260607`, then deploy the same resolver
change to the live checkout and start Cockpit once to confirm the startup notice
shows the `/mnt/tenn-nvme2/.../news.sqlite` path.
