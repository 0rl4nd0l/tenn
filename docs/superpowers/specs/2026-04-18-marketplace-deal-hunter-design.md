# 2026-04-18 Marketplace Deal Hunter Design

Status: Draft
Owner: Codex
Scope: Cockpit and backend autonomous Facebook Marketplace scouting

## Problem Statement

The current Tenn Marketplace flow is a one-off listing capture path. It can inspect or ingest a single Facebook Marketplace item URL, but it cannot:

1. store multiple independent buying missions
2. generate Marketplace searches from a user brief
3. scan result feeds repeatedly using a dedicated logged-in browser profile
4. score listings as deals against mission criteria
5. save matches as first-class records
6. raise persistent Cockpit alerts for strong matches

This misses the user’s actual goal: Tenn should autonomously scout Marketplace, flag good deals, save them, and notify the user inside Cockpit.

## Chosen Approach And Rationale

Chosen approach: `Backend-owned Marketplace hunter using a dedicated logged-in browser profile`

Summary:

- The backend owns mission definitions, scan jobs, saved matches, and alert state.
- A dedicated local Chrome/Brave profile provides the authenticated Facebook session.
- Tenn generates and rotates Marketplace searches from each mission’s structured rules and natural-language brief.
- Tenn scans deeply, checkpoints progress, scores listings, saves matches, and emits Cockpit alerts.

Rationale:

- This matches the user’s required workflow directly.
- It reuses existing repo primitives:
  - local Marketplace browser launch flow
  - local CDP browser attach
  - Cockpit state-store persistence
  - backend job execution and status tracking
- It avoids storing Facebook credentials in chat or mission records.
- It treats Marketplace hunting as a first-class workflow instead of overloading the current single-listing commentary ingestion path.

## Architecture Overview

### Current Baseline

Existing components:

- `financial-engine_v2/backend/app/services/facebook_marketplace_inspector.py`
  - inspects a single listing URL via Playwright over CDP
- `financial-engine_v2/backend/app/api/commentary.py`
  - stages one captured listing as commentary/transcript-like text
- `financial-engine_v2/scripts/launch_marketplace_browser.py`
  - launches a dedicated Brave/Chrome profile with `--remote-debugging-port=9222`
- `financial-engine_v2/backend/app/routes/cockpit_api.py`
  - provides backend job execution and status primitives
- `financial-engine_v2/cockpit/storage/state.py`
  - persists Cockpit state in SQLite

These pieces are necessary but not sufficient for autonomous scouting.

### Proposed End-to-End Flow

```
Cockpit Missions UI
  → backend Marketplace mission API
      → StateStore mission persistence
  → backend scheduler / manual run trigger
      → Marketplace scan job
          → CDP profile health check
          → generated Marketplace search pack
          → deep scroll result harvesting
          → listing card prefilter
          → detail-page evaluation
          → deal scoring
          → saved match persistence
          → Cockpit alert persistence
  → Cockpit Matches / Alerts UI
      → backend Marketplace read APIs
```

### Primary Boundaries

- `Client boundary`
  - Cockpit renders missions, matches, alerts, and job status.
  - Cockpit never owns authoritative mission or match state.
- `Backend orchestration boundary`
  - Backend owns mission definitions, deep scan execution, scoring outputs, and alerts.
- `Browser session boundary`
  - Tenn uses one dedicated local logged-in browser profile via CDP.
  - Facebook credentials are not stored in mission or chat state.
- `Capture boundary`
  - Single-listing commentary ingest remains available, but autonomous deal-finding no longer depends on commentary staging as its primary persistence model.

## Contract And Safety Constraints

Target system layers:

- client/orchestration layer in Cockpit UI
- backend-owned local workflow state and scan execution

Relevant contract rules:

- Backend remains the sole authority for workflow data correctness and persistence.
- Cockpit remains a client/orchestration layer only.
- Cockpit must not create an independent Marketplace store of truth.
- No duplicate retrieval/storage path should be introduced in the frontend.

What must not change:

- no direct Cockpit-owned persistence for missions or saved matches
- no bypass of backend-owned state
- no storage of Facebook credentials in mission state or chat history
- no automatic seller messaging, negotiation, or checkout actions
- no modification of existing financial-truth authority or RAG surfaces

Why this design is safe:

