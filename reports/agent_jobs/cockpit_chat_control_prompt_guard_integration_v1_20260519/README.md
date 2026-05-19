# Cockpit Chat Control Prompt Guard Integration

## Confirmed Facts

- Runtime path: `/home/l4nd0/tenn-runtime` resolves to `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`.
- Active branch: `migration/clean-runtime-baseline-reconstruct-v1`.
- Pre-integration HEAD: `2e73de32ac77`.
- Required base gate passed: `git merge-base --is-ancestor 2e73de32ac77 HEAD` returned success.
- Task card validation passed with `ok: true`.
- Registry `list-active` returned `active_jobs: []`.
- Registry `check-overlap` returned `ok: false` only because three unrelated untracked task cards were already dirty outside this task card:
  - `docs/agent_tasks/cockpit_chat_control_prompt_guard_tests_v1_20260519.md`
  - `docs/agent_tasks/cockpit_chat_orchestration_side_effect_audit_v1_20260519.md`
  - `docs/agent_tasks/gold_metric_coverage_audit_v1_20260519.md`
- No source-code dirt existed before integration.
- The isolated worktree exists at `/home/l4nd0/tenn-cockpit-chat-control-prompt-guard-v1-20260519`.
- The isolated branch is `safe/cockpit-chat-control-prompt-guard-v1-20260519`.

## Inferred Facts

- The isolated patch was left as uncommitted working-tree changes in the isolated worktree. `git diff 2e73de32ac77..safe/cockpit-chat-control-prompt-guard-v1-20260519` was empty because the branch HEAD was still `2e73de32ac77`.
- The safe transfer path used was manual working-tree diff transfer from the isolated checkout, limited to the four allowed source/test files.
- The registry was not claimed because the local dirty task-card artifacts made the registry overlap gate non-clean even though no active jobs existed.

## DATA_MISSING

- The isolated branch does not contain a committed patch diff against `2e73de32ac77`; the evidence source is the isolated worktree dirty diff.
- The exact final commit hash cannot be self-recorded inside this report file before creating the commit that contains it. The Codex closeout records the post-commit hash.
- The architecture-check skill rule files `.cursor/rules/00_mandatory_index.md`, `.cursor/rules/backend_architecture.md`, `.cursor/rules/embedding_rules.md`, `.cursor/rules/vector_store_invariants.md`, and `.cursor/rules/failure_policy.md` are absent in this checkout.

## Files Integrated

- `financial-engine_v2/backend/app/routes/cockpit_api.py`
- `financial-engine_v2/backend/app/services/cockpit_auto_flagger.py`
- `financial-engine_v2/backend/tests/test_cockpit_api_chat_stream.py`
- `financial-engine_v2/backend/tests/test_cockpit_auto_flagger.py`

The isolated task/report artifact `docs/agent_tasks/cockpit_chat_control_prompt_guard_tests_v1_20260519.md` was not integrated.

## Diff Summary

The isolated working-tree source/test diff was:

```text
financial-engine_v2/backend/app/routes/cockpit_api.py             | 10 ++++
financial-engine_v2/backend/app/services/cockpit_auto_flagger.py  | 21 ++++++++-
financial-engine_v2/backend/tests/test_cockpit_api_chat_stream.py | 54 ++++++++++++++++++++++
financial-engine_v2/backend/tests/test_cockpit_auto_flagger.py    | 36 +++++++++++++++
4 files changed, 120 insertions(+), 1 deletion(-)
```

The runtime copies of all four files matched the isolated worktree copies after transfer (`diff -u` returned no differences for each file).

## Safety Guard Preserved Evidence

- `Reply exactly: ok` is now exempted narrowly by `_CONTROL_LITERAL_CHAT_MESSAGE_RE` and may return `ok` without route-level visible-source refusal.
- The exemption only matches literal control/ack forms such as reply/respond/say exactly/with plus a small fixed acknowledgement vocabulary.
- Substantive prompts still reach the visible-source requirement path.
- Auto-flagger `missing_sources` findings are suppressed only for guard-only literal control prompts with no tool audit, evidence, tool traces, or status events.
- Substantive missing-visible-source turns still produce `missing_sources`.
- No source-label semantics, provenance source item logic, runtime/model routing, Home, news, memory, extraction, Qdrant, or financial truth code was touched.

## Tests And Validation

- Focused proving set:

```text
financial-engine_v2/.venv/bin/pytest -q \
  financial-engine_v2/backend/tests/test_cockpit_api_chat_stream.py::test_cockpit_chat_non_stream_allows_control_prompt_ok_without_sources \
  financial-engine_v2/backend/tests/test_cockpit_api_chat_stream.py::test_cockpit_chat_stream_blocks_substantive_answer_without_sources \
  financial-engine_v2/backend/tests/test_cockpit_auto_flagger.py::test_detect_auto_flag_findings_catches_substantive_missing_visible_sources \
  financial-engine_v2/backend/tests/test_cockpit_auto_flagger.py::test_detect_auto_flag_findings_ignores_control_prompt_missing_visible_sources_only
....                                                                     [100%]
4 passed in 2.42s
```

- Full touched backend test files:

```text
financial-engine_v2/.venv/bin/pytest -q \
  financial-engine_v2/backend/tests/test_cockpit_api_chat_stream.py \
  financial-engine_v2/backend/tests/test_cockpit_auto_flagger.py
...............................................................          [100%]
63 passed in 5.28s
```

- `git diff --check`: passed with no output.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/cockpit_chat_control_prompt_guard_integration_v1_20260519.md`: `ok: false` only due the three unrelated pre-existing untracked task cards listed above.

## Code Review

Code-reviewer pass found no critical, warning, or suggestion findings in the scoped diff. Inputs reviewed were the four modified source/test files and their `git diff`.

## Validation Match

Validation matches the isolated patch behavior:

- focused proving set: 4 passed;
- full touched backend files: 63 passed;
- source/test diff copied exactly from the isolated worktree;
- `git diff --check` clean.

## Changed File Boundary

The only non-report/non-task files changed by this integration are the four allowed source/test files. The only unrelated dirty files observed were pre-existing untracked task cards under `docs/agent_tasks/`.

## Commit

- Commit hash: DATA_MISSING until after commit creation; final Codex closeout records the hash.
- Intended commit message: `fix(query): allow cockpit control prompts without source refusal`.

## Final Git Status

Post-commit status:

```text
?? docs/agent_tasks/cockpit_chat_control_prompt_guard_tests_v1_20260519.md
?? docs/agent_tasks/cockpit_chat_orchestration_side_effect_audit_v1_20260519.md
?? docs/agent_tasks/gold_metric_coverage_audit_v1_20260519.md
```

Those three untracked task cards were pre-existing unrelated dirt and were not staged or committed.

## Registry Release Status

- Registry was not claimed.
- Release status: not applicable.
- Final `list-active` showed one active non-overlapping Memory-lane job:
  - `memory_contamination_root_cause_audit_v1_20260519`
  - lane: `Memory`
  - worktree: `/home/l4nd0/tenn-memory-contamination-root-cause-audit-v1-20260519`

## Project Memory Save Recommendation

Save a memory note that this integration used the active NVMe runtime baseline at `2e73de32ac77`, copied the validated Cockpit control-prompt guard from the isolated worktree dirty diff rather than a branch commit, preserved substantive visible-source refusal, and left unrelated untracked task-card dirt untouched.
