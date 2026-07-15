# Runtime Functionality Proof

| Field | Required evidence |
| --- | --- |
| intended output | Live Cockpit answers interactive chat through Claude, and live non-metric news/tool LLM work uses Claude while metric extraction retains the local model. |
| live output location | Cockpit chat API/UI response metadata plus backend news memo `extraction_provenance`. |
| pre-run max timestamp or count | `DATA_MISSING` — this code-only lane did not capture a live output baseline before service activation. |
| post-run max timestamp or count | `DATA_MISSING` — the live service was not restarted onto this branch. |
| rows/files inserted or updated after run start | `0` live rows/files; data and news-store mutation were forbidden. |
| readiness/gate status | Code, tests, review, and stateless Claude connectivity are ready; live activation gate remains owner-approval-required. |
| exact command/query used | Stateless proof used Tenn `AnthropicClient()` with `prompt="Reply exactly ROUTE_OK"`, `prior_messages=None`, and no persisted chat; focused pytest commands are listed in `VALIDATION.md`. |
| result | `DATA_MISSING` |
| remaining blocker | Controlled live deployment/restart and an after-start chat/news routing proof were outside the approved lane. |

result: DATA_MISSING
