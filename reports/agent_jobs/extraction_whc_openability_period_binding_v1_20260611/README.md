# WHC Openability Period Binding

State: DONE_WITH_RISK

This safe extension binds WHC openability diagnostic reporting-period phrases into the existing source-period evidence detector only when `openability_selected_tables=True`.

Exact replay result for WHC `9640d9f1-a45b-492d-8df5-9bad0f46431c`:

- Prior runtime replay: `failed`, `validation_gate:missing_period_end`, 9 non-null values before acceptance.
- After fix: `ok`, `period_end=2022-06-30`, `8` accepted non-null canonical metrics.
- Observed accepted gain versus the prior runtime replay: +1 document / +8 metrics.
- `net_debt` was not accepted in the passing replay; this avoids overclaiming a derived/weakly sourced debt metric.

Files changed are limited to the task card, `multipass_extraction.py`, focused tests, and this report directory. No extraction samples, backfills, service routes, production stores, source PDFs, prompts, gold labels, schemas, runtime config, model/GPU config, parser cache, or PR #318 patch sources were used.

Next recommended task: run a bounded saved-artifact scorecard/evaluator replay that includes WHC plus the existing CTN/HUB/AZJ/NSR guard cases, still without broad extraction or production mutation, to prove no regression before merge/push decisions.