- It introduces a new backend-owned Marketplace domain without touching canonical financial truth.
- It reuses the local CDP/browser pattern already present in the repo.
- It keeps all autonomous behavior read-only with respect to Facebook actions.
- It provides auditable saved-match evidence instead of opaque recommendations.

## Component Design

### 1. Marketplace Mission Registry

Purpose:

- Store multiple concurrent buying missions with structured rules and a natural-language brief.

New mission contract:

- `mission_id: str`
- `name: str`
- `status: "active" | "paused" | "archived"`
- `brief: str`
- `category_hint: str | null`
- `hard_filters: dict`
- `soft_preferences: dict`
- `search_config: dict`
- `scan_config: dict`
- `created_at: str`
- `updated_at: str`
- `last_scan_at: str | null`

Hard filters:

- `include_keywords: list[str]`
- `exclude_keywords: list[str]`
- `price_min: number | null`
- `price_max: number | null`
- `location_names: list[str]`
- `radius_km: number | null`
- `condition_required: list[str]`
- `required_terms: list[str]`
- `forbidden_terms: list[str]`

Soft preferences:

- `preferred_brands: list[str]`
- `preferred_suburbs: list[str]`
- `preferred_condition_terms: list[str]`
- `nice_to_have_terms: list[str]`
- `urgency: "low" | "normal" | "high"`
- `price_aggressiveness: "conservative" | "balanced" | "aggressive"`
- `negotiation_expected: bool`

Search config:

- `query_variants_enabled: bool`
- `broadening_enabled: bool`
- `max_queries_per_run: int`

Scan config:

- `scan_interval_minutes: int`
- `candidate_card_target: int`
- `detail_open_target: int`
- `run_time_budget_minutes: int`
- `strong_match_threshold: int`
- `candidate_threshold: int`
- `aggressive_alerting: bool`

Persistence location:

- Add Marketplace mission tables to `financial-engine_v2/cockpit/storage/state.py`

### 2. Dedicated Browser Session Manager

Purpose:

- Reuse one dedicated logged-in Chrome/Brave profile for all Marketplace missions.

Responsibilities:

- health-check CDP availability on `127.0.0.1:9222`
- verify a usable Facebook Marketplace logged-in session exists
- expose clear states:
  - `browser_unavailable`
  - `browser_not_running`
  - `desktop_session_missing`
  - `login_required`
  - `challenge_detected`
  - `ready`

Integration points:

- reuse `financial-engine_v2/scripts/launch_marketplace_browser.py`
- reuse CDP attach logic patterns from `facebook_marketplace_inspector.py`

Non-goals:

- no credential storage
- no login-form automation in this wave
- no multi-profile scheduling in this wave

### 3. Marketplace Search Builder

Purpose:

- Generate a search pack for each mission from the mission brief and structured rules.

Output shape:

- `primary_queries: list[str]`
- `synonym_queries: list[str]`
- `brand_model_queries: list[str]`
- `fallback_queries: list[str]`
- `exclude_terms: list[str]`
- `location_scope: dict`
- `price_bounds: dict`

Behavior:

- precise searches run first
- broader fallback searches run only when precise searches are exhausted or under-yielding
- successful query variants are prioritized in later runs
- mission rules are never silently rewritten; only query ordering and breadth are adapted

### 4. Marketplace Scan Orchestrator

Purpose:

- Execute deep, resumable Marketplace scans for all active missions.

Execution model:

- one scan worker per dedicated browser profile
- backend-owned job execution using the existing backend job/status model
- manual run and scheduled run share the same code path

Per-run algorithm:

1. load all active missions
2. verify browser profile health
3. generate mission search pack
4. open each search page
5. deep-scroll while new unseen listings continue appearing
6. harvest listing cards
7. run card prefilter
8. open detail pages for likely candidates
9. evaluate and score details
10. persist seen state, saved matches, and alerts
11. checkpoint progress

Stop conditions:

- no new unseen listings appear for a sustained stretch
- duplicate saturation exceeds threshold
- session becomes logged out or blocked
- mission run exceeds configured time/listing budget

Defaults:

- `scan_interval_minutes = 15`
- `candidate_card_target = 300`
- continue beyond target while yield remains healthy
- `detail_open_target = 100`

Checkpointing:

- checkpoint by mission, query variant, and canonical listing identifier
- resume from prior progress instead of restarting at the top of results

