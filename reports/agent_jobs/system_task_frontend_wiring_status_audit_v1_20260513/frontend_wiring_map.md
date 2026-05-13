# Frontend Wiring Map

## Summary

[Confirmed] Cockpit has 19 page routes and 52 route handlers under `cockpit-ui/app`. `next.config.mjs` rewrites `/api/:path*`, `/research/:path*`, and `/rag/:path*` to the backend URL, so pages may use either local BFF handlers or backend rewrite paths.

## App/router structure

| route | page file | primary component | visible nav? | data path |
| --- | --- | --- | --- | --- |
| `/` | `cockpit-ui/app/page.tsx` | `CockpitHomePage` | Yes | `/api/cockpit/home` BFF |
| `/full-chat` | `app/full-chat/page.tsx` | `ChatScreen` | Yes | `/api/cockpit/chat*`, `/api/commentary/*` |
| `/operations` | `app/operations/page.tsx` | `OperationsScreen` | Yes | `/api/cockpit/action*`, health, restart, models |
| `/updater` | `app/updater/page.tsx` | `UpdaterScreen` | Yes | DATA_MISSING |
| `/verification` | `app/verification/page.tsx` | `VerificationScreen` | Yes | `/api/context/verification*`, `/api/extraction-eval*` |
| `/history` | `app/history/page.tsx` | `HistoryScreen` | Yes | `/api/docs`, queue/job helpers |
| `/settings` | `app/settings/page.tsx` | `SettingsScreen` | Yes | `/api/health`, `/api/cockpit/config`, models |
| `/news` | `app/news/page.tsx` | `NewsScreen` | Yes | `/rag/query` via rewrite |
| `/intel-ops` | `app/intel-ops/page.tsx` | inline Intel page | Yes | DATA_MISSING; likely Cockpit pulse/matrix |
| `/holdings` | `app/holdings/page.tsx` | `HoldingsScreen` | Yes | `/api/cockpit/holdings*` |
| `/memory` | `app/memory/page.tsx` | `MemoryScreen` | Yes | `/api/cockpit/memory*` BFF to `/api/context/*` |
| `/thesis-audit` | `app/thesis-audit/page.tsx` | `ThesisAuditScreen` | Yes | `/api/cockpit/thesis-audit*`, context proposals |
| `/watchlist` | `app/watchlist/page.tsx` | `WatchlistScreen` | Yes | `/api/cockpit/watchlist*` |
| `/marketplace` | `app/marketplace/page.tsx` | `MarketplaceMissionScreen` | Yes | Marketplace BFF routes |
| `/marketplace/matches` | `app/marketplace/matches/page.tsx` | `MarketplaceMatchesScreen` | Yes | Marketplace match routes |
| `/marketplace/matches/[matchId]` | `app/marketplace/matches/[matchId]/page.tsx` | match detail screen | No direct sidebar item | Marketplace match detail/update |
| `/marketplace/alerts` | `app/marketplace/alerts/page.tsx` | `MarketplaceAlertsScreen` | Yes | Marketplace alert routes |
| `/marketplace-capture` | `app/marketplace-capture/page.tsx` | capture helper page | No | marketplace capture submit/token |
| `/boot` | `app/boot/page.tsx` | `BootScreen` | No | Cockpit health and direct llama.cpp health |

## Layout and navigation ownership

[Confirmed] Sidebar ownership is `cockpit-ui/components/cockpit/cockpit-sidebar.tsx`. Nav items include Overview, Chat, Operations, Updater, Verification, History, Settings, News, Intel Pulse, Holdings, Memory, Thesis Audit, Watchlist, Marketplace, Matches, and Alerts.

## BFF and route-handler inventory

| route handler family | files | backend target | mode |
| --- | --- | --- | --- |
| Action jobs | `app/api/cockpit/action/**` | `/api/cockpit/action/**` | Live/mutating |
| Claims | `app/api/cockpit/claims/verify/route.ts` | `/api/cockpit/claims/verify` | Live |
| Commentary | `app/api/cockpit/commentary/**` | `/api/commentary/*` plus local unavailable ephemeral routes | Mixed |
| Feedback | `app/api/cockpit/feedback/**`, `app/cockpit-local/**` | `/api/cockpit/feedback*` plus local Codex deploy/investigation | Mixed/mutating |
| Health/metrics | `app/api/cockpit/health`, `metrics/*` | backend health plus local OS/GPU probes | Live/read-only |
| Holdings | `app/api/cockpit/holdings/**` | `/api/cockpit/holdings*` | Live/mutating |
| Home | `app/api/cockpit/home/route.ts` | aggregate backend calls | Live |
| Marketplace | `app/api/cockpit/marketplace/**` | `/api/cockpit/marketplace/**` | Live/mutating |
| Memory | `app/api/cockpit/memory/**` | `/api/context/**` | Live/mutating |
| Restart | `app/api/cockpit/restart/route.ts` | local backend restart script | Live/mutating |
| Watchlist | `app/api/cockpit/watchlist/**` | `/api/cockpit/watchlist*` | Live/mutating |
| Legacy chat | `app/chat/route.ts` | backend `/chat` | Live/legacy |

