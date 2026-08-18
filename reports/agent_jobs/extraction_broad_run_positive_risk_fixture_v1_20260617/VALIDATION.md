# Validation

## Commands

```bash
python3 scripts/agent_job_contract.py validate docs/agent_tasks/extraction_broad_run_positive_risk_fixture_v1_20260617.md --write-report
```

Result: exit `0`, `ok: true`; wrote `validation.json`.

```bash
PYTHONDONTWRITEBYTECODE=1 /home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/financial-engine_v2/.venv/bin/python - <<'PY'
# inline exact synthetic fixture replay; transforms positive_fixture_input.json
# through _build_metric_provenance_audit, _build_scale_magnitude_risk, and
# compute_summary without running extraction
PY
```

Result: exit `0`; wrote:

- `positive_fixture_input.json`
- `positive_broad_run_record.json`
- `positive_summary.json`
- `positive_assertions.json`

Assertions passed:

- accepted-output risk payload exists and has `accepted_output=true`;
- `risk_level` is `review`;
- expected positive risk flags are present;
- risk flag count matches the flag arrays;
- summary `risk_flag_distribution` counts each expected flag once;
- summary `risk_flagged_documents` is `1`;
- `provenance_missing` is empty for the synthetic fixture.

```bash
python3 scripts/agent_job_contract.py check-report-artifacts docs/agent_tasks/extraction_broad_run_positive_risk_fixture_v1_20260617.md --repo-root .
```

Result: exit `0`, `ok: true`; all expected report artifacts were present.

```bash
python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/extraction_broad_run_positive_risk_fixture_v1_20260617.md --repo-root .
```

Result: exit `0`, `ok: true`; no disallowed files.

```bash
git diff --check
```

Result: exit `0`.

## Fixture Result

- Fixture id: `synthetic_positive_scale_magnitude_risk_v1`
- Mode: `exact_synthetic_no_extraction`
- Status: `ok`
- Non-null metrics: `5`
- Provenance missing: `[]`
- Risk level: `review`
- Risk flags:
  - `all_checked_metrics_below_minimum`
  - `mixed_metric_source_scales`
  - `payload_scale_differs_from_metric_source_scale`
  - `metric_source_scale_missing`
  - `metric_revenue_ratio_high`

## Forbidden Actions Avoided

- No `run_multipass_extraction`.
- No count-24, count-32, broad extraction, broad backfill, or full ticker-universe extraction.
- No runtime service start.
- No canonical writes.
- No DB, Qdrant, Redis, news, memory, source PDF, prompt, gold-label, schema, model, GPU, or service mutation.
- No GitHub mutation, push, or PR.