### 5. Listing Evaluation And Deal Scoring

Purpose:

- Distinguish obvious junk from plausible matches and strong deals.

Stage 1: card prefilter

Inputs:

- card title
- visible price
- location snippet
- visible listing text fragments

Outputs:

- `prefilter_decision: "reject" | "open"`
- `open_priority: int`
- `prefilter_reasons: list[str]`

Stage 2: detail evaluation

Inputs:

- full title
- price
- description
- seller/location text
- visible condition cues
- mission brief and filters

Outputs:

- `eligibility: "pass" | "reject"`
- `score: int`
- `decision_band: "strong_match" | "candidate" | "reject"`
- `reasons_for: list[str]`
- `reasons_against: list[str]`
- `confidence: float`

Scoring rules:

- hard filters are binary and can reject immediately
- natural-language brief drives the semantic ranking score
- soft preferences adjust the score up or down
- price receives its own component relative to the mission’s observed local price band
- duplicate, reseller, parts-only, repair-only, or junk signals reduce score hard

Decision bands:

- `85-100`
  - save as `strong_match`
  - emit alert immediately
- `70-84`
  - save as `candidate`
  - emit alert only if `aggressive_alerting = true`
- `<70`
  - keep as scan history only

Learning boundary:

- Tenn may improve price baselines and query ordering from observed listings and user review actions
- Tenn must not silently rewrite the mission brief or hard filters

### 6. Saved Matches And Alerts

Purpose:

- Persist good deals as first-class records with reviewable evidence.

Saved match fields:

- `match_id`
- `mission_id`
- `listing_id`
- `listing_url`
- `title`
- `price`
- `location`
- `seller_name`
- `captured_at`
- `score`
- `decision_band`
- `reasons_for`
- `reasons_against`
- `confidence`
- `raw_text_snapshot`
- `screenshot_path`
- `status: "new" | "reviewed" | "dismissed" | "contacted" | "won" | "lost"`

Alert fields:

- `alert_id`
- `mission_id`
- `match_id`
- `status: "new" | "acknowledged" | "dismissed"`
- `created_at`
- `trigger_reason`

Alert rules:

- alert only for `strong_match` by default
- do not re-alert unchanged listings
- re-alert only when material change occurs:
  - price drop
  - materially changed text
  - score crosses into `strong_match`

### 7. Cockpit UI And BFF Surfaces

New frontend surfaces:

- `/marketplace`
  - mission management
- `/marketplace/matches`
  - saved deal inbox
- `/marketplace/alerts`
  - alert queue and acknowledgements
- match detail drawer or page
  - full score breakdown and evidence

Cockpit BFF routes:

- `cockpit-ui/app/api/cockpit/marketplace/missions/*`
- `cockpit-ui/app/api/cockpit/marketplace/matches/*`
- `cockpit-ui/app/api/cockpit/marketplace/alerts/*`
- `cockpit-ui/app/api/cockpit/marketplace/scans/*`

Backend routes:

- add Marketplace-specific endpoints to `financial-engine_v2/backend/app/routes/cockpit_api.py`
  - create/update/pause/archive mission
  - list missions
  - trigger scan
  - read scan job status
  - list matches
  - read/update match review status
  - list/ack/dismiss alerts
  - read browser-profile health

Why `cockpit_api.py`:

- this workflow is Cockpit-facing and local-machine-oriented
- it fits the existing backend job execution and status model
- it avoids mixing autonomous Marketplace scouting into the commentary API

## Data Contracts

### Mission Persistence Contract

`marketplace_mission`

```json
{
  "mission_id": "mp_mission_123",
  "name": "Used dual-cab ute",
  "status": "active",
  "brief": "Find a reliable 4x4 dual-cab ute under 25k in Melbourne's north-east...",
  "category_hint": "vehicles",
  "hard_filters": {
    "include_keywords": ["4x4", "dual cab"],
    "exclude_keywords": ["wrecking", "parts"],
    "price_min": null,
    "price_max": 25000,
    "location_names": ["Heidelberg", "Preston"],
    "radius_km": 40,
    "condition_required": [],
    "required_terms": [],
    "forbidden_terms": ["statutory write-off"]
  },
  "soft_preferences": {
    "preferred_brands": ["Toyota", "Isuzu"],
    "preferred_suburbs": [],
    "preferred_condition_terms": ["full service history"],
    "nice_to_have_terms": ["bullbar", "canopy"],
    "urgency": "normal",
    "price_aggressiveness": "balanced",
    "negotiation_expected": true
  },
  "search_config": {
    "query_variants_enabled": true,
    "broadening_enabled": true,
    "max_queries_per_run": 6
  },
  "scan_config": {
    "scan_interval_minutes": 15,
    "candidate_card_target": 300,
    "detail_open_target": 100,
    "run_time_budget_minutes": 20,
    "strong_match_threshold": 85,
    "candidate_threshold": 70,
    "aggressive_alerting": false
  }
}
```

