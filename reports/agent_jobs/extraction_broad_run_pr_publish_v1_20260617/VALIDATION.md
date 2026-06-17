# Validation

## Completed Before Publish Scaffold

```bash
PYTHONDONTWRITEBYTECODE=1 /home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/financial-engine_v2/.venv/bin/python -m py_compile financial-engine_v2/scripts/broad_extraction_test.py financial-engine_v2/scripts/test_broad_extraction_test.py
```

Result: exit `0`.

```bash
PYTHONDONTWRITEBYTECODE=1 /home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/financial-engine_v2/.venv/bin/python -m pytest financial-engine_v2/scripts/test_broad_extraction_test.py -q
```

Result: exit `0`; `9 passed in 0.13s`.

## Publish Validation

```bash
python3 scripts/agent_job_contract.py validate docs/agent_tasks/extraction_broad_run_pr_publish_v1_20260617.md --write-report
```

Result: exit `0`, `ok: true`; wrote `validation.json`.

```bash
python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/extraction_broad_run_pr_publish_v1_20260617.md --repo-root .
```

Result: exit `0`, `ok: true`; wrote `diff-check.json`.

```bash
git diff --check
```

Result: exit `0`.

Pending before publish scaffold commit:

- check report artifacts
- push branch
- open draft PR

## Forbidden Actions Not Run

- No merge.
- No PR #318 use.
- No count-24, count-32, broad extraction, broad backfill, random samples, or
  full ticker-universe extraction.
- No runtime services.
- No DB, Qdrant, Redis, news, memory, source PDF, prompt, gold-label, schema,
  model, GPU, service, or production data mutation.