## Client-side service/lib files

| file | role | notes |
| --- | --- | --- |
| `cockpit-ui/lib/proxy.ts` | backend URL resolver | Defaults to `http://localhost:8000`; trims trailing slash. |
| `cockpit-ui/lib/api-client.ts` | broad Cockpit API client | Uses `NEXT_PUBLIC_API_KEY`; covers health, config, sessions, chat, actions, models, queue, docs, financials, extraction review, thesis, memory. |
| `cockpit-ui/lib/cockpit-home-api.ts` | Home BFF aggregator | Constructs deterministic DATA_MISSING/degraded states; tested. |
| `cockpit-ui/lib/cockpit-home-contract.ts` | Home trust/source label rules | Maps source labels to UI trust levels and validates DATA_MISSING reasons. |
| `cockpit-ui/lib/marketplace-api.ts` | Marketplace client | Covers browser health, missions, scans, tracked products, matches, benchmark review, alerts. |
| `cockpit-ui/lib/marketplace-assistant.ts` | Marketplace assistant/chat helper | Calls `/api/cockpit/chat`. |
| `cockpit-ui/lib/cockpit-store.ts` | local UI state | Preferences, active ticker, selected model, local settings. |

## Environment and config

| variable/config | observed use | risk |
| --- | --- | --- |
| `NEXT_PUBLIC_API_URL` | Next rewrites and BFF backend target | Wrong value breaks all proxied backend paths. |
| `NEXT_PUBLIC_API_KEY` | Browser/client auth header in multiple pages | Secret exposure risk if real secret is placed in public env. |
| `cockpit.apiKey` localStorage | Used by multiple pages as API key source | Local user state, not repo truth. |
| `DEFAULT_BACKEND_URL=http://localhost:8000` | `lib/proxy.ts` and next config | OK for local dev only. |
| LLM endpoint `http://localhost:8001` | Settings/Boot defaults | Direct frontend runtime probe. |

## Live/mock/static classification

| area | classification | evidence |
| --- | --- | --- |
| Home | Live with explicit demo fallback labels | Home BFF tests and UI DATA_MISSING text. |
| Chat | Live/proxied | Backend `/api/cockpit/chat`; session routes. |
| News | Live/proxied | `/rag/query` rewrite to backend. |
| Marketplace | Live/proxied | BFF route files and backend decorators. |
| Intel Pulse signals/memory tabs | Static unavailable/degraded placeholders | Page text includes `SIGNALS_UNAVAILABLE` and `MEMORY_UNAVAILABLE`. |
| Commentary ephemeral index | Unavailable/local 501 | BFF route files return unavailable state. |
| Capture token | Local helper token route | Not a backend truth source. |

## Missing backend route scan

[Confirmed] No obvious missing backend route was proven for inspected Cockpit paths because `next.config.mjs` rewrites backend paths and backend decorators exist for `/rag/query`, `/api/cockpit/chat/attachments/upload`, and Marketplace match feedback. [Inferred] Some frontend calls rely on rewrite-only ownership rather than a local BFF wrapper.

## Duplicated or conflicting routes

| route | evidence | risk |
| --- | --- | --- |
| `/chat`, `/api/chat`, `/api/cockpit/chat` | `main.py` includes `chat_router` with and without `/api`, and `cockpit_api.py` defines `/chat` under `/api/cockpit` | Legacy API confusion |
| `/api/cockpit/feedback` and `/api/cockpit/feedback/flag` | separate feedback response and flagged-report routes | Semantics must remain distinct |
| Marketplace price intelligence | Mounted standalone router and Cockpit marketplace wrappers | Overlap is intentional but should remain documented |

## Obvious stale/mock/placeholder areas

| area | evidence | user-facing risk |
| --- | --- | --- |
| Home demo fixtures | UI says dev/demo and not source-backed | Low if label remains visible |
| Intel Pulse unavailable tabs | Static unavailable codes | Medium if presented as complete feature |
| Commentary ephemeral index | 501/unavailable BFF | Medium if UI expects it live |
| Operations `getActionEndpoint` comments | Some action endpoint mappings return null | Medium for action preview/run expectations |

