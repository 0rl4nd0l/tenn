# DATA_MISSING And Degraded State Model

The evaluation spine should preserve absence and degraded behavior as typed facts. It should not flatten them into generic failures.

## Core States

| State | Meaning | Failure? | Notes |
| --- | --- | --- | --- |
| `DATA_MISSING` | Required evidence was unavailable, blocked, absent, or intentionally not collected. | Not automatically | Requires a code and reason. |
| `degraded_runtime` | Runtime responded or partially worked, but scope is limited or reliability is not proven. | Sometimes | Must include runtime surface and tested scope. |
| `no_hit` | A retrieval/source path returned no matching evidence. | Sometimes | Can be expected, stale, or a real coverage miss. |
| `context_only` | Evidence is context, memory, or background information, not verified support. | No | Must not become `claim_verified`. |
| `missing_required_evidence` | A required evidence category was absent for a claim/request. | Usually actionable | Keep separate from runtime failure. |
| `production_data_access_blocked` | The audit scope forbids live production DB/Qdrant/news/memory access. | No | Record as policy boundary. |
| `untrusted_memory` | Memory rows may be contaminated, stale, or unreviewed. | Risk state | Do not mix with Financial Truth. |
| `stale_artifact` | Artifact exists but is old, from another branch, or lacks current branch/HEAD metadata. | No | Needs refresh before current claim. |
| `test_blocked_environment` | Test cannot run because venv, pytest, service, network, or permission is unavailable. | No | Record command and missing prerequisite. |
| `route_expected_404` | Route is intentionally absent in this branch/profile. | No | Example: backend direct `/api/cockpit/home` in current route-parity report. |
| `expected_empty_state` | Empty data is the honest correct state. | No | Example: empty attention queue or no approved commentary. |

## Required Columns

Any table that stores evaluated behavior should include these fields or an equivalent link to `data_missing_items`:

- `state_code`
- `state_class`
- `description`
- `blocked_by_policy`
- `blocked_by_environment`
- `expected_empty_state`
- `degraded`
- `source_artifact_path`
- `followup_task`

## Encoding Rules

1. Missing live data due to audit boundaries is `production_data_access_blocked`, not a failed system.
2. A direct runtime smoke cannot clear Cockpit route degradation; store separate rows.
3. A route expected to be absent is `route_expected_404`, not route failure.
4. Empty but valid producer output is `expected_empty_state`.
5. No retrieval hit for a source-dependent query is `no_hit` and may also be `missing_required_evidence`.
6. Memory-derived context is `context_only` unless a separate verified source proves the claim.
7. Candidate, ambiguous, unsupported, and missing-evidence metric labels are inventory states, not extractor failures.
8. Stale or branch-mismatched artifacts may be indexed, but current verdict queries must filter or label them as `stale_artifact`.

## Suggested Codes

| Code | Class | Example |
| --- | --- | --- |
| `REPORT_DIR_MISSING` | `DATA_MISSING` | Expected historical report directory absent. |
| `SCORECARD_ARTIFACT_MISSING` | `DATA_MISSING` | Expected real-gold result JSON missing in checkout. |
| `BRANCH_HEAD_MISSING` | `DATA_MISSING` | Markdown-only report lacks branch/HEAD. |
| `RUNTIME_METADATA_MISSING` | `DATA_MISSING` | Eval artifact lacks model/runtime/parser metadata. |
| `SOURCE_LABEL_STATE_MISSING` | `DATA_MISSING` | Trace lacks final source-label evidence. |
| `PRODUCTION_DATA_ACCESS_BLOCKED` | `production_data_access_blocked` | Static A2M audit did not query live Qdrant. |
| `ROUTE_EXPECTED_404` | `route_expected_404` | Direct backend route intentionally absent. |
| `EXPECTED_EMPTY_STATE` | `expected_empty_state` | Empty attention queue is READY. |
| `NO_HIT` | `no_hit` | News retrieval returns no local news context. |
| `MISSING_REQUIRED_EVIDENCE` | `missing_required_evidence` | Source guard refuses source-free answer. |
| `UNTRUSTED_MEMORY` | `untrusted_memory` | Active memory rows require review. |
| `TEST_ENV_BLOCKED` | `test_blocked_environment` | System Python lacks pytest. |
| `STALE_ARTIFACT` | `stale_artifact` | Historical baseline lacks current HEAD. |

## Query Semantics

For dashboards:

- "Failures" should count explicit failed checks only.
- "Blocked" should count `test_blocked_environment` and policy blocks separately.
- "Missing evidence" should count `DATA_MISSING` rows separately from failures.
- "Honest partial" should include degraded and expected-empty rows with their exact codes.
- "Canonical pass" must exclude non-canonical scorecards and stale artifacts unless explicitly requested.