### Match Contract

`marketplace_match`

```json
{
  "match_id": "mp_match_123",
  "mission_id": "mp_mission_123",
  "listing_id": "1948337392560567",
  "listing_url": "https://www.facebook.com/marketplace/item/1948337392560567/",
  "title": "2014 Toyota Hilux SR5 4x4",
  "price": "$22,500",
  "location": "Preston, VIC",
  "seller_name": "Example Seller",
  "captured_at": "2026-04-18T05:21:00Z",
  "score": 89,
  "decision_band": "strong_match",
  "reasons_for": ["Below local median", "Matches preferred brand", "Service-history language present"],
  "reasons_against": ["High kilometres"],
  "confidence": 0.84,
  "raw_text_snapshot": "Visible listing text...",
  "screenshot_path": "/.../reports/marketplace_captures/...",
  "status": "new"
}
```

### Browser Health Contract

```json
{
  "status": "ready",
  "cdp_url": "http://127.0.0.1:9222",
  "browser_family": "chrome",
  "profile_path": "/home/l4nd0/.tenn/browser_profiles/facebook-marketplace-chrome",
  "logged_in": true,
  "challenge_detected": false,
  "last_checked_at": "2026-04-18T05:30:00Z"
}
```

## Failure Taxonomy

| Failure Mode | Detection | User-visible outcome | Persistence |
| --- | --- | --- | --- |
| Desktop session missing | no `DISPLAY` / `WAYLAND_DISPLAY` | mission scans fail with `browser_unavailable` | scan job row |
| Browser not listening on CDP | no `127.0.0.1:9222` | mission scans fail with `browser_not_running` | scan job row |
| Logged out of Facebook | Marketplace login wall / text markers | mission scans fail with `login_required` | scan job row |
| Challenge or block page | challenge markers / unexpected redirect | mission scans fail with `challenge_detected` | scan job row |
| Search feed exhausted | no unseen listings over sustained scroll | scan completes normally with exhausted status | scan run row |
| Duplicate saturation | duplicate ratio exceeds threshold | query run stops early, next query begins | scan run row |
| Detail-page parse failure | missing fields / DOM mismatch | listing marked `parse_failed`, not alerted | seen-listing row |
| Score evaluation failure | exception in scoring pipeline | listing marked `evaluation_failed` | seen-listing row |
| State-store write failure | sqlite error | job fails hard | job row + stderr log |

## Validation Gates

1. A mission cannot be activated unless it has:
   - non-empty `name`
   - non-empty `brief`
   - at least one include keyword or meaningful brief text
2. A scan cannot run unless browser health is `ready`.
3. A listing cannot be saved as a match unless:
   - hard filters pass
   - canonical listing URL or listing ID is resolved
   - score band is `candidate` or `strong_match`
4. A `strong_match` alert cannot be created twice for the same unchanged listing.
5. A dismissed listing remains dismissed until a material listing change is detected.
6. No Marketplace scan may auto-message a seller or trigger purchase/contact actions.

## Eval Harness

Primary implementation validation:

```bash
/mnt/sdb2/home/l4nd0/tenn/financial-engine_v2/.venv/bin/python -m pytest \
  financial-engine_v2/backend/tests/test_marketplace_mission_service.py \
  financial-engine_v2/backend/tests/test_marketplace_search_builder.py \
  financial-engine_v2/backend/tests/test_marketplace_scanner.py \
  financial-engine_v2/backend/tests/test_marketplace_scoring.py \
  financial-engine_v2/backend/tests/test_cockpit_marketplace_api.py \
  financial-engine_v2/cockpit/tests/test_actions_marketplace_browser.py \
  cockpit-ui/components/cockpit/marketplace/*.test.tsx \
  cockpit-ui/lib/marketplace-*.test.ts -q
```

