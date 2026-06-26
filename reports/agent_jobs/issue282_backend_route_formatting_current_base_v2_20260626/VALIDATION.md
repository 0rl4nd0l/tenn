# Validation

Commands were run from
`/home/l4nd0/tenn-issue282-backend-route-formatting-current-base-v2-20260626`.

| Command | Result |
| --- | --- |
| `pwd && git branch --show-current && git rev-parse HEAD && git remote -v && git status --short --untracked-files=all` | pass; current-base task worktree at `c237716e818feaf717e370be5ecf10da2faeabf4` |
| `python3 /home/l4nd0/.agents/skills/tenn-git-guard/scripts/tenn_git_guard.py preflight --repo-root /home/l4nd0/tenn-issue282-backend-route-formatting-current-base-v2-20260626 --topic "issue 282 backend route formatting current base v2" --json` | pass |
| `python3 scripts/agent_job_contract.py validate docs/agent_tasks/issue282_backend_route_formatting_current_base_v2_20260626.md` | pass |
| `python3 scripts/agent_job_registry.py list-active --read-only --repo-root .` | pass; no active jobs before claim |
| `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/issue282_backend_route_formatting_current_base_v2_20260626.md --repo-root .` | pass |
| `python3 scripts/agent_job_registry.py claim docs/agent_tasks/issue282_backend_route_formatting_current_base_v2_20260626.md --repo-root .` | pass |
| `python3 scripts/agent_task_ledger.py --repo-root . append --fill-identity --entry-json ...` | pass |
| `python3 scripts/agent_task_ledger.py --repo-root . validate` | pass |
| `python3 -m py_compile financial-engine_v2/backend/app/api/routes.py` | pass |
| `uv run --with ruff ruff format --check financial-engine_v2/backend/app/api/routes.py` | pass |
| `uv run --with ruff ruff check financial-engine_v2/backend/app/api/routes.py` | pass |
| `git diff --check` | pass |
| `uv run --with-requirements financial-engine_v2/backend/requirements.txt --with-requirements financial-engine_v2/backend/requirements-dev.txt python -m pytest -c financial-engine_v2/backend/pytest.ini financial-engine_v2/backend/tests/test_local_api_key.py financial-engine_v2/backend/tests/test_process_document_api.py financial-engine_v2/backend/tests/test_cursor_rule_compliance.py -q` | pass; 19 passed, 5 existing warnings |

GitHub validation is pending PR publication.

## Runtime Functionality Proof

No live runtime functionality is claimed. This task reformats source code only;
it does not start the backend, issue live API requests, or mutate runtime data.

| Field | Evidence |
| --- | --- |
| intended output | Readable, conventionally formatted `financial-engine_v2/backend/app/api/routes.py` with unchanged endpoint behavior. |
| live output location | Source file and focused test suite only; no live route output checked. |
| pre-run max timestamp or count | DATA_MISSING; no runtime output baseline was captured because no runtime was started or queried. |
| post-run max timestamp or count | DATA_MISSING; no runtime output was started or queried. |
| rows/files inserted or updated after run start | Files updated after run start: route source, task card, and report artifacts only. Runtime rows/files: zero. |
| readiness/gate status | LOCAL_FIX_VALIDATED_READY_TO_PUBLISH; GitHub checks and canonical merge containment pending. |
| exact command/query used | `py_compile`, `ruff format --check`, `ruff check`, `git diff --check`, and focused pytest route tests. No runtime query used. |
| result: WORKING / PARTIAL / BROKEN / DATA_MISSING | PARTIAL |
| remaining blocker | Publish PR, wait for green GitHub checks, verify canonical merge containment, then close issue #282 from live GitHub evidence. |
