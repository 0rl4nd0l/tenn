# 2026-04-20 Marketplace Assistant Chat Design

Status: Draft
Owner: Codex
Scope: Cockpit UI Marketplace mission drafting chat using the active model and existing Marketplace APIs

## Problem Statement

The Marketplace tab currently exposes a manual form and scan controls in
`cockpit-ui/components/cockpit/marketplace/mission-screen.tsx`, but it does not
provide a conversational workflow for mission creation.

The user wants a Marketplace-local chat window that:

1. talks to the currently active Cockpit model
2. already knows the user's saved home location
3. asks focused follow-up questions about the search
4. drafts a Marketplace mission from the conversation
5. creates the mission and optionally runs it when explicitly asked

Today, none of those behaviors exist in the Marketplace screen. The current UI
requires direct manual form entry, and there is no persisted Marketplace home
location preference.

## Chosen Approach And Rationale

Chosen approach: `Frontend-orchestrated Marketplace assistant on top of the existing Cockpit chat and Marketplace APIs`

Summary:

- Add a saved `marketplaceHomeLocation` Cockpit preference.
- Add a Marketplace-only assistant panel inside the Marketplace tab.
- Reuse the active model selection already stored in the Cockpit store.
- Reuse the existing `/api/cockpit/chat` transport for model responses.
- Keep mission creation and scan launching on the existing authoritative
  Marketplace endpoints.
- Maintain a local structured mission draft in the UI and only persist it when
  the user clicks `Create Mission` or `Create + Run Now`.

Rationale:

- This stays inside the system contract: Cockpit remains orchestration only, and
  the Marketplace backend remains the sole source of truth for saved missions.
- It avoids introducing a second Marketplace assistant backend or an alternate
  mission persistence path.
- It reuses the active model, existing chat transport, and existing mission/scan
  APIs instead of duplicating those subsystems.
- It lets the user see the evolving mission draft before any backend mutation.

## Architecture Overview

### Current Baseline

Existing authoritative surfaces:

- `cockpit-ui/components/cockpit/marketplace/mission-screen.tsx`
  - Marketplace mission list, browser health, create form, scan controls
- `cockpit-ui/lib/marketplace-api.ts`
  - Marketplace mission and scan API client
- `cockpit-ui/lib/api-client.ts`
  - Cockpit chat transport via `/api/cockpit/chat`
- `cockpit-ui/lib/cockpit-store.ts`
  - persisted Cockpit settings, session ID, and active chat model
- `financial-engine_v2/backend/app/routes/cockpit_api.py`
  - existing `/api/cockpit/chat`
  - existing `/api/cockpit/marketplace/missions`
  - existing `/api/cockpit/marketplace/scans`

What is missing:

- no saved Marketplace home location preference
- no Marketplace-scoped conversational UI
- no structured mission draft state derived from chat turns
- no assistant-driven create/run confirmation flow inside Marketplace

### Proposed End-To-End Flow

```text
Settings
  → save marketplaceHomeLocation in Cockpit preferences

Marketplace tab
  → Marketplace assistant panel loads
      → reads active model from Cockpit store
      → reads marketplaceHomeLocation from Cockpit preferences
      → reads browser health from Marketplace screen state
  → user chats in natural language
      → UI sends a constrained Marketplace drafting prompt to /api/cockpit/chat
      → UI parses a structured assistant payload from the model response
      → UI updates local MarketplaceMissionDraft
      → assistant asks the next missing question or shows confirmation actions
  → user clicks Create Mission or Create + Run Now
      → existing createMarketplaceMission()
      → optional triggerMarketplaceScan()
      → existing Marketplace screen reload()
      → existing Recent Scans / Scan Output update
```

### Primary Boundaries

- `Client boundary`
  - The Marketplace assistant owns only transient UI state:
    - conversation messages
    - parsed mission draft
    - confirmation state
  - It does not own authoritative missions or scan jobs.

- `Chat boundary`
  - The assistant uses the existing `/api/cockpit/chat` route and the currently
    active Cockpit model.
  - It does not add a second model runtime or assistant-specific backend service.

- `Persistence boundary`
  - `marketplaceHomeLocation` is a Cockpit UI preference only.
  - Real missions are created exclusively through the existing Marketplace API.

## Contract And Safety Constraints

Target system layers:

- Cockpit client/orchestration layer
- existing Cockpit backend route layer only for already-authoritative chat and Marketplace APIs