Manual validation:

1. Launch dedicated Marketplace browser profile.
2. Log into Facebook once in that profile.
3. Create two missions with different briefs and filters.
4. Trigger a scan manually.
5. Confirm:
   - scan job status updates in Cockpit
   - listings are harvested deeply
   - strong matches are saved and alerted
   - dismissed matches do not re-alert unless materially changed

## Test Suite Impact

New backend tests:

- `financial-engine_v2/backend/tests/test_marketplace_mission_service.py`
- `financial-engine_v2/backend/tests/test_marketplace_search_builder.py`
- `financial-engine_v2/backend/tests/test_marketplace_scanner.py`
- `financial-engine_v2/backend/tests/test_marketplace_scoring.py`
- `financial-engine_v2/backend/tests/test_cockpit_marketplace_api.py`

Updated backend tests:

- `financial-engine_v2/backend/tests/test_commentary_endpoints.py`
  - preserve single-listing capture behavior
- `financial-engine_v2/cockpit/tests/test_actions_marketplace_browser.py`
  - retain browser-launch contract

New frontend tests:

- mission screen tests
- matches screen tests
- alerts screen tests
- Marketplace BFF proxy route tests

Unchanged by design:

- financial extraction tests
- RAG stability tests
- commentary transcript ingestion tests outside Marketplace single-item capture

## Files Changed

| File | Status | Purpose |
| --- | --- | --- |
| `financial-engine_v2/cockpit/storage/state.py` | Modified | Add Marketplace mission, seen-listing, saved-match, and alert tables |
| `financial-engine_v2/backend/app/routes/cockpit_api.py` | Modified | Add backend Marketplace endpoints and scan job entrypoints |
| `financial-engine_v2/backend/app/services/facebook_marketplace_inspector.py` | Modified | Factor reusable listing-card/detail extraction helpers where useful |
| `financial-engine_v2/backend/app/services/marketplace_mission_service.py` | New | Mission CRUD, validation, state-store access |
| `financial-engine_v2/backend/app/services/marketplace_browser_profile.py` | New | CDP/profile health checks and readiness contract |
| `financial-engine_v2/backend/app/services/marketplace_search_builder.py` | New | Convert mission rules and brief into Marketplace search packs |
| `financial-engine_v2/backend/app/services/marketplace_scoring.py` | New | Card prefilter and full listing score logic |
| `financial-engine_v2/backend/app/services/marketplace_scanner.py` | New | Deep-scroll harvesting, dedupe, checkpointing, persistence |
| `financial-engine_v2/scripts/launch_marketplace_browser.py` | Modified | Optional health/status flags if needed for UI |
| `cockpit-ui/app/api/cockpit/marketplace/missions/route.ts` | New | Cockpit BFF mission list/create proxy |
| `cockpit-ui/app/api/cockpit/marketplace/missions/[missionId]/route.ts` | New | Cockpit BFF mission update proxy |
| `cockpit-ui/app/api/cockpit/marketplace/matches/route.ts` | New | Cockpit BFF match list proxy |
| `cockpit-ui/app/api/cockpit/marketplace/matches/[matchId]/route.ts` | New | Cockpit BFF match status update proxy |
| `cockpit-ui/app/api/cockpit/marketplace/alerts/route.ts` | New | Cockpit BFF alert list proxy |
| `cockpit-ui/app/api/cockpit/marketplace/scans/route.ts` | New | Cockpit BFF scan trigger proxy |
| `cockpit-ui/app/marketplace/page.tsx` | New | Mission management UI |
| `cockpit-ui/app/marketplace/matches/page.tsx` | New | Saved matches inbox UI |
| `cockpit-ui/app/marketplace/alerts/page.tsx` | New | Alert queue UI |
| `cockpit-ui/components/cockpit/cockpit-sidebar.tsx` | Modified | Add Marketplace navigation entries |

## Out Of Scope

- storing Facebook credentials
- automatic seller messaging
- auto-negotiation or offer placement
- multi-profile or multi-account Facebook support
- cross-marketplace support outside Facebook Marketplace
- mobile-device browser control
- background cloud browser execution detached from the local logged-in machine
- replacing the current single-item Marketplace commentary capture path

