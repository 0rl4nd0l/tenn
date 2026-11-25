# Cockpit session access

Chat commands on the cockpit `c` screen. They run before a normal reply. Web, RAG, and SQL flags live on the running process. They are not written to `memory.state_db`. Quitting cockpit and starting it again restores the defaults below.

A plain-language phrase is rewritten only when the message does not already start with `/`. The rewriter in `cockpit/core/conversation_commands.py` checks access phrases before watchlist, alert, and changes phrases. The first match wins.

## Defaults

| Scope | Starts | Config |
| --- | --- | --- |
| Web | Off | `web.enabled_default` in `config/cockpit.yaml` (checked-in value `false`). `--no-web` forces that default off and sets `runtime.no_web`. |
| RAG | On only when a reader was built | `rag.enabled` must be true. A company reader also needs `rag.qualitative_context.db_path`. A news reader is added when `resolve_news_context_db_path` returns a file. |
| SQL diagnostics | Off | `db.diagnostic_query_enabled` (checked-in value `false`). |
| Actions | Read/write with confirmation | `--read-only` flips the actions line to read-only. It does not turn web, RAG, or `/sql` off. |

`/access` prints one block for every scope: web on/off, the `--no-web` lock when set, RAG on/off, `unavailable` when no reader exists, company and news DB paths, corpus filters, news ticker mode, SQL on/off, and the actions mode. `/web`, `/rag`, and `/dbdiag` with no extra token, and the same commands with `status`, print that same block.

RAG startup is separate from the session flag. `ToolRouter.qual_context_enabled` starts true when a company or news reader object exists. `build_qual_context_reader` calls `validate_runtime()`, which raises if the SQLite file is missing. With the checked-in config (`rag.enabled: true`, company DB `reports/qual_context/company.sqlite`, news DB `reports/qual_context/news.sqlite` and `news_context.enabled: true`), a missing file stops cockpit during startup. The "RAG unavailable" reply is for a process that started with no reader, for example `rag.enabled` false or an empty company `db_path` and no news file.

## Commands

| Input | Effect |
| --- | --- |
| `/access`, `/access status` | Print the status block. |
| `/web on`, `/rag on`, `/dbdiag on` | Turn that scope on immediately. No `/confirm`. |
| `/web off`, `/rag off`, `/dbdiag off` | Turn that scope off immediately. |
| `/request-access web`, `/request-access rag`, `/request-access dbdiag` | Store a pending enable. Nothing changes until `/confirm`. |
| `/sql tables` | List tables in the financial database. Requires SQL on. |
| `/sql <SELECT or WITH ...>` | Run one read-only statement. Optional `max_rows=N`. |
| `/confirm` | Apply the pending access change, or run a pending cockpit action. |
| `/cancel` | Drop the pending action. |

`/request-access` accepts only that one scope word after the command. `/request-access web please` prints `usage: `/request-access web|rag|dbdiag`` and does not store a pending action. The command always asks to enable. Turning a scope off is the matching `off` command.

`/web on now` is not the on command. The on and off lines are exact after the message is stripped and lowercased. `/Web On` matches. Extra words do not.

## Plain language

| Typed text | Becomes |
| --- | --- |
| `what access do you have`, `show access`, `show permissions` | `/access` |
| `access status`, `permissions state` | `/access` |
| `enable web`, `turn on web`, `allow web`, `grant web` | `/request-access web` |
| `disable web`, `turn off web`, `block web` | `/web off` |
| `turn on rag`, `enable qualitative context` | `/request-access rag` |
| `turn off rag`, `disable qualitative context` | `/rag off` |
| `enable sql diagnostics`, `enable database diagnostic` | `/request-access dbdiag` |
| `disable dbdiag` | `/dbdiag off` |

The enable verbs have to appear before the scope word. `web enable` stays a normal chat message. `current access` does not match the status pattern, because `access` has to come before `status`, `state`, `have`, or `current`.

`show alerts and enable web` becomes `/request-access web`. The access rule runs first.

## When chat asks before answering

