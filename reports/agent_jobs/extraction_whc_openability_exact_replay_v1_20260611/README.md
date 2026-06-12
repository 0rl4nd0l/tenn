# WHC Openability Exact Replay

State: DONE_WITH_RISK

This report records a single exact local replay for WHC document
`9640d9f1-a45b-492d-8df5-9bad0f46431c` with the opt-in openability selected-table
bridge enabled.

No code changes, broad extraction, backfill, service routes, production DB
writes, source-PDF mutation, prompt/gold/schema/runtime/model/GPU mutation, or
PR #318 patch mining are allowed.

## Result

The exact replay was attempted with:

- `parser_backend="pymupdf"`
- `skip_narrative=True`
- `openability_selected_tables=True`
- `openability_pages=[57, 58, 60, 61]`
- temporary `DATA_ROOT=/tmp/tenn_whc_openability_exact_replay_data_*`

The run did not reach canonical metric extraction. It failed at Pass 1 with:

`pass1:OLLAMA_URL must be set when provider is 'ollama'`

## Evidence

- Source PDF was readable.
- Temporary parser cache was created under the temporary `DATA_ROOT`.
- Temporary data root was removed after the replay.
- No production cache was written.
- No canonical metrics were accepted.
- Non-null metric count: 0.

## DATA_MISSING

- Live/local extraction LLM behavior for WHC remains `DATA_MISSING`.
- Observed saved-artifact scorecard gain remains `DATA_MISSING`.

## Next Task

Run the same exact replay after the local extraction LLM runtime configuration is
available, without changing prompts, models, schemas, or validation gates.
