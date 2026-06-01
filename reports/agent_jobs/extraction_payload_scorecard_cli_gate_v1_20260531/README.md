# Extraction Payload Scorecard CLI Gate

## Summary

This safe-extension slice exposes the confirmed-metric payload scorecard and
`pre_persistence_scorecard_gate_v1` through the existing
`scripts/extraction_gold_eval_scorecard.py` helper.

The new `confirmed_metric_payload` profile requires an operator-supplied
actuals JSON map and can emit the pre-persistence gate artifact in the same
output file. It does not run extraction, start runtime services, or authorize
canonical writes.

## Scope

- Lane: Evaluation, with Financial Truth support.
- Branch: `safe/extraction-payload-scorecard-cli-gate-v1-20260531`.
- Worktree:
  `/home/l4nd0/tenn-extraction-payload-scorecard-cli-gate-v1-20260531`.
- Execution mode: SAFE EXTENSION MODE.
- Runtime/backend/GPU work: not performed.
- Production data access: not used.

## Result

- Added `--profile confirmed_metric_payload`.
- Added `--actuals-json` input validation for payload scoring.
- Added `--include-pre-persistence-gate` to emit the gate beside the payload
  scorecard.
- Preserved existing canonical core, expanded required, and
  confirmed-metric-coverage inventory behavior.
- Added focused script regressions and a sample CLI output artifact.

## Sample Artifact

Sample command:

```bash
PYTHONPATH=financial-engine_v2/backend \
  /home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/financial-engine_v2/.venv/bin/python \
  scripts/extraction_gold_eval_scorecard.py \
  --profile confirmed_metric_payload \
  --actuals-json reports/agent_jobs/extraction_payload_scorecard_cli_gate_v1_20260531/cli_actuals_sample.json \
  --include-pre-persistence-gate \
  --out-json reports/agent_jobs/extraction_payload_scorecard_cli_gate_v1_20260531/cli_payload_gate_sample.json
```

Sample result:

- Profile: `confirmed_metric_payload`
- Actual payload documents supplied: `1`
- Total metric expectations scored/reviewed: `146`
- Gate status: `fail`
- Gate decision: `blocked`
- `canonical_write_allowed`: `false`
- `broad_backfill_authorized`: `false`

## Full Goal Status

This improves the repeatability of broader scorecard evidence needed before
third-canary or all-ticker graduation claims. It does not complete the full
metric extraction objective because runtime canary execution, full corpus
payload evidence, and graduation proof remain open.
