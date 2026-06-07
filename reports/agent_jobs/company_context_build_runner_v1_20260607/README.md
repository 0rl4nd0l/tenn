# Company Context Build Runner V1 Report

Status: DONE_WITH_RISK
Date: 2026-06-07
Task card: `docs/agent_tasks/company_context_build_runner_v1_20260607.md`
Worktree: `/home/l4nd0/tenn-company-context-runner-v1-20260607`
Branch: `safe/company-context-runner-v1-20260607`
Stacked on: PR #314 head `2dd0d131ee6c614ad9f36edd5251655e7064bca6`

## Scope

This slice adds a fail-closed runner for the missing production
`company.sqlite` artifact. It does not build or promote the real production DB.
The point is to remove the next ad hoc operator step: future production
provisioning can go through a reviewed lock/temp/validate/promote path.

## Current Evidence

- PR #314 is open, green, and mergeable; it fixes Cockpit company DB resolution.
- Production company DB remains absent:
  `/mnt/tenn-nvme2/tenn/financial-engine_v2/reports/qual_context/company.sqlite`.
- Production news DB exists:
  `/mnt/tenn-nvme2/tenn/financial-engine_v2/reports/qual_context/news.sqlite`.
- Source corpus exists at:
  `/mnt/tenn-nvme2/tenn/financial-engine_v2/data/asx/docs`.
- Current compute remains unsuitable for a quick full BGE build:
  the live runtime venv is CPU-only, and the directly visible Tesla M40 is
  compute capability 5.2 while the builder's sentence-transformers CUDA gate
  requires compute capability >= 7.

## Changes

- Added `scripts/build_company_context_artifact.py`.
  - Default mode is plan-only and does not require or create artifact paths.
  - `--stage-only` builds and validates a staged DB without promotion.
  - `--allow-production-write` is required before promotion to the production
    artifact root.
  - Production promotion also refuses to replace an existing `company.sqlite`
    unless `--replace-existing` is supplied.
  - Production semantic artifact builds reject `--embed-backend hash`; hash is
    available only with `--allow-test-hash-backend` for temp tests.
  - Builds use a lock file and stage into a run-specific directory first.
  - Run ids are constrained to a single safe path segment to prevent staging
    path traversal.
  - Production promotion stages under the artifact root by default, so final
    replacement stays on the artifact filesystem.
  - Existing staged artifacts for the same run id fail closed instead of being
    reused.
  - Staged DB validation requires a non-empty `context_chunks` table, company
    corpus rows, SQLite `quick_check`, required columns, numeric JSON embedding
    lists with consistent dimensions, a success manifest, matching chunk count,
    and nonzero query results when a query is requested.
  - The wrapper prefers `financial-engine_v2/.venv/bin/python` when present and
    falls back to `sys.executable`.
- Added `scripts/test_build_company_context_artifact.py`.
  - Uses a fake builder and temp SQLite files only.
  - Tests plan-only behavior, hash gating, lock failure, stage-only validation,
    promotion mechanics, existing-production-DB refusal, and hash rejection in
    plan mode.
  - Tests stale staging-artifact refusal and production staging-root safety.
  - Tests run-id traversal rejection, malformed embedding JSON rejection,
    missing embedding-column rejection, and corrupt SQLite rejection.

## Plan-Only Output

Command:

```bash
python3 scripts/build_company_context_artifact.py --run-id current-plan
```

Result: exit 0 with JSON plan. The plan targets:

```text
pdf_dir=/mnt/tenn-nvme2/tenn/financial-engine_v2/data/asx/docs
final_db=/mnt/tenn-nvme2/tenn/financial-engine_v2/reports/qual_context/company.sqlite
staged_db=/tmp/tenn_company_context_builds/current-plan/company.sqlite
embed_backend=sentence-transformers
embed_model=BAAI/bge-large-en-v1.5
st_device=auto
```

No production artifact was written.

## Validation

```bash
python3 scripts/test_build_company_context_artifact.py
python3 -m py_compile scripts/build_company_context_artifact.py scripts/test_build_company_context_artifact.py
git diff --check
python3 scripts/build_company_context_artifact.py --run-id current-plan
python3 scripts/build_company_context_artifact.py --embed-backend hash --run-id hash-plan-reject
```

Results:

```text
test_build_company_context_artifact.py: Ran 13 tests, OK
py_compile: passed
git diff --check: passed
plan-only command: exit 0
hash plan rejection: exit 2
```

Task-card validator:

```text
DATA_MISSING: scripts/agent_job_contract.py absent in stacked baseline
```

## Unsafe Actions Avoided

- Did not write `/mnt/tenn-nvme2/tenn/financial-engine_v2/reports/qual_context/company.sqlite`.
- Did not stop `llama-server`, change GPU/runtime config, install dependencies,
  edit crontab/timers, mutate source PDFs, or write Qdrant/Redis.
- Did not change Cockpit degraded-startup behavior.
- Did not modify or clean the dirty live checkout.

## Remaining Gate

This runner makes the production artifact build path safer and reviewable, but
the production system is not done. The actual `company.sqlite` still needs an
approved production run and post-run validation. The next safe sequence is:

1. Merge PR #314.
2. Merge this stacked runner PR.
3. Approve either a managed CPU production build or provision supported CUDA
   compute for sentence-transformers BGE.
4. Run `scripts/build_company_context_artifact.py --allow-production-write ...`
   with a production run id.
5. Validate the DB and Cockpit startup with no temp override.
