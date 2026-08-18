# Validation Summary

## Commands And Results

```text
pwd -P
# /home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1

git rev-parse --abbrev-ref HEAD
# migration/clean-runtime-baseline-reconstruct-v1

git rev-parse HEAD
# 06cb29067d1021ea89d7b93341653d5750babe92

git merge-base --is-ancestor 8c9e3e0a9fd16034dee47317d7b69e80704c5453 HEAD
# exit 0

gh pr view 39 --json number,state,isDraft,headRefName,baseRefName,mergeable,url,updatedAt,statusCheckRollup
# PR #39 open, draft, head ref migration/clean-runtime-baseline-reconstruct-v1;
# lint-and-test completed with FAILURE for run 26439822448; scan completed SUCCESS.

gh run view 26439822448 --json databaseId,headSha,status,conclusion,createdAt,updatedAt,event,headBranch,name,url
# completed failure; headSha 8635833b7d7359ed55daf0495eb49c5457bab91d

python3 scripts/agent_job_contract.py validate docs/agent_tasks/pr39_backend_architecture_invariant_reconciliation_v1_20260527.md
# ok true

python3 scripts/agent_job_registry.py list-active --read-only
# ok true; active_jobs []

python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/pr39_backend_architecture_invariant_reconciliation_v1_20260527.md
# ok false; unrelated dirty file outside allowlist:
# docs/agent_tasks/extraction_primary_canary_retry_after_cache_fix_v1_20260527.md

python3 -m pytest -c pytest.ini financial-engine_v2/backend/tests/test_architecture_invariants.py financial-engine_v2/backend/tests/test_cursor_rule_compliance.py -q
# failed locally because pytest was not installed in the ambient interpreter

uv run --python 3.10 pytest -c pytest.ini financial-engine_v2/backend/tests/test_architecture_invariants.py financial-engine_v2/backend/tests/test_cursor_rule_compliance.py -q
# failed locally because pytest was not installed in the uv ephemeral environment without requirements

uv run --python 3.10 --with-requirements financial-engine_v2/backend/requirements.txt --with-requirements financial-engine_v2/backend/requirements-dev.txt python -m pytest -c pytest.ini financial-engine_v2/backend/tests/test_architecture_invariants.py financial-engine_v2/backend/tests/test_cursor_rule_compliance.py -q
# pre-fix focused reproduction: 6 failed, 7 passed

uv run --python 3.10 --with-requirements financial-engine_v2/backend/requirements.txt --with-requirements financial-engine_v2/backend/requirements-dev.txt python -m pytest -c pytest.ini financial-engine_v2/backend/tests/test_architecture_invariants.py financial-engine_v2/backend/tests/test_cursor_rule_compliance.py -q
# post-fix focused validation: 13 passed in 5.53s

uv run --python 3.10 --with ruff==0.15.6 ruff check financial-engine_v2/backend/tests/test_architecture_invariants.py financial-engine_v2/backend/tests/test_cursor_rule_compliance.py
# All checks passed

uv run --python 3.10 --with ruff==0.15.6 ruff format --check financial-engine_v2/backend/tests/test_architecture_invariants.py financial-engine_v2/backend/tests/test_cursor_rule_compliance.py
# 2 files already formatted

git diff --check
# exit 0

python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/pr39_backend_architecture_invariant_reconciliation_v1_20260527.md
# ok false; disallowed file:
# docs/agent_tasks/extraction_primary_canary_retry_after_cache_fix_v1_20260527.md
# report_path: reports/agent_jobs/pr39_backend_architecture_invariant_reconciliation_v1_20260527/diff-check.json
```

Report JSON parse validation was run after writing `status.json` and
`invariant_matrix.json`; both parsed successfully.

## Not Run

- Production services.
- Production DB/Qdrant/news/memory mutation jobs.
- Broad pytest suites.
- Parser, extraction, gold-label, canonical truth, runtime config, Docker, or service rebinding workflows.
- GitHub mutation, PR update, issue closeout, push, merge, rebase, or cherry-pick.
