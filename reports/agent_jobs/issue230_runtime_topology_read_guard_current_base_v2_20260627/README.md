# Issue #230 Runtime Topology Read Guard V2

Status: DONE_WITH_RISK

## Summary

Replaced stale/conflicting PR #440 on current canonical base
`aa177c7c22f2651c64b5ddbab755333462cea2f8`.

Changes:

- Added `require_api_key` dependencies to Cockpit runtime-topology read routes:
  `/api/cockpit/config`, `/api/cockpit/models`, and `/api/cockpit/queue`.
- Preserved no-key local development behavior through the existing
  `require_api_key` contract.
- Added focused backend tests for dependency registration, fail-closed
  configured-key behavior, and authenticated success.
- Exported `withApiKey()` from the Cockpit API client and sent `X-API-Key` for
  guarded runtime-topology helper calls and direct config fetches.
- Added API-client test coverage for runtime-topology helper headers.
- Updated the backend API surface documentation.

No production DB, Qdrant, Redis, news, memory, source PDF, gold label,
extraction prompt, runtime/model/GPU/service config, dependency, lockfile, or
production data surface was mutated.

## Runtime Functionality Proof

| Field | Required evidence |
| --- | --- |
| intended output | Configured-key Cockpit runtime-topology read routes reject missing or wrong API keys before exposing config, model inventory, or queue state. |
| live output location | Backend route surface in `financial-engine_v2/backend/app/routes/cockpit_api.py`: `/config`, `/models`, `/queue` mounted under `/api/cockpit`. |
| pre-run max timestamp or count | DATA_MISSING; no live backend/browser baseline was captured because this lane used current-base route/test evidence only. |
| post-run max timestamp or count | DATA_MISSING; no live backend/browser post-run baseline was captured. |
| rows/files inserted or updated after run start | 0 runtime rows/files; source/tests/docs/report artifacts only. |
| readiness/gate status | Local backend tests, ruff, py_compile, task-card validate passed. Frontend Vitest/eslint are blocked locally by missing tools. GitHub checks pending until PR open. |
| exact command/query used | `PYTHONPATH=financial-engine_v2/backend uv run --with-requirements financial-engine_v2/backend/requirements.txt --with-requirements financial-engine_v2/backend/requirements-dev.txt python -m pytest -c financial-engine_v2/backend/pytest.ini financial-engine_v2/backend/tests/test_cockpit_api_models.py -q` |
| result: WORKING / PARTIAL / BROKEN / DATA_MISSING | PARTIAL |
| remaining blocker | No live backend/browser runtime was exercised; local frontend test/lint tools are missing. |

result: PARTIAL

## Current Gate

This is issue remediation with route-level proof only. It is not proof of a
deployed or running Cockpit runtime.