Relevant contract rules:

- Backend remains the sole authority for authoritative workflow persistence.
- Cockpit remains a client/orchestration layer only.
- Cockpit must not create an independent Marketplace store of truth.
- No alternate mission persistence or scan execution path may be introduced.

What must not change:

- no direct frontend persistence of authoritative mission data
- no new backend mission store outside the existing Marketplace mission service
- no silent mission creation
- no silent scan launch
- no hidden mutation of an existing mission record from a chat turn
- no change to financial truth, extraction, RAG, or commentary authority boundaries

Why this design is safe:

- All create/run side effects remain explicit button-driven calls to the existing
  Marketplace endpoints.
- The assistant draft is local and inspectable before confirmation.
- The active model is reused through the existing chat transport.
- The design is isolated to Cockpit preferences and Marketplace UI behavior.

## Component Design

### 1. Saved Marketplace Home Location

Purpose:

- Persist one user-defined default location for Marketplace mission drafting.

Storage:

- Add `marketplaceHomeLocation: string` to `CockpitPreferences` in
  `cockpit-ui/lib/cockpit-types.ts`.
- Persist it through the existing Zustand store in
  `cockpit-ui/lib/cockpit-store.ts`.
- Concrete store changes required:
  - extend the `CockpitPreferences` TypeScript interface with
    `marketplaceHomeLocation: string`
  - add `marketplaceHomeLocation: ''` to the default `preferences` object in
    `cockpit-ui/lib/cockpit-store.ts`
  - ensure the existing persisted `preferences` object in `partialize(...)`
    continues to include the new field automatically
  - keep the change inside `preferences`, not as a parallel top-level store key

UI:

- Extend `cockpit-ui/components/cockpit/settings/settings-screen.tsx` with a new
  Marketplace subsection containing:
  - `Home location / suburb`
- This subsection must be store-backed, not backend-config-backed:
  - read the current value from `useCockpitStore().preferences.marketplaceHomeLocation`
  - write updates through `useCockpitStore().updatePreferences(...)`
- The existing read-only backend configuration cards remain unchanged; the new
  Marketplace subsection is a separate editable preference control layered into
  the same screen.

Behavior:

- If populated, this value seeds the Marketplace assistant context and initial
  draft location scope.
- If blank, the assistant asks for location early in the conversation.

Non-goals:

- no geolocation permission flow
- no backend persistence for home location

### 2. Marketplace Assistant Panel

Purpose:

- Add a Marketplace-scoped conversational surface inside the Marketplace tab.

Placement:

- Render a new `Marketplace Assistant` card near the top of
  `mission-screen.tsx`, above the manual mission form.

Displayed elements:

- transcript area
- text input
- send button
- assistant session badge or hidden session identity tied to this Marketplace tab only
- small context strip containing:
  - active model
  - saved home location
  - browser health
- live mission draft summary panel
- explicit confirmation buttons once the draft is ready

Seeded opening message:

- If `marketplaceHomeLocation` exists:
  - `I know your default Marketplace location is <location>. What are you hunting for, what budget do you have, and what deal-breakers matter most?`
- Otherwise:
  - `What are you hunting for, what budget do you have, and what location should I use for the search?`

Scope rules:

- The assistant is Marketplace-only.
- It drafts missions and explains scan readiness.
- It does not replace the general Cockpit chat screen.

Session isolation:

- The Marketplace assistant uses its own dedicated `session_id` for `/api/cockpit/chat`.
- It must not reuse the main chat screen’s session ID from the general Cockpit chat workflow.
- The session ID may be generated client-side and stored in `sessionStorage` for the
  lifetime of the Marketplace tab/session.

### 3. Local Mission Draft State

Purpose:

- Maintain a structured, inspectable mission draft before any backend mutation.

Local UI contract:

```ts
type MarketplaceMissionDraft = {
  status: 'collecting' | 'ready'
  missingFields: string[]
  name: string
  brief: string
  categoryHint: string | null
  hardFilters: {
    includeKeywords: string[]
    excludeKeywords: string[]
    locationNames: string[]
    priceMin: number | null
    priceMax: number | null
    radiusKm: number | null
    conditionRequired: string[]
    requiredTerms: string[]
    forbiddenTerms: string[]
  }
  softPreferences: {
    preferredBrands: string[]
    preferredSuburbs: string[]
    preferredConditionTerms: string[]
    niceToHaveTerms: string[]
    urgency: 'low' | 'normal' | 'high'
    priceAggressiveness: 'conservative' | 'balanced' | 'aggressive'
    negotiationExpected: boolean
  }
  searchConfig: {
    queryVariantsEnabled: boolean
    broadeningEnabled: boolean
    maxQueriesPerRun: number
  }
  scanConfig: {
    aggressiveAlerting: boolean
  }
}
```

