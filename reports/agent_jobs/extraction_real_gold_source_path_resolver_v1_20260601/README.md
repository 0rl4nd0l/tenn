# Extraction Real-Gold Source Path Resolver V1

Task card: `docs/agent_tasks/extraction_real_gold_source_path_resolver_v1_20260601.md`

Lane: Financial Truth

Mode: SAFE EXTENSION.

## Result

The backend real-gold eval source resolver now reuses the existing allowlisted
confirmed-metric coverage source resolver. This lets `/api/extraction-eval/real-gold`
open canonical fixture source paths through the current `/data/asx/docs`
binding.

Before the fix:

- Canonical real-gold fixtures checked: 15
- Backend real-gold resolver successes: 0
- Existing confirmed-metric coverage resolver successes: 15

After the fix:

- Canonical real-gold fixtures checked: 15
- Backend real-gold resolver successes: 15
- Existing confirmed-metric coverage resolver successes: 15

## Scope Boundary

This task did not start backend/runtime services, run the real-gold eval,
submit canary documents, run broad extraction, mutate source PDFs, copy
source assets, write canonical financial rows, change parser prompts/routing,
change schemas, write Qdrant/news/memory stores, change Cockpit UI, or mutate
GitHub.

## Validation

- `test_extraction_gold_eval.py`: 29 passed
- Targeted Ruff: passed
- Redirected `py_compile`: passed
- Before/after real-gold source-path probes: 0/15 -> 15/15

## Next Safe Step

Create a separate approval-required runtime task card for the backend real-gold
eval run at current HEAD. That task must start/reload runtime services only
under explicit bounds and record queue/GPU/model/source-path gates before
calling `/api/extraction-eval/real-gold`.
