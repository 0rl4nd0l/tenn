# Validation

## Red Check

- `uv run --with pytest --with pyyaml python -m pytest scripts/test_agent_job_contract.py -k "control_plane_mention or negative_report_only or explicit_closeout_scope or docs_only_control_plane" -q`
  - Result before fix: failed on the two loose-exemption regressions; explicit
    exemption cases passed once parser dependencies were available.
- `uv run --with pytest --with pyyaml python -m pytest scripts/test_agent_job_hook.py -k "control_plane_mention" -q`
  - Result before fix: failed because the Stop hook emitted no warning for a
    runtime-like card that merely mentioned control-plane.

## Green Checks

- `uv run --with pytest --with pyyaml python -m pytest scripts/test_agent_job_contract.py -k "control_plane_mention or negative_report_only or explicit_closeout_scope or docs_only_control_plane" -q`
  - Result: 5 passed, 34 deselected.
- `uv run --with pytest --with pyyaml python -m pytest scripts/test_agent_job_hook.py -k "control_plane_mention" -q`
  - Result: 1 passed, 18 deselected.
- `uv run --with pytest --with pyyaml python -m pytest scripts/test_agent_job_contract.py scripts/test_agent_job_hook.py -q`
  - Result: 58 passed.

## Preflight Checks

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/control_plane_runtime_proof_explicit_exemptions_v1_20260622.md`
  - Result: ok.
- `python3 scripts/agent_job_registry.py list-active --read-only --repo-root .`
  - Result: ok, no active jobs.
- `python3 scripts/agent_task_ledger.py resolve-path`
  - Result:
    `/home/l4nd0/tenn-extraction-handoff-continuation-v1-20260621/.git/tenn-agent-registry/task-ledger.jsonl`.
- `python3 scripts/agent_task_ledger.py validate`
  - Result: ok, `data_missing=["live"]`.

## Final Checks

- `python3 scripts/check_runtime_functionality_proof_docs.py`
  - Result: `runtime_functionality_proof_docs_ok`, 9 fields checked.
- `scripts/sync_codex_skills.sh`
  - Result: dry run only, `would_link=10`, `linked=0`.
- `git diff --check`
  - Result: passed.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/control_plane_runtime_proof_explicit_exemptions_v1_20260622.md --repo-root .`
  - Result: ok, no disallowed files.
- `python3 scripts/agent_job_contract.py check-report-artifacts docs/agent_tasks/control_plane_runtime_proof_explicit_exemptions_v1_20260622.md --repo-root .`
  - Result: ok, all report artifacts present and non-empty.
- Product/runtime/data/extraction/count-24 path guard:
  - Result: no changed paths matched forbidden product/runtime/data/extraction/count-24 prefixes.
- Host-global path guard:
  - Result: no changed paths matched host-global prefixes.
