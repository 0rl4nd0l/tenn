# Control Surface Inventory

Generated: 2026-05-27T14:30:25+10:00

| Surface | Files | Classification | Who Can Call | Confirmation / Intent | Blast Radius | Risk | Tracker |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `POST /api/cockpit/restart` | `cockpit-ui/app/api/cockpit/restart/route.ts` | guarded after this change | loopback same-origin by default; remote only with explicit env opt-in token | requires JSON, `X-Cockpit-Restart-Intent: restart-backend`, body intent and `RESTART BACKEND`; rejects cross-origin/cross-site | stops first matching `uvicorn app.main:app`, starts `run_local_backend.sh`, waits for health | HIGH before, LOW for direct route after fix | #55 |
| Operations restart button | `cockpit-ui/components/cockpit/operations/operations-screen.tsx`, `cockpit-ui/lib/api-client.ts` | guarded via shared helper after this change | browser user on same origin; route rejects non-loopback by default | helper sends explicit restart intent contract; UI confirmation remains #51 scope | calls `POST /api/cockpit/restart` | MEDIUM after route guard | #55, #51 |
| Chat slash command `/restart backend` | `cockpit-ui/components/cockpit/chat/chat-screen.tsx`, `cockpit-ui/lib/api-client.ts` | guarded via shared helper after this change | browser user on same origin; route rejects non-loopback by default | helper sends explicit restart intent contract; slash-command confirmation remains #51/action UX scope | calls `POST /api/cockpit/restart` | MEDIUM after route guard | #55, #51 |
| Cockpit BFF action execute | `cockpit-ui/app/api/cockpit/action/execute/route.ts` | DATA_MISSING / broader audit needed | any caller reaching Cockpit BFF route, subject to caller-provided headers | action body exists; route-local auth/CSRF parity not proven here | launches or polls backend action jobs | HIGH | #121 |
| Backend action execute | `financial-engine_v2/backend/app/routes/cockpit_api.py` | DATA_MISSING / broader audit needed | any caller reaching backend API, depending on network exposure | backend action registry preview validates action ids/args, but route auth parity not proven here | launches action subprocesses or queued jobs | HIGH | #121 |
| Backend action job stop | `financial-engine_v2/backend/app/routes/cockpit_api.py` | DATA_MISSING / broader audit needed | any caller reaching backend API, depending on network exposure | job id and backend state checks exist; route auth parity not proven here | terminates queued action process or requests cancellation | HIGH | #121 |
| Backend marketplace scan/calibration/sync launch routes | `financial-engine_v2/backend/app/routes/cockpit_api.py` | DATA_MISSING / broader audit needed | any caller reaching backend API, depending on network exposure | payload validation and runtime health checks exist; route auth parity not proven here | launches Marketplace browser/scanner jobs | HIGH | #121 |
| `scripts/cockpit restart backend` and related kill/reboot commands | `scripts/cockpit` | guarded by local shell access, not HTTP exposed | local operator shell | CLI intent only; not browser-callable in this audit | can kill/restart backend/UI/runtime processes | HIGH if misused locally | not #55 HTTP route |
| `financial-engine_v2/scripts/run_local_backend.sh` | script used by restart route and launchers | guarded when reached through #55 route after this change | local shell or guarded restart route | no standalone HTTP surface | starts backend on configured port/host | HIGH if directly invoked locally | #55 for route use |
| `financial-engine_v2/scripts/run_backend.sh` | local script | not Cockpit API exposed in this audit | local shell | no HTTP route found | kills existing uvicorn and starts backend on 127.0.0.1 | MEDIUM local-only | DATA_MISSING if externally wrapped elsewhere |
| `scripts/gpu_process_guard.sh --kill-rogues` | local script | not Cockpit API exposed in this audit | local shell | explicit CLI flag | can terminate rogue llama-server processes | HIGH local-only | outside #55 |

## Notes

- #55 is direct restart-route server-side guard coverage.
- #51 remains adjacent UI confirmation/review coverage.
- #121 tracks broader Cockpit action-control route auth parity discovered during
  this audit.