These prompts come from `ChatController.build_chat_response`. They are skipped when the message was already handled as a slash command. Earlier short-circuits also skip them: a detected cockpit action, smalltalk, a ticker-universe question, a global announcement question, a historical price question, and a current price question. A current price question is one that names a ticker and includes `price`, `quote`, `chart`, `historical`, `history`, `close`, `traded`, or `trading`, and does not include `full analysis`, `deep analysis`, `company brief`, `valuation`, or `moat`. `price BHP` skips the access gates. `deep analysis price BHP` does not, because `deep analysis` removes it from the price short-circuit and gate 1 asks for web.

For everything else, the first matching gate wins:

1. Structured analysis, deep mode, a ticker, and web still off. Reply asks to enable web enrichment. Pending scope is `web`. Analysis does not run.
2. The text contains `http://` or `https://`, the message is treated as analysis, and web is off. A ticker is not required. Pending scope is `web`. A current price question is still handled earlier, so `price BHP https://example.com` does not ask for web access.
3. Deep mode, a ticker, at least one qualitative reader, and RAG still off. Pending scope is `rag`. This is reached only after web is already on, because gate 1 returns first.
4. Operational mode (not deep), a ticker, web off, and a full-report phrase such as `analyse`, `analysis`, `valuation`, or `full report`. The reply offers optional web access. The pending action is that web enable only when announcement sync does not also attach an update. See the confirm collision below.

The UI marks the message deep before that call when the chat mode is already deep, or when the text contains an explicit marker (`deep analysis`, `analyse in depth`, `analyze in depth`, `in-depth analysis`, `full scale analysis`, `full-scale analysis`, `extreme analysis`). With auto-deep left on (the default), these also force deep for that message: `in depth`, `detailed analysis`, `comprehensive analysis`, `thorough analysis`, `full analysis`, `full-scale`. `/auto-deep off` leaves only the explicit markers and the current mode.

Deep mode with web already on and RAG already on does not stop for access. It continues into local context and, for a structured analysis, web retrieval.

## Confirm, cancel, and resume

While a pending action is stored, the exact words `yes`, `y`, `ok`, `okay`, `no`, `n`, and `cancel` are rewritten. The first four become `/confirm`. The last three become `/cancel`. `okay please` is not rewritten. With no pending action, `ok` stays a normal message and the chat layer treats `ok` and `okay` as smalltalk.

`/confirm` and `/cancel` themselves are matched in that exact lowercase form. `/CONFIRM` is not rewritten, because messages that already start with `/` skip the rewriter, and it is not equal to `/confirm`.

Confirm of `__access_request__` calls the same applicator as `/web on`. On success:

- Web: `web fetch enabled for this session.`
- RAG: also sets `tool_router.qual_context_enabled`, which is what later chat checks. `rag qualitative context enabled for this session.`
- SQL: `db diagnostic query mode enabled. Use `/sql tables` or `/sql <select ...>`.`

Failures leave the flag unchanged:

- `/web on` while `--no-web` is set returns `web is hard-disabled by runtime flag (--no-web). Restart cockpit without --no-web to enable.`
- `/rag on` with no reader returns `rag is unavailable in this runtime (qualitative context backend not configured).`

Auto-resume runs only for a pending access enable that chat built from the question you just typed. The payload keeps that question as `resume_message`. After a successful enable, cockpit waits until the current chat turn finishes, up to 3 seconds, then submits that question again. If the turn is still in flight, the reply is `Access was approved, but automatic resume timed out. Please resend your previous request.`

`/request-access` does not store `resume_message`. Confirm enables the scope and does not re-run an earlier question. A disable, a failed enable, and a non-access action do not auto-resume.

A second deep-analysis pass can stop again. Web is gate 1 and RAG is gate 3, so the usual chain with both off is: confirm web, the question is submitted again, confirm RAG, the question is submitted again, then analysis runs. If RAG was already on at startup, the second stop does not happen.

