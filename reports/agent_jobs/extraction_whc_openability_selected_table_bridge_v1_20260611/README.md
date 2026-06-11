# WHC Openability Selected-Table Bridge

State: DONE_WITH_RISK

This job is the next bounded slice after the WHC openability diagnostic sidecar.
It may add an explicit opt-in bridge from already-captured openability
diagnostics into selected statement tables, but default extraction must remain
unchanged.

No broad extraction, count samples, service routes, DB/Qdrant/Redis/news/memory,
source-PDF, prompt/gold/schema/runtime/model/GPU mutation, or PR #318 patch
mining is allowed.

## Result

- Added an opt-in `openability_selected_tables` bridge in
  `multipass_extraction.py`.
- The bridge requests parser openability diagnostics only when explicitly
  enabled.
- Existing openability diagnostics can be converted into synthetic statement
  tables only when the diagnostic payload is provenance-only, has explicit
  period evidence, has exact scale evidence, and row candidates are marked
  `financial_amount`.
- Synthetic tables still go through Pass 2, Pass 3a, Pass 4, and existing
  validation gates.
- Default extraction behavior remains unchanged.

## WHC Evidence Covered

Mocked WHC-style diagnostics cover:

- page 57 income statement rows, including revenue `4,920,102`
- page 58 balance sheet rows, including cash `1,215,460`
- page 60 cash-flow rows, including operating cash flow `2,529,823` and capex
  `(124,210)`
- scale evidence from `$000` / nearest thousand diagnostic phrases
- period evidence from `For the year ended 30 June 2022` and `As at 30 June
  2022`

## Validation

- Task card validate: passed.
- Registry read-only: `ok=true`, `active_jobs=[]`.
- Focused pytest: `190 passed in 2.13s`.
- `py_compile`: passed.
- `ruff`: passed.
- Code review: no critical findings, warnings, or suggestions.

## Remaining Risk

This is not a saved-artifact scorecard gain yet. The implementation is opt-in
and mocked because running exact WHC extraction or a scorecard replay would cross
the current no-extraction boundary. The next safe step is an exact WHC saved/local
replay under a new card that explicitly allows opt-in openability diagnostics for
document `9640d9f1-a45b-492d-8df5-9bad0f46431c` only.
