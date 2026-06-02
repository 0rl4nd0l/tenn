# Cockpit Strategy Lab Route Guard

## Summary

Implemented issue #238 in Reporting lane on isolated branch `safe/cockpit-strategy-lab-route-guard-v1-20260602`, stacked on PR #268.

- Added Cockpit BFF API-key checks to `/api/cockpit/strategy-lab/status` and `/api/cockpit/strategy-lab/artifacts`.
- Wired the Strategy Lab Home status and artifact-review cards to send the configured browser/operator key.
- Generalized the shared BFF auth helper message from telemetry-specific wording to operator-route wording.
- Replaced raw guarded API links in the Strategy Lab status card with in-page anchors so normal browser navigation does not hit guarded JSON endpoints without headers.
- Preserved Strategy Lab truth boundaries: read-only, pending review, current sidecar unavailable, no trading, no canonical financial truth, no store writes.

## Scope And Contract

- Lane: Reporting
- Target layer: Client / Next.js BFF repo-evidence diagnostics
- Execution mode: SAFE EXTENSION
- Contested backend surfaces touched: none
- Collision risk: MEDIUM due adjacent open Strategy Lab PRs, with no unresolved active-job overlap
- GPU process check required: no; this task does not spawn, restart, or depend on llama-server or Strategy Lab/QuantDinger runtime

Relevant contract evidence:
- `docs/architecture/SYSTEM_CONTRACT.md` keeps Cockpit as client/orchestration only.
- `docs/architecture/21_cockpit_client_contract.md` treats Next.js BFF routes as presentation surfaces and documents `X-API-Key`.
- `docs/architecture/13_security_and_secrets.md` prohibits exposing or committing real keys.

## Issue And Overlap Evidence

- `gh issue view 238 --repo 0rl4nd0l/tenn` returned OPEN with acceptance criteria for Strategy Lab status/artifact route gating.
- Duplicate searches for `strategy lab status artifacts guard` and `api/cockpit/strategy-lab/status` returned #238 plus adjacent non-duplicate issues only.
- `gh pr list --repo 0rl4nd0l/tenn --state all --search "strategy lab status artifacts guard"` returned no duplicate PR.
- Open Strategy Lab PRs checked:
  - PR #183 touches `cockpit-ui/lib/strategy-lab-artifacts.test.ts` and a review-queue utility, but not the guarded routes or Home cards.
  - PR #134 and PR #159 touch adjacent Home/Strategy Lab surfaces, but not the same allowed files.
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/cockpit_strategy_lab_repo_artifact_route_guard_v1_20260602.md` returned `ok: true`, `issues: []`.

## Validation

Commands run from `cockpit-ui/` unless noted:

- `node_modules/.bin/vitest run lib/strategy-lab-status.test.ts lib/strategy-lab-artifacts.test.ts components/cockpit/home/cards/strategy-lab-status-card.test.tsx components/cockpit/home/cards/strategy-lab-artifacts-review-card.test.tsx lib/telemetry-route-access-guard.test.ts lib/cockpit-api-headers.test.ts`
  Result: PASS, 6 files, 21 tests.
- `node_modules/.bin/eslint 'app/api/cockpit/strategy-lab/status/route.ts' 'app/api/cockpit/strategy-lab/artifacts/route.ts' 'components/cockpit/home/cards/strategy-lab-status-card.tsx' 'components/cockpit/home/cards/strategy-lab-artifacts-review-card.tsx' 'components/cockpit/home/cards/strategy-lab-status-card.test.tsx' 'components/cockpit/home/cards/strategy-lab-artifacts-review-card.test.tsx' 'lib/strategy-lab-status.test.ts' 'lib/strategy-lab-artifacts.test.ts' 'lib/cockpit-bff-auth.ts' 'lib/cockpit-api-headers.ts'`
  Result: PASS.
- `node_modules/.bin/tsc --noEmit --pretty false`
  Result: PASS.
- Code-reviewer pass over modified and added files: no critical issues after replacing raw guarded API links with in-page anchors.

## Files Intentionally Not Touched

- `financial-engine_v2/backend/**`
- `financial-engine_v2/cockpit/**`
- Strategy Lab or QuantDinger runtime, sidecar, probes, or service config
- repo evidence artifacts outside this task report directory
- extraction, parser, prompt, gold-label, Qdrant, database, memory, runtime/model/GPU service configuration, and financial truth surfaces
- Home layout issue #42 and Strategy Lab workflow issue #76/#183

## Remaining Blockers Or Follow-Up

- This PR remains stacked on PR #268, which is stacked on PR #264 and PR #178.
- PR #183 remains an adjacent Strategy Lab workflow PR to recheck during merge sequencing.
- #232 remains the broader browser API-key propagation tracker; this slice uses the focused helper already introduced in the #268 stack.
