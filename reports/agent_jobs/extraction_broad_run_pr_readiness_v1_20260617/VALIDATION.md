# Validation

## Commands

```bash
python3 scripts/agent_job_contract.py validate docs/agent_tasks/extraction_broad_run_pr_readiness_v1_20260617.md --write-report
```

Result: exit `0`, `ok: true`; wrote `validation.json`.

```bash
python3 scripts/agent_job_contract.py validate docs/agent_tasks/extraction_broad_run_provenance_risk_flags_v1_20260617.md
python3 scripts/agent_job_contract.py validate docs/agent_tasks/extraction_broad_run_saved_artifact_fixture_replay_v1_20260617.md
python3 scripts/agent_job_contract.py validate docs/agent_tasks/extraction_broad_run_positive_risk_fixture_v1_20260617.md
```

Result: all exit `0`, `ok: true`.

```bash
python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/extraction_broad_run_pr_readiness_v1_20260617.md --repo-root .
```

Result: exit `0`, `ok: true`; no disallowed files. This command wrote
`diff-check.json`.

```bash
python3 scripts/agent_job_contract.py check-report-artifacts docs/agent_tasks/extraction_broad_run_pr_readiness_v1_20260617.md --repo-root .
```

Initial result before `check-diff`: exit `1`, missing `diff-check.json`.
Final result after `check-diff`: exit `0`, `ok: true`.

```bash
python3 scripts/agent_job_contract.py check-report-artifacts docs/agent_tasks/extraction_broad_run_provenance_risk_flags_v1_20260617.md --repo-root .
python3 scripts/agent_job_contract.py check-report-artifacts docs/agent_tasks/extraction_broad_run_saved_artifact_fixture_replay_v1_20260617.md --repo-root .
python3 scripts/agent_job_contract.py check-report-artifacts docs/agent_tasks/extraction_broad_run_positive_risk_fixture_v1_20260617.md --repo-root .
```

Result: all exit `0`, `ok: true`.

```bash
git diff --check origin/migration/clean-runtime-baseline-reconstruct-v1...HEAD
```

Result: exit `0`.

```bash
PYTHONDONTWRITEBYTECODE=1 /home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/financial-engine_v2/.venv/bin/python -m py_compile financial-engine_v2/scripts/broad_extraction_test.py financial-engine_v2/scripts/test_broad_extraction_test.py
```

Result: exit `0`.

```bash
PYTHONDONTWRITEBYTECODE=1 /home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/financial-engine_v2/.venv/bin/python -m pytest financial-engine_v2/scripts/test_broad_extraction_test.py -q
```

Result: exit `0`; `9 passed in 0.13s`.

## Not Run

- No count-24 or count-32.
- No broad extraction or broad backfill.
- No full ticker-universe extraction.
- No runtime services.
- No DB, Qdrant, Redis, news, memory, source PDF, prompt, gold-label, schema,
  model, GPU, service, GitHub, or remote branch mutation.