Draft readiness rules:

- `name` is required
- `brief` is required
- at least one meaningful search constraint must exist:
  - include keywords, or
  - price constraint, or
  - brand/location/deal-breaker constraints

Defaults:

- `hardFilters.locationNames` defaults from `marketplaceHomeLocation`
- `softPreferences.urgency = "normal"`
- `softPreferences.priceAggressiveness = "balanced"`
- `searchConfig.queryVariantsEnabled = true`
- `searchConfig.broadeningEnabled = true`
- `searchConfig.maxQueriesPerRun = 6`
- `scanConfig.aggressiveAlerting = false`

### 4. Assistant Message Protocol

Purpose:

- Keep chat responses readable for the user while allowing the UI to deterministically
  update the mission draft.

Transport:

- Reuse the existing authoritative `/api/cockpit/chat` backend route and the
  current active Cockpit model.
- Do not depend on `sendChatMessage()` unchanged, because the current helper is
  not shaped like the Marketplace API helpers that accept the runtime page
  `apiKey`.
- Add a Marketplace-local chat helper in `cockpit-ui/lib/marketplace-assistant.ts`
  that:
  - accepts the runtime `apiKey`
  - posts to `/api/cockpit/chat`
  - forwards the active model ID
  - disables unrelated retrieval features for this assistant:
    - `web_search = false`
    - `rag = false`
    - `db_diagnostics = false`

Why non-streaming:

- The assistant response must include machine-parseable structured state.
- Blocking responses are simpler and safer than attempting to parse partial
  streaming text for this v1 workflow.

Prompt construction:

- The UI assembles a constrained Marketplace drafting prompt containing:
  - Marketplace assistant session-local transcript, not the main Cockpit chat transcript
  - saved home location
  - browser health status
  - current draft snapshot
  - recent Marketplace assistant transcript
  - the user’s latest message

Required assistant output format:

```json
{
  "assistant_message": "Human-readable reply shown in the transcript.",
  "draft": {
    "...": "partial MarketplaceMissionDraft delta"
  },
  "missing_fields": ["field_name"],
  "ready_to_create": false,
  "suggested_action": "ask_followup"
}
```

Accepted `suggested_action` values:

- `ask_followup`
- `confirm_create`
- `confirm_create_and_run`

Parsing rules:

- The UI parses the full JSON response.
- `assistant_message` is appended to the local transcript.
- `draft` is merged into the local `MarketplaceMissionDraft`.
- If parsing fails, the raw response is shown as assistant text and the draft is
  left unchanged.

### 5. Create And Run Orchestration

Purpose:

- Turn a ready draft into a real Marketplace mission and optionally a real scan.

Flow:

1. User converses with the assistant.
2. Draft reaches `ready`.
3. Assistant presents a confirmation summary:
   - mission name
   - budget
   - default/override location
   - include keywords
   - exclusions or deal-breakers
4. The UI exposes two explicit actions:
   - `Create Mission`
   - `Create + Run Now`

`Create Mission` behavior:

- map the local draft to the existing `MarketplaceMissionUpsertRequest`
- create the mission with `status: "paused"` so it does not get auto-queued by
  the existing Marketplace scheduler immediately after creation
- call `createMarketplaceMission(apiKey, payload)`
- refresh Marketplace state via the existing `load()`
- append a confirmation message to the assistant transcript

`Create + Run Now` behavior:

- create mission first with `status: "paused"` to avoid a scheduler race
- call `triggerMarketplaceScan(apiKey, createdMission.mission_id)`
- after the scan is successfully queued, update the mission to `status: "active"`
  so future scheduled scans are allowed
- refresh Marketplace state via the existing `load()`
- let the existing `Recent Scans` and `Scan Output` surfaces show the queued or running job
- append a confirmation message with mission ID and job ID when available

Mutation rules:

