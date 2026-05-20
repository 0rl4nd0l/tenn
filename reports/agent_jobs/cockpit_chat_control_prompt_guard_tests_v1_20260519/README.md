# Cockpit Chat Control Prompt Guard Tests

Job: `cockpit_chat_control_prompt_guard_tests_v1_20260519`
Mode: `safe_extension`
Worktree: `/home/l4nd0/tenn-cockpit-chat-control-prompt-guard-v1-20260519`
Branch: `safe/cockpit-chat-control-prompt-guard-v1-20260519`
Base HEAD: `2e73de32ac77`

## Scope

This task was moved from `/home/l4nd0/tenn-runtime` into a clean isolated worktree because the runtime checkout had an unrelated untracked prior audit task card outside this job's allowed files. No runtime services, model/GPU config, Home producers, data, memory, Qdrant, news, extraction/parser code, or financial truth were changed.

## Tests Added First

- `financial-engine_v2/backend/tests/test_cockpit_api_chat_stream.py::test_cockpit_chat_non_stream_allows_control_prompt_ok_without_sources`
  - Proves a source-free literal control prompt (`Reply exactly: ok`) can deliver `ok` without route-level `missing_visible_sources` replacement.
- `financial-engine_v2/backend/tests/test_cockpit_auto_flagger.py::test_detect_auto_flag_findings_catches_substantive_missing_visible_sources`
  - Proves substantive/source-dependent turns still produce `missing_sources` diagnostics.
- `financial-engine_v2/backend/tests/test_cockpit_auto_flagger.py::test_detect_auto_flag_findings_ignores_control_prompt_missing_visible_sources_only`
  - Proves a guard-only literal control prompt does not create an auto-diagnostic finding by itself.

The new tests were run before implementation. The focused run failed as expected:

- Route test failed because `ok` was replaced with the visible-source refusal.
- Auto-flagger test failed because a guard-only control prompt produced `missing_sources` and follow-on inability diagnostics.

## Patch Summary

- `financial-engine_v2/backend/app/routes/cockpit_api.py`
  - Added `_CONTROL_LITERAL_CHAT_MESSAGE_RE`.
  - `_message_requires_visible_sources()` now exempts only literal acknowledgement/control prompts such as `Reply exactly: ok`, `say exactly ok`, `respond with pong`.
- `financial-engine_v2/backend/app/services/cockpit_auto_flagger.py`
  - Added matching `_CONTROL_LITERAL_PROMPT_RE`.
  - Suppresses only `missing_sources` auto-flag creation when the turn is a source-guard-only literal control prompt with no tool audit, evidence, tool traces, or status events.

## Safety Guard Preserved

The substantive no-source guard remains intact. Existing and new tests confirm that a substantive request like `tell me about BHP` without visible sources is still replaced by the visible-source refusal and that substantive `grounding_guard: missing_visible_sources` still produces auto-flag findings.

The new route exemption is deliberately narrower than the existing generic/control prompt detector: it only matches literal acknowledgement outputs, not arbitrary `reply exactly ...` financial statements.

## Validation Commands Run

Initial clean-worktree preflight:

- `pwd`
- `git branch --show-current`
- `git rev-parse --short=12 HEAD`
- `git status --short`
- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/cockpit_chat_control_prompt_guard_tests_v1_20260519.md`
- `python3 scripts/agent_job_registry.py list-active --repo-root /home/l4nd0/tenn-cockpit-chat-control-prompt-guard-v1-20260519`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/cockpit_chat_control_prompt_guard_tests_v1_20260519.md --repo-root /home/l4nd0/tenn-cockpit-chat-control-prompt-guard-v1-20260519`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/cockpit_chat_control_prompt_guard_tests_v1_20260519.md --repo-root /home/l4nd0/tenn-cockpit-chat-control-prompt-guard-v1-20260519`

Test commands:

- System `python3 -m pytest ...` was attempted first and was blocked by missing `pytest`.
- `uv run` was then used with `/usr/bin/python3.10` and a minimal temporary dependency set.
- First focused test run after adding tests failed as expected: 2 failed, 2 passed.
- Final focused test run passed: 4 passed.
- Full touched-file regression run passed: 63 passed.

Final successful command:

```bash
uv run --python /usr/bin/python3.10 \
  --with pytest==8.3.3 \
  --with pytest-asyncio==0.24.0 \
  --with fastapi==0.115.6 \
  --with httpx==0.27.2 \
  --with pydantic==2.9.2 \
  --with pydantic-settings==2.6.1 \
  --with SQLAlchemy==2.0.36 \
  --with requests \
  --with python-dateutil==2.9.0.post0 \
  --with pandas==2.2.3 \
  --with numpy==1.26.4 \
  --with exchange_calendars==4.6 \
  --with qdrant-client==1.12.1 \
  --with PyMuPDF==1.24.10 \
  python -m pytest \
  financial-engine_v2/backend/tests/test_cockpit_api_chat_stream.py \
  financial-engine_v2/backend/tests/test_cockpit_auto_flagger.py
```

Other validation:

- `git diff --check` -> clean.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/cockpit_chat_control_prompt_guard_tests_v1_20260519.md` -> `ok: true`, no disallowed files.

## Code Review

Post-change review found no critical findings, warnings, or suggestions. The patch is narrow, test-covered, and does not expose secrets or add runtime/data mutations.

## Final Git Status

- Clean isolated worktree status:
  - `M financial-engine_v2/backend/app/routes/cockpit_api.py`
  - `M financial-engine_v2/backend/app/services/cockpit_auto_flagger.py`
  - `M financial-engine_v2/backend/tests/test_cockpit_api_chat_stream.py`
  - `M financial-engine_v2/backend/tests/test_cockpit_auto_flagger.py`
  - `?? docs/agent_tasks/cockpit_chat_control_prompt_guard_tests_v1_20260519.md`
- Report artifacts are under ignored `reports/agent_jobs/cockpit_chat_control_prompt_guard_tests_v1_20260519/`:
  - `README.md`
  - `status.json`
  - `diff-check.json`
- `/home/l4nd0/tenn-runtime` was left untouched after the overlap failure. Its dirty task-card state remains unrelated to this isolated implementation lane.

## Registry Release Status

- `python3 scripts/agent_job_registry.py release cockpit_chat_control_prompt_guard_tests_v1_20260519 --repo-root /home/l4nd0/tenn-cockpit-chat-control-prompt-guard-v1-20260519` -> `ok: true`.
- Post-release `list-active` -> `active_jobs: []`.
