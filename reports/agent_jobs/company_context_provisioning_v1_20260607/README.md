# Company Context Provisioning V1 Report

Status: DONE_WITH_RISK
Date: 2026-06-07
Task card: `docs/agent_tasks/company_context_provisioning_v1_20260607.md`
Worktree: `/home/l4nd0/tenn-company-context-provisioning-v1-20260607`
Branch: `safe/company-context-provisioning-v1-20260607`
Baseline: `origin/main` at `7443d9f248346210ada834e1fd19ab923ace192f`

## Scope

This slice treats the missing Cockpit company qualitative-context DB as a
required production artifact. It does not add degraded startup behavior and it
does not create a partial production DB to satisfy startup.

## Current Evidence

- Live dirty checkout preserved:
  `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`.
- Clean sibling worktree used for implementation:
  `/home/l4nd0/tenn-company-context-provisioning-v1-20260607`.
- Production news artifact root currently contains:
  `/mnt/tenn-nvme2/tenn/financial-engine_v2/reports/qual_context/news.sqlite`
  with 4,397 `context_chunks`.
- Production company DB is still absent:
  `/mnt/tenn-nvme2/tenn/financial-engine_v2/reports/qual_context/company.sqlite`
  does not exist.
- Clean worktree repo-local company DB is absent:
  `reports/qual_context/company.sqlite` does not exist.
- Repo-local `financial-engine_v2/data/asx/docs` is absent in this worktree.
- NVMe source corpus exists but is large:
  `/mnt/tenn-nvme2/tenn/financial-engine_v2/data/asx/docs` has 179,016 PDFs
  and totals 152G.
- GPU discovery is broken:
  `nvidia-smi --query-gpu=name,pci.bus_id,memory.total --format=csv,noheader`
  returned `Unable to determine the device handle for GPU0000:25:00.0: Unknown Error`.

## Code Changes

- `AGENTS.md`
  - Added a repo rule that safe-installable missing Python/runtime dependencies
    should be installed or repaired in the project/runtime venv and recorded,
    rather than hidden behind degraded behavior.
- `financial-engine_v2/cockpit/core/config.py`
  - Added company DB env override handling:
    `COCKPIT_COMPANY_DB_PATH`, `TENN_COMPANY_CONTEXT_DB`, and
    `TENN_QUAL_CONTEXT_ARTIFACT_ROOT/company.sqlite`.
- `financial-engine_v2/cockpit/integrations/qual_context_bootstrap.py`
  - Added company-context path resolution that preserves explicit absolute
    paths and prefers the production artifact root for the default relative
    `reports/qual_context/company.sqlite`.
- `financial-engine_v2/cockpit/ui/app.py`
  - Uses the company-specific resolver for the company qualitative-context DB.
- `financial-engine_v2/scripts/test_cockpit_company_context_path.py`
  - Covers company DB override priority and default artifact-root resolution.

## Dependency Repair

User approval was provided to install missing dependencies when safely needed.
Repairs were made in the existing runtime venv:
`/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/financial-engine_v2/.venv`.

Commands run:

```bash
/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/financial-engine_v2/.venv/bin/python \
  -m pip install --force-reinstall --no-cache-dir \
  --index-url https://download.pytorch.org/whl/cpu \
  torch==2.2.2+cpu torchvision==0.17.2+cpu

/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/financial-engine_v2/.venv/bin/python \
  -m pip install --force-reinstall --no-cache-dir transformers==4.57.6

/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/financial-engine_v2/.venv/bin/python \
  -m pip install --force-reinstall --no-cache-dir \
  numpy==1.26.4 packaging==24.2 requests==2.32.4
```

Validation:

```text
torch 2.2.2+cpu cuda False devices 0
torchvision 0.17.2+cpu
transformers 4.57.6
sentence_transformers 3.4.1
numpy 1.26.4
packaging 24.2
requests 2.32.4
pip check: No broken requirements found.
```

BGE model load also succeeded on CPU:
`SentenceTransformer('BAAI/bge-large-en-v1.5', device='cpu')`; encoding one
sentence returned a 1-row, 1024-dimension embedding.

## Temp Artifact Validation

Hash backend bounded build:

- Output: `/tmp/tenn-company-context-temp-O114Sd/out/company.sqlite`.
- SQLite table: `context_chunks`.
- Chunks: 118.
- Companies: BHP 88, CBA 30.
- Manifest file:
  `/tmp/tenn-company-context-temp-O114Sd/out/company_manifest.json`.
- Manifest output included:
  `db=sqlite`, `corpus=company`, `embed_backend=hash`,
  `embed_model=bge-large-en-v1.5`, `chunks_written=118`,
  `query_result_count=3`.

Sentence-transformers BGE bounded build:

- Output: `/tmp/tenn-company-context-bge-temp-iftymZ/out/company.sqlite`.
- SQLite table: `context_chunks`.
- Chunks: 118.
- Companies: BHP 88, CBA 30.
- Representative embedding payload length: 22,731 characters.
- Manifest file:
  `/tmp/tenn-company-context-bge-temp-iftymZ/out/company_manifest.json`.
- Manifest output included:
  `db=sqlite`, `corpus=company`,
  `embed_backend=sentence-transformers`,
  `embed_model=BAAI/bge-large-en-v1.5`, `chunks_written=118`,
  `query_result_count=3`.

Cockpit startup smoke with temp BGE company DB:

```bash
TERM=xterm-256color \
COCKPIT_COMPANY_DB_PATH=/tmp/tenn-company-context-bge-temp-iftymZ/out/company.sqlite \
/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/financial-engine_v2/.venv/bin/python \
  -m cockpit.main --read-only --no-web
```

Result: Cockpit reached the UI and exited with code 0 after `q`. This proves
the code path can start when a real company DB is supplied. It is not production
DB provisioning evidence.

## Validation Commands

```bash
python3 financial-engine_v2/scripts/test_cockpit_company_context_path.py
python3 financial-engine_v2/scripts/test_cockpit_news_context_path.py
python3 financial-engine_v2/scripts/test_cockpit_news_qual_context.py
python3 -m py_compile \
  financial-engine_v2/cockpit/core/config.py \
  financial-engine_v2/cockpit/integrations/qual_context_bootstrap.py \
  financial-engine_v2/cockpit/ui/app.py \
  financial-engine_v2/scripts/test_cockpit_company_context_path.py
git diff --check
```

All commands above passed after this report was added.

Task-card validation status:

```text
DATA_MISSING: scripts/agent_job_contract.py absent in clean baseline
```

## Unsafe Actions Avoided

- Did not modify or clean the dirty live checkout.
- Did not create or copy a stale DB into production artifact paths.
- Did not write Qdrant, Redis, source PDFs, extraction truth data, prompts,
  migrations, Docker/runtime config, crontab, timers, symlinks, or host env
  files.
- Did not start Cockpit in degraded mode.
- Did not attempt a full 179,016-PDF production BGE build on CPU while GPU
  discovery is broken.

## Remaining Blocker

The system is closer to production readiness because dependency repair, company
artifact-root resolution, and temp DB startup validation are proven. It is not
fully production-ready because no production `company.sqlite` has been built at
`/mnt/tenn-nvme2/tenn/financial-engine_v2/reports/qual_context/company.sqlite`.

The next safe production step is to repair GPU/runtime compute or explicitly
approve a managed long-running production builder plan. After a real production
DB exists, validate nonzero chunks, schema, representative retrieval, and normal
Cockpit startup with no temp override.
