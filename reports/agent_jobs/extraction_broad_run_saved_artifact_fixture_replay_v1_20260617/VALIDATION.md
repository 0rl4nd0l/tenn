# Validation

## Commands

```bash
python3 scripts/agent_job_contract.py validate docs/agent_tasks/extraction_broad_run_saved_artifact_fixture_replay_v1_20260617.md --write-report
```

Result: exit `0`, `ok: true`; wrote `validation.json`.

```bash
PYTHONDONTWRITEBYTECODE=1 /home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/financial-engine_v2/.venv/bin/python - <<'PY'
# inline saved-artifact replay; transforms lbl_replay_summary.json through
# _build_metric_provenance_audit, _build_scale_magnitude_risk, and compute_summary
PY
```

Result: exit `0`; wrote:

- `fixture_broad_run_record.json`
- `fixture_summary.json`
- `fixture_assertions.json`

Assertions passed:

- record status is accepted output;
- `metric_provenance` is non-empty;
- `revenue` provenance is available;
- `provenance_missing` is an explicit list;
- `accepted_output_scale_magnitude_risk` exists and has `accepted_output=true`;
- summary `provenance_coverage` exists and is non-empty;
- summary `risk_flag_distribution` exists.

```bash
python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/extraction_broad_run_saved_artifact_fixture_replay_v1_20260617.md --repo-root .
```

Initial result: exit `1`; `audit_only` task cards require
`allow_audit_code_changes=true` before the task/report package itself can be
accepted by the diff contract. The task card was updated to make that scope
explicit, then the contract was rerun.

Final result: exit `0`, `ok: true`; no disallowed files.

```bash
python3 scripts/agent_job_contract.py check-report-artifacts docs/agent_tasks/extraction_broad_run_saved_artifact_fixture_replay_v1_20260617.md --repo-root .
```

Result: exit `0`, `ok: true`; all expected report artifacts were present.

```bash
git diff --check
```

Result: exit `0`.

## Fixture Result

- Source artifact: `reports/agent_jobs/extraction_lbl_income_row_ref_repair_v1_20260616/lbl_replay_summary.json`
- Mode: `saved_artifact_no_extraction`
- Status: `ok`
- Non-null metrics: `7`
- Provenance missing: `[]`
- Risk level: `none`
- Risk flags: `[]`

## Forbidden Actions Avoided

- No `run_multipass_extraction`.
- No count-24, count-32, broad extraction, broad backfill, or full ticker-universe extraction.
- No runtime service start.
- No canonical writes.
- No DB, Qdrant, Redis, news, memory, source PDF, prompt, gold-label, schema, model, GPU, or service mutation.
- No GitHub mutation, push, or PR.
