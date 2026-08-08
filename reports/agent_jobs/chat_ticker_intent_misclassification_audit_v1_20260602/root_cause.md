# Root Cause: Issue #119

## Verdict

`ROOT_CAUSE_DOCUMENTED_AUDIT_ONLY`.

The current code path can still route the Gemini audit prompt to ticker `UI`, but the exact root cause is narrower than the issue body's first hypothesis. The underscore marker `UI_AUDIT_GEMINI` is not itself split by `TICKER_TOKEN_RE` in the current code. The exact prompt also contains the standalone uppercase phrase `Cockpit UI`; that `UI` token is accepted as a ticker before cue-pattern checks run.

## Evidence

Original Gemini audit evidence:

- `/home/l4nd0/.gemini/tmp/tenn-nvme-clean-baseline-reconstruct-v1/ui-audit-gemini-20260526/audit-results.json`
- Prompt: `UI_AUDIT_GEMINI 2026-05-26: From the current Cockpit UI, what should I review first today across holdings, watchlist, and recent news? Use only visible/source-backed Tenn context and say DATA_MISSING where needed.`
- Observed output included: `I couldn't find recent indexed news for UI`, `daily_news_ingest`, `tickers=UI`, and `News search: no hits for UI`.

Current code evidence:

- `financial-engine_v2/shared/ticker_inference.py:10-12` defines the token regex for 2-5 character ticker-like tokens.
- `financial-engine_v2/shared/ticker_inference.py:29-116` defines common stopwords; `UI` is absent.
- `financial-engine_v2/shared/ticker_inference.py:154-161` returns any uppercase candidate before whole-message and cue-pattern checks.
- `financial-engine_v2/cockpit/core/chat.py:1204-1208` uses `detect_primary_ticker(...)` for chat ticker resolution.
- `financial-engine_v2/cockpit/core/tool_executor.py:712-714` uses the same detector for news ticker inference.
- `financial-engine_v2/backend/app/services/query_orchestrator.py:383-384` and `financial-engine_v2/backend/app/services/tenn_chat.py:101-105` also route through the shared detector.

Current probe evidence:

- Exact Gemini prompt returns `UI` from shared detection, `ChatController._detect_ticker(...)`, backend query-orchestrator entity resolution, backend Tenn chat ticker resolution, and `ToolExecutor._infer_news_ticker(...)`.
- `UI_AUDIT_GEMINI what should I review across holdings watchlist and recent news` does not return a ticker in current code.
- `what should I review across holdings watchlist and recent news` does not return a ticker.
- `UI AUDIT GEMINI ...` and punctuation-split variants do return `UI`, showing that marker/session tokens can still trigger the same failure if tokenized into standalone uppercase words.
- `ASX:UI news`, `$UI news`, and `UI.AX news` still route as explicit ticker forms and must remain valid if a remediation is later implemented.

## Classification

The failure is a class-wide ticker intent issue:

- Standalone uppercase acronyms in ordinary analyst prose can outrank contextual intent.
- News ticker inference and chat ticker resolution share the same detector, so the false ticker can flow into a current-news no-hit path and action proposal.
- The existing regression tests cover generic conversational false positives and common uppercase words, but they do not cover UI/session/audit markers or the phrase `Cockpit UI`.

## Remediation Guidance

Do not close #119 from this audit alone.

The next safe implementation task should add focused regression coverage for:

- exact Gemini prompt with `Cockpit UI`;
- audit/session marker variants with spaces or punctuation;
- ordinary cross-surface review prompts across holdings, watchlist, and recent news;
- explicit ticker requests such as `BHP news`, `ASX:UI news`, `$UI news`, and `UI.AX news`.

The implementation should preserve explicit ticker routing while preventing unsupported uppercase acronyms in UI/audit/session language from becoming ticker scope. A one-off hidden alias should not be treated as sufficient unless tests prove explicit ticker routes still work and the broader uppercase-acronym class is covered.

## DATA_MISSING

- A live browser `/full-chat` replay was not run in this audit because the task is report-only and starting UI/backend/model services would widen collision risk.
- Whether `UI` is a valid external market ticker was not treated as authoritative financial truth in this audit; explicit ticker forms are still listed as routes to preserve.
