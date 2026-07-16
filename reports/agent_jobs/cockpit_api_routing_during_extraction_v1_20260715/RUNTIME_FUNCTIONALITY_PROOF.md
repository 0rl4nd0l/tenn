# Runtime Functionality Proof

| Field | Required evidence |
| --- | --- |
| intended output | Interactive Cockpit chat and non-metric/news LLM work use Anthropic while metric extraction retains the protected local model. |
| live output location | `POST /api/cockpit/chat`, returned routing metadata, backend `generate_json` metadata, Cockpit state DB, news memo file, and host llama-router journal. |
| pre-run max timestamp or count | `chat_messages=1535`, max `2026-05-16T06:46:26.786360+00:00`; `chat_sessions=75`, same max; `session_summaries=17`, max `2026-03-31 13:37:17`. |
| post-run max timestamp or count | Counts and maximum timestamps remained identical after both stateless proofs. |
| rows/files inserted or updated after run start | Zero Cockpit state rows; `news_memos.jsonl` retained mtime `2026-07-15T04:21:06.217573+00:00`, before proofs at `06:25:52Z` and `06:26:53Z`. |
| readiness/gate status | Backend health and chat readiness HTTP 200; normal analysis allowed; extraction inactive; token count zero; Celery active/reserved/scheduled empty. |
| exact command/query used | `docker compose --env-file .env.docker -f docker-compose.yml up -d --no-deps --force-recreate backend worker gpu_worker`; stateless `curl` requests to `/api/cockpit/chat`; backend `generate_json(...)`; read-only `SELECT COUNT(*), MAX(...)` SQLite queries; `journalctl --after-cursor`. |
| result | `WORKING` |
| remaining blocker | `none` for the approved routing scope; the pre-existing UI outage is a separate scope. |

result: WORKING
