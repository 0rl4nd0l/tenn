# Automation Small Model Routing V1 Validation

validated_at: 2026-07-10T05:56:19+10:00

review_fix_started_at: 2026-07-10T14:59:00+10:00

review_fix_validated_at: 2026-07-10T14:59:35+10:00

Status: DONE_WITH_RISK

## Command Results

- PASS:
  `python3 scripts/tenn_dev_status.py`.
  Repo root
  `/home/l4nd0/tenn-automation-small-model-routing-v1-20260710`, branch
  `control-plane/automation-small-model-routing-v1-20260710`, HEAD
  `ed481f4a333d3d62e944ccd48a6fcdccbfb67068`, guard result `pass`,
  duplicate work `NO_MATCHING_ACTIVE_WORK_FOUND`, registry `PASS`, ledger
  `PASS`. Dirty state is expected from this task's allowlisted edits.
- PASS:
  `python3 scripts/agent_job_contract.py validate docs/agent_tasks/automation_small_model_routing_v1_20260710.md`.
  Result: `ok=true`, no issues.
- PASS:
  `python3 -m unittest scripts/test_codex_automation_runner.py`.
  Result: 13 tests passed.
- PASS:
  `python3 scripts/codex_automation_runner.py list`.
  Result: all 8 jobs listed with model policy metadata. `automation-health`
  reports `native`; `repo-hygiene`, `daily-closeout`, `doc-drift`,
  `future-opportunities`, and `memory-drift` report `small`; `bug-regression`
  and `extraction-regression` report `default`.
- PASS:
  `TENN_CODEX_AUTOMATION_OUTPUT_ROOT=<tmp> python3 scripts/codex_automation_runner.py repo-hygiene --dry-run`.
  Result: command includes `--model gpt-5.4-mini` and
  `model_reasoning_effort="medium"`.
- PASS:
  `TENN_CODEX_AUTOMATION_OUTPUT_ROOT=<tmp> python3 scripts/codex_automation_runner.py extraction-regression --dry-run`.
  Result: command omits `--model` and keeps Codex default routing.
- PASS:
  `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/automation_small_model_routing_v1_20260710.md --no-write-report`.
  Result: no disallowed files.
- PASS:
  `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/automation_small_model_routing_v1_20260710.md`.
  Result: no disallowed files; wrote
  `reports/agent_jobs/automation_small_model_routing_v1_20260710/diff-check.json`.

## Code Review

- Initial review found no critical issues, one durable approval/state warning,
  and two hardening suggestions covering override tests and reasoning-value
  validation.
- Orlando approved applying those review fixes to draft PR #499.
- RED proof: `python3 -m unittest scripts/test_codex_automation_runner.py`
  ran 16 tests with one expected failure:
  `test_invalid_reasoning_effort_names_the_environment_variable` reported that
  `ValueError` was not raised.
- GREEN proof: the same command ran 16 tests successfully after validation was
  added.
- PASS: `uv run --with pytest pytest -q scripts/test_codex_automation_runner.py`
  ran 16 tests and 48 subtests. Pytest emitted one non-blocking warning because
  the ephemeral environment does not install the plugin for the repo's
  `asyncio_default_fixture_loop_scope` option.
- PASS:
  `uv run --with ruff ruff check scripts/codex_automation_runner.py scripts/test_codex_automation_runner.py`.
- PASS: task-card validation, no-write diff scope, report-artifact validation,
  and closeout validation.
- PASS: default small routing, default high-risk routing, and uppercase global
  override dry-runs.
- PASS: invalid `TENN_CODEX_AUTOMATION_REASONING_EFFORT=medum` exited non-zero
  before child execution and named the variable, invalid value, and allowed
  values.
- PASS: `python3 -m py_compile`, `git diff --check`, and markdown hygiene.
- Final code review: no critical findings, warnings, or suggestions.
- GitHub CI was green before this review-fix commit; fresh CI is required after
  push.

## Runtime Functionality Note

This was a control-plane source change. No live systemd timers, services,
automation execution worktree, runtime data, DB, Qdrant, source PDFs, gold
labels, model/GPU runtime config, or GitHub state were mutated.

Live scheduled automations are not claimed updated from this report alone. The
repo command-construction behavior is proven locally; live behavior requires
merge plus execution-surface update.