- No create without an explicit button click
- No scan without an explicit button click
- No silent overwrite of an existing mission
- Chat-created missions are new missions only in this wave

### 6. Manual Form Coexistence

Purpose:

- Preserve the transparent manual path and avoid trapping the user in chat-only flow.

Behavior:

- The existing manual mission form remains visible in `mission-screen.tsx`.
- The assistant may optionally offer a `Copy draft to form` behavior, but the
  authoritative create path remains the existing Marketplace API.
- Users can ignore the assistant entirely and keep using the form and existing scan buttons.

## Data Contract Mapping

The assistant draft maps to the existing backend request in
`financial-engine_v2/backend/app/routes/cockpit_api.py:2040`.

Create payload shape:

```ts
{
  name: draft.name,
  brief: draft.brief,
  category_hint: draft.categoryHint,
  status: 'paused',
  hard_filters: {
    include_keywords: draft.hardFilters.includeKeywords,
    exclude_keywords: draft.hardFilters.excludeKeywords,
    location_names: draft.hardFilters.locationNames,
    price_min: draft.hardFilters.priceMin,
    price_max: draft.hardFilters.priceMax,
    radius_km: draft.hardFilters.radiusKm,
    condition_required: draft.hardFilters.conditionRequired,
    required_terms: draft.hardFilters.requiredTerms,
    forbidden_terms: draft.hardFilters.forbiddenTerms,
  },
  soft_preferences: {
    preferred_brands: draft.softPreferences.preferredBrands,
    preferred_suburbs: draft.softPreferences.preferredSuburbs,
    preferred_condition_terms: draft.softPreferences.preferredConditionTerms,
    nice_to_have_terms: draft.softPreferences.niceToHaveTerms,
    urgency: draft.softPreferences.urgency,
    price_aggressiveness: draft.softPreferences.priceAggressiveness,
    negotiation_expected: draft.softPreferences.negotiationExpected,
  },
  search_config: {
    query_variants_enabled: draft.searchConfig.queryVariantsEnabled,
    broadening_enabled: draft.searchConfig.broadeningEnabled,
    max_queries_per_run: draft.searchConfig.maxQueriesPerRun,
  },
  scan_config: {
    aggressive_alerting: draft.scanConfig.aggressiveAlerting,
  },
}
```

Activation sequence:

- `Create Mission`
  - create paused mission only
- `Create + Run Now`
  - create paused mission
  - queue manual scan with `mission_id`
  - on successful queue only, patch mission status to `active`

## Failure Taxonomy

### 1. Assistant Response Parse Failure

Symptoms:

- model returns prose instead of valid JSON
- JSON is malformed or missing required keys

Handling:

- show the raw assistant text in the transcript
- preserve the current draft unchanged
- append a UI warning:
  - `I couldn't parse that assistant response into a mission draft.`

### 2. Incomplete Draft

Symptoms:

- missing `name`
- missing `brief`
- no meaningful search intent

Handling:

- keep draft status at `collecting`
- disable `Create Mission` and `Create + Run Now`
- assistant continues asking targeted follow-up questions

### 3. Mission Create Failure

Symptoms:

- backend rejects payload validation
- request fails at `/api/cockpit/marketplace/missions`

Handling:

- show backend error in Marketplace assistant transcript and screen error banner
- do not clear the draft
- do not mark mission as created

### 4. Scan Launch Failure After Successful Create

Symptoms:

- mission is created successfully
- `/api/cockpit/marketplace/scans` fails

Handling:

- preserve the created mission
- keep the mission `paused`
- show backend scan error in assistant transcript and error banner
- do not roll back the mission

### 5. Browser Health Blocks Scan

Symptoms:

- browser health is not `ready`

Handling:

- assistant can still help draft and create the mission
- `Create + Run Now` may be disabled pre-emptively when browser health is clearly non-ready,
  or the backend error is surfaced if the user still triggers a run path
- existing browser-health guidance remains visible in the Marketplace screen

## Validation Gates

Implementation is acceptable only if all of the following are true:

1. Saved `marketplaceHomeLocation` persists across reloads.
2. Marketplace assistant uses the active model ID from the Cockpit store.
3. Marketplace assistant seeds location from saved settings by default.
4. Marketplace assistant can reach a ready draft without using the manual form.
5. `Create Mission` creates a paused mission through the existing Marketplace mission API.
6. `Create + Run Now` creates paused, runs, then activates through the existing Marketplace APIs.
7. Existing `Active Missions`, `Recent Scans`, and `Scan Output` surfaces update after assistant actions.
8. No hidden mission or scan side effects occur without explicit user confirmation.

