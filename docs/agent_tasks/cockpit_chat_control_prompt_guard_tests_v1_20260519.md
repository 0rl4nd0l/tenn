---
job_id: cockpit_chat_control_prompt_guard_tests_v1_20260519
lane: Query Orchestration
owner: Codex
allowed_files:
  - docs/agent_tasks/cockpit_chat_control_prompt_guard_tests_v1_20260519.md
  - reports/agent_jobs/cockpit_chat_control_prompt_guard_tests_v1_20260519/
  - financial-engine_v2/backend/app/routes/cockpit_api.py
  - financial-engine_v2/backend/app/services/cockpit_auto_flagger.py
  - financial-engine_v2/backend/tests/test_cockpit_api_chat_stream.py
  - financial-engine_v2/backend/tests/test_cockpit_auto_flagger.py
approval_required: false
timeout_seconds: 7200
output_dir: reports/agent_jobs/cockpit_chat_control_prompt_guard_tests_v1_20260519
mutation_mode: safe_extension
production_data_access: false
allow_unapproved_safe_extension: true
---

# Task

Add tests first for Cockpit `/api/cockpit/chat` source-free control/meta prompt behavior, then apply the smallest narrow patch only if the tests prove it is needed.

Do not weaken financial visible-source safety. Do not change runtime, model, GPU, routing policy, Home producers, data, memory, Qdrant, news, extraction/parser code, or financial truth.

# Context

The previous audit found that direct local APEX is stable and the issue is owned by the Cockpit route layer:

- route prompt envelope and metadata differ from direct `:8001`
- route-level `_enforce_visible_source_contract()` can replace model output with `grounding_guard: missing_visible_sources`
- auto diagnostics can flag `missing_visible_sources` and write `auto_diagnostic` artifacts
- generic/control prompt smokes such as `Reply exactly: ok` are route-smoke mismatches, not direct runtime failures

# Requirements

1. Work from `/home/l4nd0/tenn-cockpit-chat-control-prompt-guard-v1-20260519`.
2. Validate this task card.
3. Run registry `list-active` and `check-overlap` if supported.
4. Claim only if safe.
5. Add focused failing tests before implementation.
6. Patch only the minimum code required to pass those tests.
7. Preserve source/grounding safety for substantive financial claims without visible sources.
8. Do not run live Cockpit chat smoke or mutate runtime/data.

# Intended Tests

Add or update focused backend tests that prove:

- A source-free control/meta prompt like `Reply exactly: ok` with response text `ok` is not replaced by `missing_visible_sources`.
- A substantive financial claim without visible sources is still replaced by the visible-source refusal.
- Auto-flagging still catches `missing_visible_sources` for substantive/source-dependent turns.
- Generic/control prompt smoke responses do not create `auto_diagnostic` findings solely because the source guard was involved.

# Allowed Implementation Scope

Prefer the narrowest patch in:

- `financial-engine_v2/backend/app/routes/cockpit_api.py`
- `financial-engine_v2/backend/app/services/cockpit_auto_flagger.py`

Use tests in:

- `financial-engine_v2/backend/tests/test_cockpit_api_chat_stream.py`
- `financial-engine_v2/backend/tests/test_cockpit_auto_flagger.py`

# Required Output

Write a short report to:

`reports/agent_jobs/cockpit_chat_control_prompt_guard_tests_v1_20260519/README.md`

Include:

- tests added
- patch summary
- safety guard preserved
- validation commands run
- final git status
- registry release status
