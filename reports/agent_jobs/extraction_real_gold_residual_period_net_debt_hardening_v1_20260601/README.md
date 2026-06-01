# Extraction Real-Gold Residual Hardening

Job: `extraction_real_gold_residual_period_net_debt_hardening_v1_20260601`

Lane: Financial Truth

Mode: SAFE EXTENSION with bounded backend runtime validation

## Outcome

The three residual canonical blockers from the prior real-gold backend eval are
fixed in this task-card scope:

- `14d_q_2021-03-31`: Appendix 4C quarter-end text with parenthetical wording
  now yields `period_type=Q`, `period_end=2021-03-31`.
- `29m_a_2025-12-31`: explicit `Net Drawn Debt 1` source evidence now recovers
  `net_debt=85161000`.
- `a2m_h_2025-12-31`: derived negative `net_debt` from
  `total_debt(39000000)-cash_end(436878000)` is blocked unless an explicit
  source row reports net debt.

This is not broad ticker-universe extraction graduation. It is the current
canonical 15-document real-gold proof point for the residual hardening slice.

## Final Runtime Eval

- Route: backend real-gold eval
- Dataset: `financial-engine_v2/data/extraction_gold_real`
- Parser: `docling`
- Strict method: `true`
- Limit: `0`
- Tolerance: `0.01`
- Documents: `15`
- Metric checks: `39`
- Correct: `39`
- Metric accuracy: `100.00%`
- Context accuracy: `100.00%`
- Trust distribution: `trusted=15`, `abstain=0`, `quarantine=0`
- Failed documents: `0`

Primary artifacts:

- `real_gold_eval_results.json`
- `real_gold_eval_results_summary.json`
- `real_gold_eval_results_canonical_scorecard.json`
- `real_gold_eval_results_documents.csv`
- `real_gold_eval_results_metrics.csv`
- `real_gold_eval_summary.md`
- `real_gold_eval_stdout.txt`

## Runtime Cleanup

Dedicated backend/router units were stopped after validation. Shutdown evidence
is recorded in `runtime_shutdown.json`: ports `8000`/`8001` closed, GPU activity
guard inactive, and M40 VRAM returned to `0 / 24576 MiB`.
