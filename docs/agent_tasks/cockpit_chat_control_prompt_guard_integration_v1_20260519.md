---
job_id: cockpit_chat_control_prompt_guard_integration_v1_20260519
lane: Query Orchestration
owner: Codex
allowed_files:
  - docs/agent_tasks/cockpit_chat_control_prompt_guard_integration_v1_20260519.md
  - financial-engine_v2/backend/app/routes/cockpit_api.py
  - financial-engine_v2/backend/app/services/cockpit_auto_flagger.py
  - financial-engine_v2/backend/tests/test_cockpit_api_chat_stream.py
  - financial-engine_v2/backend/tests/test_cockpit_auto_flagger.py
  - reports/agent_jobs/cockpit_chat_control_prompt_guard_integration_v1_20260519/
  - reports/agent_jobs/cockpit_chat_control_prompt_guard_integration_v1_20260519/README.md
  - reports/agent_jobs/cockpit_chat_control_prompt_guard_integration_v1_20260519/diff-check.json
approval_required: false
timeout_seconds: 7200
output_dir: reports/agent_jobs/cockpit_chat_control_prompt_guard_integration_v1_20260519
mutation_mode: safe_extension
production_data_access: false
allow_unapproved_safe_extension: true
---

# Task

Integrate the already-validated Cockpit chat control-prompt guard patch from the isolated safe-extension worktree into the active NVMe runtime baseline.

# Source Patch

- Worktree: `/home/l4nd0/tenn-cockpit-chat-control-prompt-guard-v1-20260519`
- Branch: `safe/cockpit-chat-control-prompt-guard-v1-20260519`
- Base HEAD: `2e73de32ac77`

# Scope

Only integrate the narrow route-layer and auto-flagger guard changes needed for source-free literal control/ack prompts such as:

- `Reply exactly: ok`
- `respond with pong`
- `say exactly done`

Do not redesign Cockpit chat. Do not broaden source guard behavior. Do not touch runtime/model/GPU/Home/provenance/news/memory/extraction/financial truth.

# Required Preflight

Run and report:

- `cd /home/l4nd0/tenn-runtime`
- `readlink -f /home/l4nd0/tenn-runtime`
- `git branch --show-current`
- `git rev-parse --short=12 HEAD`
- `git status --short`
- `git worktree list`
- `git show --stat --oneline --no-renames HEAD`
- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/cockpit_chat_control_prompt_guard_integration_v1_20260519.md`
- `python3 scripts/agent_job_registry.py list-active --repo-root /home/l4nd0/tenn-runtime`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/cockpit_chat_control_prompt_guard_integration_v1_20260519.md --repo-root /home/l4nd0/tenn-runtime`

Claim the registry job only if safe.

# Hard Stops

Stop before integration if:

- active registry shows overlapping Query Orchestration / Cockpit chat work;
- `/home/l4nd0/tenn-runtime` has source-code dirt beyond known untracked task/report artifacts;
- active branch is not `migration/clean-runtime-baseline-reconstruct-v1`;
- HEAD is not at or after `2e73de32ac77`;
- the isolated worktree is missing;
- the isolated patch cannot be compared cleanly;
- integration would require touching files outside the allowed list.

# Integration Method

Prefer the smallest safe transfer from the isolated worktree. Inspect the isolated branch diff before applying:

- `git diff --name-status 2e73de32ac77..safe/cockpit-chat-control-prompt-guard-v1-20260519`
- `git diff --stat 2e73de32ac77..safe/cockpit-chat-control-prompt-guard-v1-20260519`

Apply only the allowed source/test file patch. Do not integrate the isolated worktree task/report artifacts.

# Patch Requirements

- Literal control/ack prompts may bypass route-level visible-source refusal.
- The exemption must remain narrow and source-free.
- Arbitrary unsupported financial claims must not bypass the source guard.
- Substantive financial/source-dependent prompts without visible sources must still be refused.
- Auto-diagnostic `missing_sources` findings must still fire for substantive/source-dependent missing-source turns.
- Guard-only literal control prompts must not create noisy auto-diagnostic findings by themselves.
- Source-label semantics and provenance safety must not be weakened.

# Validation

Run the focused proving set, the full touched backend test files, `git diff --check`, and:

`python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/cockpit_chat_control_prompt_guard_integration_v1_20260519.md`

Do not run live `/api/cockpit/chat` smoke, runtime restart, model reload, Home producer jobs, Qdrant/news backfills, extraction jobs, or production data mutations.

# Required Report

Write:

`reports/agent_jobs/cockpit_chat_control_prompt_guard_integration_v1_20260519/README.md`

Include confirmed facts, inferred facts, DATA_MISSING, source isolated worktree and branch, files integrated, diff summary, tests run and exact results, safety guard preserved evidence, whether validation matches isolated patch, whether source files were the only non-report files changed, commit hash if committed, final git status, registry release status, and Project Memory save recommendation.