Confirm collision on operational analysis: when the sync check wants an update, its preview replaces the optional web preview. Sync wants an update when the ticker has no indexed announcements, none of the timestamps parse, or the newest timestamp is strictly older than 168 hours (96 hours if the message contains `latest`, `recent`, `today`, `yesterday`, `announcement`, `announcements`, `news`, `update`, or `updates`). Age equal to the threshold does not offer an update. The reply can still include the sentence that says `/confirm` approves web. `/confirm` runs the stored preview, which is `update_ticker_financials` with `years=1` and `process_documents=True` when that preview is present. `/cancel` drops it and does not enable web.

`/confirm` with nothing pending writes `No pending action.` to the chat log and does not append that line to chat history.

## What an enabled scope can reach

Web fetches run only from a structured analysis, and only when the session flag is on.

- A message that contains a URL fetches the first `http://` or `https://` token. Deep mode passes the full response body. Operational mode keeps the first 8000 characters. The client follows redirects, uses a 20 second timeout, and sends `User-Agent: FinancialEngineCockpit/1.0`.
- Deep mode with a ticker and no URL searches DuckDuckGo HTML. The query is the ticker plus `ASX announcements latest results filings investor update market news` and the message clipped to 140 characters. It requests 4 results, keeps 3500 characters of text per page, and records `strict_official` on the payload. That flag does not drop other hosts. `asx.com.au` is inserted into the preferred-domain list, and those domains are ranked ahead of the rest. Preferred domains collected for the ticker are included too.

RAG retrieval runs inside `gather_local_context` when `qual_context_enabled` is true and a reader exists. `/rag off` leaves the reader objects in place and stops queries until `/rag on`.

`/sql` uses the financial engine database from `DATABASE_URL`. The cockpit default is `sqlite:///./data/fe_local.db`, resolved under the financial-engine root. It does not query `memory.state_db` or the RAG SQLite files. `--read-only` does not block it.

`/sql tables` runs, on a `sqlite:` URL:

```sql
select name as table_name from sqlite_master where type='table' order by name
```

On any other URL it reads `information_schema.tables`, excluding `information_schema` and `pg_catalog`.

Any other `/sql` text is one statement:

- Empty text prints `usage: `/sql tables` or `/sql <SELECT ...> [max_rows=N]``.
- The statement must start with `select ` or `with ` after lowercasing, including the space. Anything else fails here, including `pragma table_info(...)`, with `only SELECT/CTE read queries are allowed`.
- Length limit is 4000 characters.
- `;`, `--`, `/*`, and `*/` are rejected with `only single-statement queries without comments are allowed`.
- These whole words are rejected with `query contains blocked SQL token`: `insert`, `update`, `delete`, `drop`, `alter`, `create`, `grant`, `revoke`, `truncate`, `attach`, `detach`, `vacuum`, `pragma`, `replace`, `merge`, `call`, `execute`, `copy`, `refresh`, `analyze`, `reindex`. The scan does not skip quotes, so `where title = 'update'` is rejected.
- `max_rows` defaults to 50. A trailing ` max_rows=N` is clamped to 1 through 500. An unparsable value keeps 50 and still drops that suffix from the SQL.
- The result flag `truncated` is true when the fetched row count is at least the limit, including when the result ends exactly on the limit.
- The chat log shows JSON clipped at 14000 characters. The stored assistant history line is `/sql executed ok=<bool> rows=<count>`, not the rows.

## Pitfalls

- Session flags reset on every cockpit start. A confirmed `/request-access web` does not edit `cockpit.yaml`.
- `--no-web` cannot be overridden from chat. Restart without that flag.
- Missing company or news SQLite files fail startup under the checked-in RAG config. They do not come up as a disabled RAG toggle.
- Plain language `enable web` waits for `/confirm`. Plain language `disable web` turns web off immediately.
- `ok` while a financial update is pending confirms that update.
- An operational `analyse TICKER` can print a web-access offer and still confirm an announcement update instead.
- `/sql` can read any `SELECT` the database user can read, including rows outside the ticker you were discussing. The guard blocks extra statements and the listed words, including those words inside a quoted string. It does not apply row-level filters.
