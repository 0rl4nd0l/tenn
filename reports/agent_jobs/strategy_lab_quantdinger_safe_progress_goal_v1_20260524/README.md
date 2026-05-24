# Strategy Lab QuantDinger Safe Progress Goal

Generated: 2026-05-24T11:15:00Z

## Result

Pushed Strategy Lab / QuantDinger forward within safe-extension bounds.

- Resolved the stale `strategy_lab_quantdinger_readonly_sidecar_online_v1_20260524` card as `SUPERSEDED_ARCHIVE_ONLY_DO_NOT_EXECUTE`.
- Added historical read-only smoke metadata to the Strategy Lab status route and Home card.
- Added repo-only artifact review references for the historical complete-and-next-phases milestone and the stronger read-only sidecar smoke proof.
- Added focused tests preventing historical smoke evidence from implying current runtime availability, real transport, live trading, paper order placement, store writes, or canonical financial truth.
- Added a non-executing future transport design.

## Repo State

- Branch: `migration/clean-runtime-baseline-reconstruct-v1`
- Worktree: `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`
- HEAD after implementation commit: `751dafdce39306196cab23a065e43123dd239e59`
- Parent task card: `docs/agent_tasks/strategy_lab_quantdinger_safe_progress_goal_v1_20260524.md`

## Commits Created

- `eb01cec2c723a7fc94fe106415ea14dd421aa140` - `milestone(reporting): supersede stale quantdinger sidecar card`
- `751dafdce39306196cab23a065e43123dd239e59` - `milestone(reporting): surface quantdinger readonly smoke history`
- Final report/design commit subject: `milestone(reporting): document quantdinger readonly transport path`

## Stale Sidecar-Online Decision

`docs/agent_tasks/strategy_lab_quantdinger_readonly_sidecar_online_v1_20260524.md` is now archive-only and must not be executed.

Reason: the draft had no matching report directory in this worktree and is superseded by commit `0ee837f7dc0706f1b0ff6d6c900522f4c2b43090`, `milestone(reporting): preserve quantdinger readonly smoke proof`. That later proof supports historical `SMOKE_PASSED / PENDING_REVIEW` only. It does not support `current_sidecar_available=true`.

## Strategy Lab / QD Map

- Status route: `cockpit-ui/app/api/cockpit/strategy-lab/status/route.ts`
- Status model/helper: `cockpit-ui/lib/strategy-lab-status.ts`, `cockpit-ui/lib/strategy-lab-status-server.ts`
- Artifacts route: `cockpit-ui/app/api/cockpit/strategy-lab/artifacts/route.ts`
- Artifacts model/helper: `cockpit-ui/lib/strategy-lab-artifacts.ts`, `cockpit-ui/lib/strategy-lab-artifacts-server.ts`
- Home cards: `cockpit-ui/components/cockpit/home/cards/strategy-lab-status-card.tsx`, `cockpit-ui/components/cockpit/home/cards/strategy-lab-artifacts-review-card.tsx`
- Focused tests: matching `*.test.ts` and `*.test.tsx` files for those model/card paths
- Full map: `reports/agent_jobs/strategy_lab_quantdinger_safe_progress_goal_v1_20260524/route_map.json`

## User-Visible Behavior

Strategy Lab Home now distinguishes:

- `HISTORICAL SMOKE PASSED`
- `PENDING REVIEW`
- `CURRENT SIDECAR OFFLINE`
- `READ ONLY`
- `NO LIVE TRADING`
- `NO PAPER ORDER PLACEMENT`
- `NO REAL TRANSPORT`
- `NO STORE WRITES`
- `NO CANONICAL FINANCIAL TRUTH`

Artifact review now shows historical report evidence with preserved commit references. The read-only smoke proof is visible as historical smoke proof, but its report file is still marked missing in the current worktree when absent.

## What QD Can Now Do

- Show historical read-only smoke status in Cockpit.
- Show that the current sidecar is offline.
- Show preserved QD evidence as repo-only artifact review context.
- Keep historical smoke proof separate from current runtime availability.

## What QD Still Cannot Do

- No broker connection.
- No live trading.
- No paper order placement.
- No market orders.
- No real QuantDinger transport integration.
- No current sidecar runtime availability.
- No DB, Qdrant, news, memory, store, parser routing, runtime/model, or canonical financial truth writes.

## Validation Summary

Passed:

- Parent task-card validation.
- JSON parse for `route_map.json`.
- Focused Vitest: `4 passed`, `7 tests passed`.
- Focused ESLint: passed with no output.
- `git diff --check`.
- Secret-pattern scan found only policy words such as `token`; no secret values were present.

Classified non-blocking:

- `registry check-overlap` failed because a separate active `Reporting` lane job exists and because existing foreign untracked task cards remain outside this task card. The active registry job did not own this goal's allowed files.
- Task-card `check-diff` failed because existing foreign untracked task cards remain outside this task card.
- Hook posture: without an active task card, `scripts/agent_job_hook.py` returned `{}`. With `TENN_AGENT_TASK_CARD` set to this card in no-write `BeforeTool` mode, the hook blocked for the same lane-overlap and foreign-dirt reasons, not because QuantDinger files were out of scope.

Browser smoke:

- Not run in this goal. The local Playwright config starts `pnpm run start` when no external base URL is supplied; no existing app server was provided, and this goal avoided persistent service startup.

## Remaining Foreign Dirt

Unrelated untracked task cards remain intentionally untouched:

- `docs/agent_tasks/chat_guard_canonical_review_and_csl_live_smoke_v1_20260524.md`
- `docs/agent_tasks/cockpit_chat_visible_evidence_gap_labels_live_reload_smoke_v1_20260524.md`
- `docs/agent_tasks/disk_pressure_safe_cleanup_audit_v1_20260524.md`
- `docs/agent_tasks/docker_builder_cache_broad_prune_v1_20260524.md`
- `docs/agent_tasks/pc_ssh_slow_safe_diagnostics_v1_20260524.md`
- `docs/agent_tasks/post_quantdinger_milestone_dirt_hygiene_audit_v1_20260524.md`
- `docs/agent_tasks/repo_native_orchestration_readiness_audit_v1_20260524.md`
- `docs/agent_tasks/strategy_lab_artifact_review_integration_readiness_v1_20260524.md`

## Remaining QD Risks

- Historical smoke proof is available by commit, but its report bundle is not checked out on this branch.
- No current live sidecar probe was performed.
- Real transport remains not integrated.
- Any future runtime smoke requires a separate approval-gated task card.

## Next Safe Goals

1. Preserve/archive `docs/agent_tasks/strategy_lab_artifact_review_integration_readiness_v1_20260524.md` as the next likely Strategy Lab-related dirt item.
2. If QD runtime work is desired, create a child task card for a loopback-only read/backtest smoke using the safety contract in `transport_design.md`.
3. If UI browser proof is desired, run a separate browser-smoke card against an existing app server or a bounded dev-server lifecycle.

## Project Memory Recommendation

Save the boundary: historical QD smoke may be surfaced as `SMOKE_PASSED / PENDING_REVIEW`, but current sidecar availability remains false unless a new approval-gated live runtime proof is produced.

## Fresh Session Recommendation

Recommended before runtime sidecar work. The next step is higher risk than this static metadata/reporting change.
