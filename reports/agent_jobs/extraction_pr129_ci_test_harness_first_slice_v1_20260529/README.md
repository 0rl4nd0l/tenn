# PR 129 CI Test-Harness First Slice

Job: `extraction_pr129_ci_test_harness_first_slice_v1_20260529`

Branch: `safe/extraction-real-gold-corpus-baseline-v1-20260529`

Base PR: #129, `migration/clean-runtime-baseline-reconstruct-v1`

Mode: SAFE EXTENSION MODE, test-harness only.

## Decision

Fixed the first locally reproduced CI test-harness slice blocking PR #129:

- Cockpit service-session tests now accept the current production
  `_build_chat_controller(..., llm_client=...)` call shape in their test
  doubles.
- Streaming subprocess tests now pass deterministic `job_id` values to
  `_run_action_subprocess_streaming()`, matching the production helper
  signature.
- The artifact-dir normalization test now compares against `Path("/data").resolve()`
  so it remains correct on hosts where `/data` is a symlink to the NVMe data
  root and in CI where `/data` may remain literal.

No production code changed.

No runtime reload, canary run, `POST /api/process/document`, broad extraction,
backfill, production DB write, Qdrant/news/memory mutation, source-PDF mutation,
parser/prompt/schema change, service/GPU/model config change, Cockpit UI work,
or GitHub issue closure was performed by this task.

## Current Validation

Passed:

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/extraction_pr129_ci_test_harness_first_slice_v1_20260529.md`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/extraction_pr129_ci_test_harness_first_slice_v1_20260529.md --repo-root .`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/extraction_pr129_ci_test_harness_first_slice_v1_20260529.md`
- `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/financial-engine_v2/.venv/bin/python -m pytest -q financial-engine_v2/backend/tests/test_cockpit_service_session_threads.py financial-engine_v2/backend/tests/test_streaming_subprocess.py`:
  `35 passed`
- `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/financial-engine_v2/.venv/bin/python -m ruff check financial-engine_v2/backend/tests/test_cockpit_service_session_threads.py financial-engine_v2/backend/tests/test_streaming_subprocess.py`:
  `All checks passed!`
- `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/financial-engine_v2/.venv/bin/python -m py_compile financial-engine_v2/backend/tests/test_cockpit_service_session_threads.py financial-engine_v2/backend/tests/test_streaming_subprocess.py`
- PR #129 focused extraction suite:
  `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/financial-engine_v2/.venv/bin/python -m pytest -q financial-engine_v2/backend/tests/test_extraction_gold_eval.py financial-engine_v2/backend/tests/test_extraction_pre_canary_truth_gates.py financial-engine_v2/backend/tests/test_extraction_gold_eval_scorecard.py financial-engine_v2/backend/tests/test_multipass_extraction.py financial-engine_v2/backend/tests/test_metric_ontology_bridge.py`:
  `252 passed, 5 warnings`

Local broad CI command was attempted with the project venv:

`/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/financial-engine_v2/.venv/bin/python -m pytest -c pytest.ini financial-engine_v2/backend/tests financial-engine_v2/cockpit/tests -q`

It stopped during collection on missing local dev dependency `respx`. The GitHub
CI workflow installs `financial-engine_v2/backend/requirements-dev.txt`, so this
local venv dependency gap is not the same failure mode as the GitHub-hosted
PR #129 run.

## CI Impact

This should remove the reproduced PR #129 failures in:

- `financial-engine_v2/backend/tests/test_cockpit_service_session_threads.py`
- `financial-engine_v2/backend/tests/test_streaming_subprocess.py`

It does not claim to fix the remaining known broad CI failures in marketplace,
memo signal routing, Redis-dependent process-document, query-orchestrator,
Cockpit agent/router/subagent tests, or any future CI result not yet observed
after this push.

## Goal Impact

This improves PR #129 mergeability for the consolidated BHP real-gold/source
path evidence and therefore advances item 7 of the active extraction goal. The
full extraction goal remains incomplete until the remaining CI blockers, fresh
approved third canary, #97 actual-payload scorecard, #98/#99 closure, and full
graduation evidence are complete.

## Next Safe Step

Run final task-card diff/staging gates, commit, release the claim, push PR #129,
and inspect the new GitHub check result. Continue with the next failing CI slice
only if it is narrow and safe; otherwise keep it separate from extraction truth
work.
