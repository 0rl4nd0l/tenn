# Operator Gate Evidence

Collected: 2026-06-01T07:38:10Z

## Scope

- Target layer: Cockpit client/orchestration UI plus backend Cockpit prompt
  control routes.
- Contested surface touched: `financial-engine_v2/backend/app/routes/cockpit_api.py`.
- Production data access: false.
- Live LLM dry-run: not performed.
- GPU/runtime configuration changes: none.

## Implemented Behavior

- `financial-engine_v2/backend/app/routes/cockpit_api.py` now requires
  `COCKPIT_PROMPT_LAB_OPERATOR_ACCESS` and
  `X-Cockpit-Prompt-Lab-Intent: inspect-prompts` before serving:
  - `GET /api/cockpit/prompts/routes`
  - `POST /api/cockpit/prompts/preview`
  - `POST /api/cockpit/prompts/dry-run`
- `cockpit-ui/components/cockpit/settings/settings-screen.tsx` hides the
  Prompt Lab tab unless `NEXT_PUBLIC_COCKPIT_PROMPT_LAB_OPERATOR_ACCESS=1`.
- `cockpit-ui/lib/api-client.ts` sends the Prompt Lab intent header for Prompt
  Lab route, preview, and dry-run calls.

## Test Evidence

- `PYTHONPATH=financial-engine_v2/backend /home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/financial-engine_v2/.venv/bin/pytest financial-engine_v2/backend/tests/test_cockpit_prompt_lab.py`
  - Result: passed, 7 tests.
  - Evidence covered:
    - Prompt routes reject when backend operator access is disabled.
    - Prompt dry-run rejects when the operator intent header is missing.
    - Missing-intent dry-run does not call the fake LLM client.
    - Existing enabled Prompt Lab route, preview, slash preview, dry-run, and
      no-LLM-route rejection behavior is preserved.
- `corepack pnpm --dir cockpit-ui exec vitest run components/cockpit/settings/settings-screen.test.tsx`
  - Result: passed, 1 file, 5 tests.
  - Evidence covered:
    - Prompt Lab hidden from normal Settings by default.
    - Prompt Lab remains usable when operator UI access is enabled.
    - Dry-run client call includes `X-Cockpit-Prompt-Lab-Intent:
      inspect-prompts`.
- `corepack pnpm --dir cockpit-ui exec eslint components/cockpit/settings/settings-screen.tsx components/cockpit/settings/settings-screen.test.tsx components/cockpit/settings/prompt-lab-panel.tsx lib/api-client.ts`
  - Result: passed.
- `corepack pnpm --dir cockpit-ui exec tsc --noEmit --pretty false`
  - Result: passed.
- `PYTHONPATH=financial-engine_v2/backend /home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/financial-engine_v2/.venv/bin/python -m ruff check financial-engine_v2/backend/app/routes/cockpit_api.py financial-engine_v2/backend/tests/test_cockpit_prompt_lab.py`
  - Result: passed.
- `PYTHONPATH=financial-engine_v2/backend /home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/financial-engine_v2/.venv/bin/python -m py_compile financial-engine_v2/backend/app/routes/cockpit_api.py financial-engine_v2/backend/tests/test_cockpit_prompt_lab.py`
  - Result: passed.

## Rendered UI Evidence

Browser plugin was not available in this session, so validation used local
Playwright against the Next.js dev server.

- Default UI mode, `http://127.0.0.1:3016/settings`:
  - Runtime tab present: true.
  - Prompt Lab tab present: false.
  - Prompt stack text present: false.
  - Prompt API requests observed: none.
  - Page errors: none.
  - Console errors: none.
- Operator UI mode,
  `NEXT_PUBLIC_COCKPIT_PROMPT_LAB_OPERATOR_ACCESS=1`,
  `http://127.0.0.1:3017/settings`:
  - Tabs observed: Runtime, Prompt Lab.
  - Prompt API requests observed:
    - `GET /api/cockpit/prompts/routes` with intent `inspect-prompts`.
    - `POST /api/cockpit/prompts/preview` with intent `inspect-prompts`.
    - `POST /api/cockpit/prompts/dry-run` with intent `inspect-prompts`.
  - Page errors: none.
  - Console errors: none.

## Boundaries Preserved

- Financial truth, extraction, parser routing, prompt content semantics,
  retrieval, memory stores, source/evidence labels, Qdrant, Postgres,
  production data, runtime/model/GPU configuration, and service state were not
  modified.