## Test Suite

### Frontend Unit Tests

Add:

- `cockpit-ui/components/cockpit/marketplace/marketplace-assistant.test.tsx`
  - seeded greeting uses saved home location
  - assistant updates draft from parsed response
  - create buttons remain disabled until draft is ready
  - parse failure leaves draft unchanged and shows warning
  - assistant uses a Marketplace-local session ID, not the main chat session ID
  - create success path calls the existing Marketplace API client
  - create + run path calls create first, then run, then activate

- `cockpit-ui/lib/marketplace-assistant.test.ts`
  - runtime `apiKey` is forwarded on assistant chat requests
  - assistant request payload disables web/rag/db diagnostics
  - structured response parsing and draft merging behave deterministically

- `cockpit-ui/components/cockpit/settings/settings-screen.test.tsx`
  - marketplace home location is editable and persisted through the store
  - settings uses `updatePreferences(...)` rather than fetched backend config state

### Frontend Integration Tests

Modify:

- `cockpit-ui/components/cockpit/marketplace/mission-screen.test.tsx`
  - assistant panel renders
  - assistant-created mission appears in the existing mission list
  - create + run updates the existing scan selection/output flow

### Backend Tests

Unchanged unless a grounded implementation need emerges:

- existing Marketplace API tests in
  `financial-engine_v2/backend/tests/test_cockpit_marketplace_api.py`
- existing chat transport tests in
  `financial-engine_v2/backend/tests/test_cockpit_api_chat_stream.py`

If a small supporting route/helper is added later, add targeted tests only for that surface.

### Validation Commands

```bash
pnpm --dir cockpit-ui exec vitest run --pool=forks --reporter=verbose \
  components/cockpit/marketplace/marketplace-assistant.test.tsx \
  components/cockpit/marketplace/mission-screen.test.tsx \
  components/cockpit/settings/settings-screen.test.tsx

pnpm --dir cockpit-ui exec tsc --noEmit

pnpm --dir cockpit-ui build
```

## Files Changed

| File | Status | Purpose |
|---|---|---|
| `cockpit-ui/lib/cockpit-types.ts` | modified | add `marketplaceHomeLocation` to Cockpit preferences |
| `cockpit-ui/lib/cockpit-store.ts` | modified | persist Marketplace home location preference |
| `cockpit-ui/components/cockpit/settings/settings-screen.tsx` | modified | expose Marketplace home location input |
| `cockpit-ui/components/cockpit/marketplace/mission-screen.tsx` | modified | host the Marketplace assistant card and wire assistant actions into the existing Marketplace screen |
| `cockpit-ui/components/cockpit/marketplace/marketplace-assistant.tsx` | new | Marketplace-local conversational mission drafting UI |
| `cockpit-ui/lib/marketplace-assistant.ts` | new | prompt builder, response parser, draft merge helpers, payload mapper |
| `cockpit-ui/lib/marketplace-assistant.test.ts` | new | verify assistant auth forwarding and structured parsing helpers |
| `cockpit-ui/components/cockpit/marketplace/marketplace-assistant.test.tsx` | new | focused Marketplace assistant tests |
| `cockpit-ui/components/cockpit/marketplace/mission-screen.test.tsx` | modified | verify assistant integration with existing Marketplace screen |
| `cockpit-ui/components/cockpit/settings/settings-screen.test.tsx` | new | verify Marketplace home location persistence and UI behavior |
| `cockpit-ui/lib/api-client.ts` | unchanged | general chat transport remains unchanged; Marketplace assistant uses the same backend route through a Marketplace-local helper |
| `cockpit-ui/lib/marketplace-api.ts` | unchanged | reused existing authoritative Marketplace mission and scan transport |
| `financial-engine_v2/backend/app/routes/cockpit_api.py` | unchanged | reused existing authoritative chat, mission, and scan routes |

## Out Of Scope

- editing an existing mission from assistant chat
- deleting or archiving missions from assistant chat
- browser geolocation permission flows
- assistant-triggered listing capture or commentary ingestion
- Marketplace match triage chat
- Marketplace seller messaging or negotiation automation
- streaming structured assistant parsing
- a dedicated backend Marketplace assistant route
