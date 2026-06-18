# Validation

## Commands

| Command | Exit | Result |
| --- | ---: | --- |
| `python3 scripts/agent_job_contract.py validate docs/agent_tasks/extraction_hub_current_period_line_binding_v1_20260618.md` | 0 | Task card valid. |
| `python3 scripts/agent_job_registry.py list-active --read-only --repo-root .` | 0 | Registry read-only OK; no active jobs. |
| RED focused test from implementation worker | 1 | Intended failure confirmed: HUB-like current/prior fixture returned `period_type=None` before fix completion. |
| `PYTHONPATH=financial-engine_v2/backend uv run ... pytest -q financial-engine_v2/backend/tests/test_extraction_pre_canary_truth_gates.py -k 'hub or explicit_source_period_end or companion'` | 0 | `10 passed, 19 deselected`. |
| `PYTHONPATH=financial-engine_v2/backend uv run ... pytest -q financial-engine_v2/backend/tests/test_extraction_pre_canary_truth_gates.py` | 0 | `29 passed`. |
| `python3 -m py_compile financial-engine_v2/backend/app/services/multipass_extraction.py` | 0 | Syntax check passed. |
| `git diff --check` | 0 | No whitespace errors. |
| `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/extraction_hub_current_period_line_binding_v1_20260618.md --repo-root . --no-write-report` | 0 | Diff scope valid. |
| `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/extraction_hub_current_period_line_binding_v1_20260618.md --repo-root .` | 0 | Diff scope valid; `diff-check.json` written. |
| `python3 scripts/agent_job_contract.py check-report-artifacts docs/agent_tasks/extraction_hub_current_period_line_binding_v1_20260618.md` | 0 | All report artifacts exist and are non-empty. |
| JSON parse for `git_guard.json`, `status.json`, and `validation.json` | 0 | JSON artifacts valid. |

## Not Run

- No extraction, count-24, count-32, random sample, broad extraction, backfill,
  runtime service, DB/Qdrant/Redis/news/memory/source-PDF/gold-label/prompt/
  model/GPU/service mutation, branch cleanup, or unrelated cleanup.
- No exact-HUB runtime/no-write replay was run; a clearly bounded current-repo
  command was not identified during the publish preflight.

## Validation Environment

No repo virtualenv was present. Focused tests used `/home/l4nd0/.local/bin/uv`
with ephemeral validation dependencies only; no project dependency files,
runtime envs, or system packages were changed.
