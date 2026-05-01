---
name: cockpit-flag-orchestrator
description: Investigate and fix outstanding Cockpit feedback artifacts, including auto diagnostics (`auto_*`), manually flagged chats (`flag_*`), and captured UI screenshots (`ui_issue_*`). Use when Codex is asked to triage unresolved Cockpit flags, run or improve `scripts/cockpit_flag_investigator.py`, coordinate subagents to inspect evidence and debate fixes, implement the chosen fix, verify it, commit it, and resolve the backend flag records.
---

# Cockpit Flag Orchestrator

Use this skill to turn Cockpit feedback artifacts into verified fixes. The workflow covers three capture kinds:

- `auto_diagnostic`: deterministic backend auto flags for tool failures, missing sources, timeouts, latency, compaction, or information-access issues.
- `chat_feedback`: operator-flagged chat responses that need root-cause analysis and code fixes.
- `ui_issue`: captured Cockpit screens with `ui-screenshot.png` and often `browser-debug.json`.

## Contract Guard

Before investigation or edits:

1. Read `CLAUDE.md`, `docs/architecture/SYSTEM_CONTRACT.md`, `/home/l4nd0/.claude/projects/-mnt-sdb2-home-l4nd0-tenn/memory/MEMORY.md`, and `docs/claude/STATE.md`.
2. State the target layer, relevant contract rules, invariants that must not change, and why the planned work is safe.
3. If the task starts, restarts, or depends on llama-server, run `scripts/gpu_process_guard.sh --check` before proceeding. Most flag triage does not need this.
4. Treat backend APIs as authoritative for Cockpit feedback. Do not query Postgres or Qdrant directly for authoritative Cockpit facts.
5. Do not introduce fallback behavior that masks backend failure. Surface unavailable evidence as unavailable.
6. Do not resolve a flag until the fix is committed and the backend resolve endpoint accepts the commit metadata.

## Discovery

Prefer the backend API whenever it is reachable:

```bash
curl -sS "http://127.0.0.1:8000/api/cockpit/feedback/flags?limit=100&status=open"
curl -sS "http://127.0.0.1:8000/api/cockpit/feedback/flags/<REPORT_ID>"
```

Use the local artifact tree only to read paths returned by the API, or to operate the existing queued-investigation runner:

```bash
python scripts/cockpit_flag_investigator.py --once --dry-run
python scripts/cockpit_flag_investigator.py --report-id <REPORT_ID> --once --apply
```

Expected artifact files live under `reports/cockpit/flagged_sessions/<session>/<report_id>/`:

- `bundle.json`: saved transcript, request, response, runtime context, auto findings, and attachment metadata.
- `summary.md`: compact human-readable summary.
- `analysis.json`: optional backend analysis of likely failure modes.
- `investigation.json`: queued/running/completed Codex investigation status.
- `codex_prompt.md`: backend-generated one-report prompt.
- `ui-screenshot.png` and `browser-debug.json`: UI issue evidence when present.

## Workflow

1. Inventory open flags.
   - List open flags with the API and include `status=all` only when looking for duplicates or prior fixes.
   - Group obvious duplicates by `capture_kind`, `note`, `auto_findings[].category`, failing tool, route, and response excerpt.
   - Work one root cause group at a time. A single verified fix may resolve multiple reports, but do not mix unrelated failures in one patch.

2. Build the evidence packet.
   - Read each selected report through `GET /api/cockpit/feedback/flags/{report_id}`.
   - Inspect `summary_markdown`, `bundle.backend_turn`, `bundle.frontend_snapshot`, `bundle.auto_findings`, `bundle.transcript`, `bundle.flagged_message`, `analysis`, and `investigation`.
   - For `ui_issue`, open the saved screenshot with `view_image` when a local path is available, then inspect `browser-debug.json` for console errors, failed fetches, route, viewport, and timing.
   - Record only evidence visible in the current turn. Mark anything else unverified.

3. Dispatch subagents when the current user request explicitly authorizes subagents or parallel agent work.
   - Use read-only explorer agents for evidence, code mapping, reproduction, UI/browser review, and contract checking.
   - Give each agent a bounded task and exact output shape. Use `references/subagent-prompts.md`.
   - Do not ask subagents to edit code during evidence collection or debate.

4. Run the debate gate.
   - Compare the agents' root-cause hypotheses against the evidence packet.
   - Reject any hypothesis that cannot cite a file, API payload field, test, screenshot detail, or log line.
   - Choose the smallest contract-compliant fix that addresses the root cause and can be verified.
   - If the evidence only proves an operational outage or duplicate already-fixed report, do not edit code. Report that state and ask before resolving without a new fix commit.

5. Implement.
   - Keep the patch scoped to the chosen root cause.
   - If delegating implementation to a worker, assign a disjoint write set and tell it other agents may be editing the repo, so it must not revert unrelated changes.
   - Add or update focused tests for the failing behavior. For screenshots, include a UI test or Playwright reproduction when the issue is visual or interaction-based.

6. Verify.
   - Run the narrowest meaningful test lane first, then expand when shared behavior is touched.
   - Typical lanes:
     - Backend feedback/chat: `financial-engine_v2/.venv/bin/python -m pytest financial-engine_v2/backend/tests/test_cockpit_api_chat_stream.py -q`
     - Cockpit agent/tool routing: `financial-engine_v2/.venv/bin/python -m pytest financial-engine_v2/cockpit/tests/test_agent_loop.py financial-engine_v2/cockpit/tests/test_tool_executor.py -q`
     - Web UI: `pnpm --dir cockpit-ui exec tsc --noEmit`, targeted `pnpm --dir cockpit-ui exec eslint <files>`, targeted `pnpm --dir cockpit-ui test <test-file>`
     - Formatting: `python -m ruff check autodev financial-engine_v2/backend scripts`
   - If a required lane cannot run, state why and keep the flag unresolved unless the user explicitly accepts the residual risk.

7. Commit and resolve.
   - Commit the fix with the repo milestone format:

```text
milestone(<subsystem>): <what works now>

Working: <confirmed-working behavior>
Tested: <how verified>
```

   - Resolve every fixed report after the commit lands:

```bash
COMMIT_SHA="$(git rev-parse --short=12 HEAD)"
COMMIT_MSG="$(git log -1 --pretty=%s)"
curl -sS -X POST "http://127.0.0.1:8000/api/cockpit/feedback/flags/<REPORT_ID>/resolve" \
  -H "Content-Type: application/json" \
  -d "{\"commit_sha\":\"${COMMIT_SHA}\",\"resolved_by\":\"codex\",\"note\":\"${COMMIT_MSG}\"}"
```

## Debate Output

Keep the working notes compact:

- Report group: IDs, capture kinds, shared symptoms, status.
- Evidence: API fields, screenshot/browser-debug observations, failing tests or repro commands.
- Agent positions: root cause and proposed fix from each agent, with citations.
- Decision: chosen fix, rejected alternatives, contract check.
- Result: changed files, validation commands, resolved report IDs.

## Reference Prompts

Read `references/subagent-prompts.md` when dispatching evidence scouts, reproduction scouts, contract enforcers, debate agents, or implementation workers.
