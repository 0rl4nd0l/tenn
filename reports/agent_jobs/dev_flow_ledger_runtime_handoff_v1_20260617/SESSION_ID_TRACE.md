# Session ID Trace

## Safe Sources Checked

- `CODEX_THREAD_ID`: `019ed3df-4b31-7cd1-8ed8-8bc1981cb7c8`
- `TENN_AGENT_SESSION_ID`: `DATA_MISSING`
- `CODEX_SESSION_ID`: `DATA_MISSING`
- `OPENAI_SESSION_ID`: `DATA_MISSING`
- `CLAUDE_SESSION_ID`: `DATA_MISSING`
- `CODEX_GOAL_ID`: `DATA_MISSING`
- read-only `~/.codex/goals_1.sqlite` by explicit `CODEX_THREAD_ID`:
  `f7141898-80f6-4dcd-af60-9f4e0514fcba`

## Result

- `session_id`: `DATA_MISSING`
- `thread_id`: `019ed3df-4b31-7cd1-8ed8-8bc1981cb7c8`
- `codex_goal_id`: `f7141898-80f6-4dcd-af60-9f4e0514fcba`
- `source_session_ref`: `codex:thread:019ed3df-4b31-7cd1-8ed8-8bc1981cb7c8`

No session ID was invented. Registry lease fallback IDs are not treated as
Codex session or thread IDs.
