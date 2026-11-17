# Cockpit Boot Health BFF Contract

## Summary

- Branch: `safe/reporting-boot-health-bff-contract-v1-20260601`
- Worktree: `/home/l4nd0/tenn-reporting-boot-health-bff-contract-v1-20260601`
- Base HEAD: `0320f645c806`
- Lane: Reporting
- Execution mode: safe_extension
- Collision risk: MEDIUM
- Issue: #144

## Scope Result

`/boot` now consumes `/api/cockpit/health` as the single readiness source. The
Boot page no longer runs browser-side localhost checks for llama.cpp, Ollama,
Qdrant, or Redis. It renders backend, llama.cpp, Ollama, Qdrant, Redis, GPU,
and host rows from the BFF service envelope. Services missing from the BFF
envelope stay `unknown` with an explicit BFF verification message.

The existing Next.js BFF route was inspected and already merges backend
`/api/cockpit/health` services with server-side GPU and host probes, so no BFF
route edit was required.

## Files Changed

- `docs/agent_tasks/cockpit_boot_health_bff_contract_v1_20260531.md`
- `cockpit-ui/components/cockpit/boot/boot-screen.tsx`
- `cockpit-ui/lib/boot-health.test.tsx`
- `cockpit-ui/tests/chat-browser-regression.spec.ts`
- `reports/agent_jobs/cockpit_boot_health_bff_contract_v1_20260531/README.md`
- `reports/agent_jobs/cockpit_boot_health_bff_contract_v1_20260531/status.json`
- `reports/agent_jobs/cockpit_boot_health_bff_contract_v1_20260531/validation.json`
- `reports/agent_jobs/cockpit_boot_health_bff_contract_v1_20260531/diff-check.json`

## Files Inspected

- `CLAUDE.md`
- `docs/architecture/SYSTEM_CONTRACT.md`
- `/home/l4nd0/.claude/projects/-mnt-sdb2-home-l4nd0-tenn/memory/MEMORY.md`
- `cockpit-ui/app/api/cockpit/health/route.ts`
- `financial-engine_v2/backend/app/routes/cockpit_api.py`
- `cockpit-ui/components/cockpit/boot/boot-screen.tsx`
- `cockpit-ui/tests/chat-browser-regression.spec.ts`
- `cockpit-ui/tests/smoke.spec.ts`
- `cockpit-ui/package.json`
- `cockpit-ui/vitest.config.ts`
- `cockpit-ui/vitest.setup.ts`
- `scripts/agent_job_contract.py`
- `scripts/agent_job_registry.py`

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/cockpit_boot_health_bff_contract_v1_20260531.md --write-report`: PASS
- `python3 scripts/agent_job_registry.py list-active`: PASS; unrelated active Financial Truth extraction job present
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/cockpit_boot_health_bff_contract_v1_20260531.md`: PASS
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/cockpit_boot_health_bff_contract_v1_20260531.md`: PASS
- `corepack pnpm install --frozen-lockfile`: PASS; populated ignored dependencies only
- `corepack pnpm exec vitest run lib/boot-health.test.tsx`: PASS, 2 tests
- `corepack pnpm exec tsc --noEmit --pretty false`: PASS
- `corepack pnpm exec eslint components/cockpit/boot/boot-screen.tsx lib/boot-health.test.tsx tests/chat-browser-regression.spec.ts`: PASS
- `corepack pnpm exec next build`: PASS
- `PLAYWRIGHT_BASE_URL=http://127.0.0.1:3016 COCKPIT_ROUTE_PARITY_REPORT_PATH=/tmp/cockpit_boot_health_bff_contract_route_parity.md corepack pnpm exec playwright test tests/chat-browser-regression.spec.ts --project=chromium --grep "Boot readiness uses Cockpit health BFF|visible primary routes load"`: PASS, 2 tests
- `git diff --check`: PASS
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/cockpit_boot_health_bff_contract_v1_20260531.md --no-write-report`: PASS

## Runtime And Data Safety

- No backend runtime services were started, stopped, or restarted.
- The only temporary service was a local Next.js production server on
  `127.0.0.1:3016` for Playwright validation; it was stopped after the test.
- No DB, Qdrant, news, memory, extraction, parser, gold-label, Docker, cron,
  model, GPU, or service config files were changed.
- The shared branch and active extraction job were not modified.

## DATA_MISSING

- `graphify-out/GRAPH_REPORT.md` was not present in this worktree when checked,
  so graphify community/god-node evidence was unavailable.

## Remaining Blockers

None for issue #144 scope.

## Next Safe Step

Commit this isolated worktree, push the branch, and open a draft PR with
`fixes #144`.
