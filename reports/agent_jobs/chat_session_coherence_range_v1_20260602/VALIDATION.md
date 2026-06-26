# Validation

Commands are run from
`/home/l4nd0/tenn-issue258-chat-session-coherence-range-v1-20260626` unless
noted otherwise.

| Command | Result |
| --- | --- |
| `python3 /home/l4nd0/.agents/skills/tenn-git-guard/scripts/tenn_git_guard.py preflight --repo-root /home/l4nd0/tenn-issue258-chat-session-coherence-range-v1-20260626 --topic "issue 258 chat session coherence range" --json` | pass |
| `python3 scripts/agent_job_registry.py list-active --read-only --repo-root .` | pass; no active jobs |
| `python3 scripts/agent_task_ledger.py --repo-root . search --issue 258` | pass; no matching entries, duplicate classification `UNKNOWN_ASK`; guard duplicate-work classification was `NO_MATCHING_ACTIVE_WORK_FOUND` |
| `python3 scripts/agent_job_contract.py validate docs/agent_tasks/chat_session_coherence_range_v1_20260602.md` | pass |
| `python3 scripts/agent_task_ledger.py --repo-root . append --fill-identity --entry-json ...` | pass; claim entry appended |
| `uv run --with-requirements financial-engine_v2/backend/requirements.txt --with-requirements financial-engine_v2/backend/requirements-dev.txt pytest -q financial-engine_v2/backend/app/services/tests/test_chat_quality_scorer.py::test_compute_session_coherence_negative_cosine_is_clamped` | red pass; failed before source fix with `assert 2.0 == 1.0` |
| `uv run --with-requirements financial-engine_v2/backend/requirements.txt --with-requirements financial-engine_v2/backend/requirements-dev.txt pytest -q financial-engine_v2/backend/app/services/tests/test_chat_quality_scorer.py` | pass; 8 passed |
| `uv run --with ruff ruff format --check financial-engine_v2/backend/app/services/chat_quality_scorer.py financial-engine_v2/backend/app/services/tests/test_chat_quality_scorer.py` | pass |
| `uv run --with ruff ruff check financial-engine_v2/backend/app/services/chat_quality_scorer.py financial-engine_v2/backend/app/services/tests/test_chat_quality_scorer.py` | pass |
| `python3 -m py_compile financial-engine_v2/backend/app/services/chat_quality_scorer.py financial-engine_v2/backend/app/services/tests/test_chat_quality_scorer.py` | pass |
| `git diff --check` | pass |
| `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/chat_session_coherence_range_v1_20260602.md --repo-root .` | pass; no disallowed files |
| `python3 scripts/agent_job_contract.py check-report-artifacts docs/agent_tasks/chat_session_coherence_range_v1_20260602.md --repo-root .` | pass after rerunning sequentially; the first parallel run raced `check-diff` before `diff-check.json` existed |
| `gh issue comment 258 --repo 0rl4nd0l/tenn --body ...` | pass; posted `https://github.com/0rl4nd0l/tenn/issues/258#issuecomment-4807361415` |
| `python3 scripts/agent_task_ledger.py --repo-root . append --fill-identity --entry-json ...` | pass; final `done` entry appended with `owner_boundary=true` |

## Notes

- The first full focused scorer test run after adding only the new test failed
  two pre-existing tests because they depended on real embedding runtime config
  and `OLLAMA_URL` was unset. The tests now stub embeddings directly, keeping
  the scorer validation deterministic and no-runtime.
- `uv` warned that it ignored the requirements file `--extra-index-url`; the
  focused tests still installed/resolved the required packages and passed.
