# Marketplace Price Intelligence v1 — Design Spec

Status: design-only handoff prep  
Lane: Evaluation  
Collision risk: Medium  
Execution mode: Audit / bounded extension design

## 1. Purpose

Add a **price intelligence layer** to the existing Marketplace workflow so Cockpit can:

1. continuously track dated price observations for selected PC parts across multiple sources,
2. build recent benchmark snapshots from those observations,
3. enrich Marketplace mission matches with a separate **value score** based on recent market data.

This must be implemented as a **bounded extension of the existing Marketplace benchmark lane**, not as a new parallel subsystem.

## 2. Locked decisions

These decisions are now fixed for v1.1:

- Primary product scope: **PC parts generally**, starting with the easiest high-signal categories.
- A mission may search broadly, but **value scoring is anchored to one primary tracked product per mission**.
- **Tracked products can exist standalone** without a mission.
- **Transactional prices (eBay Sold)** are prioritized over asking prices.
- **Facebook Marketplace** is the primary used-market source for asking prices.
- **eBay** is the primary source for transactional (Sold) data.
- **Centre Com** is the first retail anchor source.
- **Gumtree** should be designed for now, but can be deferred from initial implementation if needed.
- Australia-wide coverage is desired, but should start bounded and scale through resumable background collection.
- Value scoring is **additive only** in v1. It must not replace or rewrite existing mission relevance scoring.
- Benchmarks use **Time-Decayed Weighting** (exponential decay) to ensure market responsiveness.
- A small amount of manual review is acceptable and should be used for ambiguous observations.
- Frontend work must target the **Next.js Cockpit web UI**, not the local TUI.

## 3. Goals

### 3.1 Functional goals

- Allow users to create and manage **tracked products**.
- Automatically bootstrap benchmark data for a tracked product via **Active Calibration**.
- Continuously collect and store **dated price observations**.
- Distinguish between **asking prices** and **transactional (Sold) prices**.
- Preserve **listing-level price movement history** where the same listing is seen multiple times.
- Build **Weighted Benchmark snapshots** (fair range, medians, freshness, confidence) using time-decay.
- Allow Marketplace missions to link to one primary tracked product.
- Show each mission match with:
  - existing match/relevance score,
  - separate value score,
  - confidence,
  - fair range,
  - retail anchor,
  - recent price movement summary when available.

### 3.2 Product goals

- Make Marketplace more useful for sourcing deals on PC parts.
- Let a user either:
  - track a product continuously, or
  - create a mission and get value scoring automatically.
- Ensure "Fair Price" reflects actual transaction history (eBay Sold) rather than just seller optimism.
- Keep the system explainable and reviewable.

### 3.3 System goals

- Keep marketplace data as **cockpit-local operational data**.
- Avoid changes to canonical financial truth, company memory, market memory, or core orchestrator logic.
- Keep v1 additive, reversible, and testable.

## 4. Non-goals

These are explicitly out of scope for v1:

- Replacing current mission scoring/ranking with value scoring.
- Multi-product benchmark pooling within one mission.
- Automatic bargain-buy recommendations without confidence/freshness gating.
- Broad retailer integration beyond Centre Com.
- Full substitute-aware “best alternative product” comparison.
- Training models from user feedback.
- Moving Marketplace price data into memory or financial-truth systems.

## 5. Architecture boundary

This feature belongs to the existing Marketplace lane.

### 5.1 Keep inside Marketplace

- tracked products
- benchmark jobs
- raw observations
- listing timelines
- benchmark snapshots
- mission-time value enrichment
- review queue / inclusion overrides

### 5.2 Keep outside

Do **not** place any of the following in:

- canonical financial truth
- company memory
- market memory
- RAG / query orchestrator
- unrelated Cockpit chat storage

### 5.3 Current integration targets

Based on the current Marketplace flow summary, the intended extension points are:

- Next.js Marketplace UI surface under `cockpit-ui/`
- Next BFF marketplace routes under `cockpit-ui/app/api/cockpit/marketplace/*`
- backend Marketplace API in `financial-engine_v2/backend/app/routes/cockpit_api.py`
- backend mission/benchmark/scanner services such as:
  - `financial-engine_v2/backend/app/services/marketplace_mission_service.py`
  - `financial-engine_v2/backend/app/services/marketplace_scanner.py`
  - `financial-engine_v2/backend/app/services/marketplace_benchmark_service.py`
- marketplace state storage in `financial-engine_v2/cockpit/storage/state.py`

This is a **web Marketplace extension**, not a local-TUI feature.

## 6. Core domain model

## 6.1 Tracked product

A tracked product is the reusable benchmark anchor for one normalized PC part.

Examples:

- NVIDIA RTX 4070 Super 12GB
- AMD Ryzen 7 7800X3D
- Samsung 990 Pro 2TB
- Corsair Vengeance DDR5 32GB 6000 CL30

A tracked product owns:

- canonical identity
- category-aware normalization rules
- aliases / synonyms
- negative/junk patterns
- source policy
- benchmark freshness state
- historical observations
- benchmark snapshots

## 6.2 Mission

A Marketplace mission remains the existing discovery workflow.

A mission may:

- search broadly,
- link to **one primary tracked product**,
- use that tracked product’s latest benchmark snapshot for value enrichment.

## 6.3 Observation

An observation is one dated capture of a listing/product price from a source.

Observations are append-only and auditable.

## 6.4 Listing timeline

A listing timeline tracks the history of the same listing over time:

- first seen
- last seen
- latest price
- prior prices
- number of price changes

## 6.5 Benchmark snapshot

A benchmark snapshot is the mission-facing rollup for a tracked product:

- recent medians
- fair range
- sample size
- freshness
- confidence
- retail anchor context

## 7. Product normalization rules

This feature will succeed or fail based on correct product normalization.

### 7.1 High-priority v1 categories

Start with:

- GPUs
- CPUs
- RAM
- SSDs

These are the highest-value and most standardized categories for v1.

### 7.2 Category-specific extraction examples

#### GPU

Extract where possible:

- vendor
- model family
- exact SKU/chip
- VRAM
- suffixes like `Ti`, `Super`, `XT`, `XTX`

#### CPU

Extract where possible:

- family
- exact SKU
- suffix
- generation
- socket when available

#### RAM

Extract where possible:

- DDR generation
- total capacity
- module count
- speed
- CAS latency if present

#### SSD

Extract where possible:

- brand/model
- capacity
- NVMe vs SATA
- PCIe generation when present

### 7.3 Negative/junk patterns

Treat these as strong exclusions or review triggers:

- wanted
- WTB
- swap
- trade
- box only
- broken
- for parts
- not working
- bundle
- full PC / gaming PC when tracking a component
- missing component disclaimers
- placeholder prices such as `$1`

## 8. Source policy

## 8.1 Facebook Marketplace

Role in v1:

- primary used-market price source
- main observation history source
- main fair-range signal

Coverage policy:

- broad Australia-wide intent
- initial implementation should start bounded and scale through resumable shards

## 8.2 Centre Com

Role in v1:

- retail new-price anchor
- supporting context only
- not the primary truth source for used-value scoring

Constraint:

- Centre Com may have live fetch instability / fallback behavior, so benchmark outputs must surface freshness and provenance clearly.

## 8.3 Gumtree

Role in v1:

- planned adapter
- schema and architecture should support it
- implementation may be deferred until core FB + Centre Com flow is stable

## 9. Storage model

Start with **dedicated Marketplace price tables** in the existing Cockpit/local Marketplace state layer.

If observation volume grows later, raw history can be moved behind the same API boundary to a dedicated store without changing UI contracts.

## 9.1 Required tables

### `marketplace_tracked_products`

Purpose: reusable benchmark anchors.

Suggested fields:

- `tracked_product_id`
- `canonical_name`
- `category`
- `brand`
- `model_family`
- `variant`
- `attributes_json`
- `aliases_json`
- `negative_terms_json`
- `location_policy`
- `source_policy_json`
- `status`
- `created_at`
- `updated_at`

### `marketplace_price_observations`

Purpose: append-only dated observation log.

Suggested fields:

- `observation_id`
- `tracked_product_id`
- `source`
- `observed_at`
- `source_listing_id`
- `listing_fingerprint`
- `title`
- `price`
- `currency`
- `url`
- `location`
- `seller_type`
- `condition_label`
- `product_match_confidence`
- `is_transactional` (binary flag for sold data)
- `capture_mode`
- `provenance_json`
- `included_in_rollup`
- `review_state`

### `marketplace_listing_timelines`

Purpose: per-listing history.

Suggested fields:

- `listing_fingerprint`
- `tracked_product_id`
- `source`
- `first_seen_at`
- `last_seen_at`
- `latest_price`
- `prior_prices_json`
- `price_change_count`
- `active_state`

### `marketplace_benchmark_snapshots`

Purpose: mission-facing rollups.

Suggested fields:

- `benchmark_snapshot_id`
- `tracked_product_id`
- `as_of`
- `sample_size_total`
- `sample_size_facebook`
- `sample_size_centrecom`
- `median_7d`
- `median_30d`
- `median_90d`
- `fair_low`
- `fair_high`
- `retail_anchor_price`
- `freshness_status`
- `confidence_label`
- `notes_json`

### `marketplace_mission_product_links`

Purpose: one primary tracked product per mission.

Suggested fields:

- `mission_id`
- `tracked_product_id`
- `link_type` (`primary` only in v1)

### `marketplace_observation_reviews`

Purpose: lightweight review / override log.

Suggested fields:

- `review_id`
- `observation_id`
- `review_action`
- `review_reason`
- `reviewed_at`
- `reviewer`
- `notes`

## 10. State model

### 10.1 Tracked product state

- `draft`
- `active`
- `disabled`

### 10.2 Benchmark state

- `building`
- `provisional`
- `fresh`
- `stale`
- `low_data`
- `error`

### 10.3 Observation review state

- `pending_review`
- `accepted`
- `rejected`

### 10.4 Mission match value state

- `pending`
- `scored`
- `low_confidence`
- `unavailable`

## 11. Functional flow

## 11.1 Flow A — direct tracked-product creation

User enters a product to track.

System should:

1. parse user input,
2. classify category,
3. propose canonical product profile,
4. generate aliases and negative terms,
5. persist tracked product,
6. enqueue bootstrap benchmark job,
7. show benchmark state as `building`.

## 11.2 Flow B — mission-first creation

User creates a Marketplace mission.

System should:

1. create mission as normal,
2. infer whether the mission clearly targets one primary product,
3. if yes, auto-create or suggest a linked tracked product,
4. enqueue bootstrap benchmark automatically,
5. show benchmark state inline on the mission screen,
6. allow the mission to run immediately even if benchmark is still building.

## 11.3 Flow C — bootstrap benchmark

Purpose: provide fast first-usefulness.

Order:

1. load tracked product profile,
2. generate query variants,
3. build initial source plan,
4. attempt Centre Com retail anchor capture,
5. run small Facebook sweep,
6. accept only high-confidence observations,
7. build provisional benchmark snapshot,
8. expose fair range / confidence / freshness in UI.

Important rule:

- bootstrap is not exhaustive;
- it should produce a useful first estimate quickly.

## 11.4 Flow D — continuous collection

For each active tracked product, run recurring collection.

Per cycle:

1. load tracked product profile,
2. build shards (`source × query variant × location bucket`),
3. execute shard,
4. parse results,
5. normalize candidate product match,
6. dedupe observations,
7. store raw observations,
8. update listing timelines,
9. rebuild rollup when enough observations changed.

## 11.5 Flow E — mission-time value enrichment

Current mission scanning remains primary for discovery.

Additive enrichment flow:

1. mission scan runs using existing pipeline,
2. listing passes current relevance flow,
3. system checks for linked primary tracked product,
4. system loads latest benchmark snapshot,
5. system runs listing-to-product confidence check,
6. if confidence sufficient, system computes value assessment,
7. persist value fields onto the saved match,
8. UI renders value context on cards and detail views.

Important v1 rule:

- value score must not replace or silently overwrite match score.

## 11.6 Flow F — review and correction

Low-confidence or suspicious observations should enter a review queue.

Review actions:

- accept
- reject
- wrong variant
- junk listing
- bundle
- parts / broken
- optional condition correction

Review affects rollup inclusion, but raw observations remain stored.

## 12. Australia-wide collection strategy

“Search Australia-wide” must not mean one giant blocking run.

### 12.1 Recommended v1 approach

- start with a bounded initial set of AU location buckets,
- keep coverage resumable,
- gradually broaden via scheduler,
- persist shard progress and last-run state.

### 12.2 Shard model

Use shards such as:

- source
- query variant
- AU location bucket

This allows:

- partial progress,
- scaling without giant runs,
- cancellation/resume,
- background deep sweeps.

## 13. Job model and scheduling

## 13.1 New benchmark job types

- `benchmark_bootstrap`
- `benchmark_refresh`
- `benchmark_deep_sweep`

## 13.2 Priority order

1. mission scans
2. benchmark bootstrap
3. benchmark refresh
4. benchmark deep sweep

This keeps user-facing missions responsive.

## 13.3 Key scheduling rule

A mission should never be blocked on a full deep benchmark refresh.

If benchmark data is stale or incomplete:

- use the latest acceptable snapshot,
- show benchmark state honestly,
- optionally trigger refresh in background.

## 14. Scoring model

## 14.1 Existing match/relevance score

Keep current Marketplace mission scoring logic intact.

## 14.2 New value score

This is a separate deterministic overlay.

### Inputs

- asking price
- recent used-market benchmark
- Centre Com retail anchor
- condition label
- sample size
- freshness
- variant certainty
- source diversity
- local vs national weighting
- listing price-cut history

### Outputs

- `value_score` (0–100)
- `value_label` (`excellent`, `good`, `fair`, `weak`, `unclear`)
- `value_confidence` (`high`, `medium`, `low`)
- `fair_range`
- `used_median`
- `retail_anchor`
- `price_movement_summary`
- short explanation

### Required principles

- deterministic
- explainable
- confidence-aware
- freshness-aware
- sample-size-aware
- penalty for ambiguous product match

### Important constraint

Do not use Centre Com as the primary truth source for used-value scoring.
It is an anchor, not the main benchmark cohort.

## 15. Local vs national weighting

Weighting should be category-aware.

### National-friendly categories

Use national comps more freely for:

- GPUs
- CPUs
- RAM
- SSDs

### More local-sensitive categories

Potentially weight locality more for later categories like:

- cases
- large coolers
- bulky accessories

## 16. UI / UX requirements

## 16.1 New Marketplace surface: tracked products

Add a tracked-products view within Marketplace.

Core actions:

- create tracked product
- refresh benchmark
- disable tracking
- inspect benchmark details
- review low-confidence observations
- link/unlink mission

## 16.2 Mission screen enhancements

Mission create/edit should support:

- optional primary tracked product link,
- auto-suggested tracked product when mission is specific enough,
- visible benchmark state.

## 16.3 Match card requirements

Each saved match should be able to show:

- asking price
- match/relevance score
- value label
- value confidence
- fair range

## 16.4 Match detail requirements

Each detailed match view should be able to show:

- asking price
- recent used median
- fair range
- Centre Com retail anchor
- price movement timeline when available
- benchmark freshness
- confidence explanation

## 16.5 Honest system states

The UI must clearly surface states like:

- `benchmark building`
- `value pending`
- `insufficient data`
- `retail anchor only`
- `stale benchmark`
- `variant ambiguous`

## 17. API surface (proposed)

These are design targets, not confirmed existing endpoints.

### Tracked products

- `POST /api/cockpit/marketplace/tracked-products`
- `GET /api/cockpit/marketplace/tracked-products`
- `GET /api/cockpit/marketplace/tracked-products/{id}`
- `POST /api/cockpit/marketplace/tracked-products/{id}/refresh`
- `POST /api/cockpit/marketplace/tracked-products/{id}/disable`

### Benchmark data

- `GET /api/cockpit/marketplace/tracked-products/{id}/snapshot`
- `GET /api/cockpit/marketplace/tracked-products/{id}/observations`
- `GET /api/cockpit/marketplace/tracked-products/{id}/timelines`

### Mission link

- `POST /api/cockpit/marketplace/missions/{mission_id}/link-product`
- `DELETE /api/cockpit/marketplace/missions/{mission_id}/link-product`

### Review actions

- `POST /api/cockpit/marketplace/observations/{id}/review`
- `GET /api/cockpit/marketplace/review-queue`

## 18. What should be automated

Automate by default:

- tracked-product inference from mission
- canonical profile proposal
- alias generation
- bootstrap benchmark job
- recurring benchmark refresh
- observation dedupe
- listing timeline maintenance
- snapshot rebuild
- mission-time value enrichment
- stale detection
- low-confidence review-queue placement

## 19. What may remain manual

Allow manual intervention for:

- confirming/correcting the canonical tracked product
- rejecting junk observations
- rejecting wrong variants
- correcting condition/category edge cases
- pinning/overriding a retail anchor if needed

## 20. Safe implementation order

The recommended implementation order is:

1. audit current benchmark/state/UI surfaces,
2. add tracked-product storage and models,
3. add benchmark job types and scheduler integration,
4. implement product normalization for v1 categories,
5. implement raw observation persistence and listing timelines,
6. implement bootstrap benchmark flow,
7. integrate Centre Com anchor into snapshot building,
8. implement Facebook observation collection for tracked products,
9. build benchmark snapshots / rollups,
10. link mission ↔ tracked product,
11. add mission-time value enrichment,
12. add review queue and review actions,
13. add tracked-products UI and value rendering,
14. manually test real flows where environment allows,
15. expand AU coverage and add Gumtree later.

## 21. Acceptance criteria for v1

v1 should be considered acceptable when all of the following are true:

### 21.1 Tracked product core

- user can create a tracked product,
- tracked product persists across restart,
- tracked product shows benchmark state,
- tracked product can refresh benchmark.

### 21.2 Observation/history core

- dated observations are stored,
- repeated sightings of the same listing update listing timeline,
- price movement history is visible in stored state and/or detail UI.

### 21.3 Benchmark core

- bootstrap benchmark produces a provisional snapshot,
- benchmark freshness/confidence are surfaced,
- low-data and error states are visible and honest.

### 21.4 Mission integration core

- mission can link to one primary tracked product,
- mission match results preserve current relevance scoring,
- value score appears separately on eligible matches,
- ambiguous or low-data cases do not fake confidence.

### 21.5 Review core

- suspicious observations can be reviewed,
- rejected observations are excluded from rollups,
- raw observation record remains retained.

### 21.6 UX core

- user can understand whether the system is still building, fresh, stale, or uncertain,
- UI is usable without reading internal logs.

## 22. Manual verification checklist

When this moves to implementation, manual verification should include:

1. create a tracked product,
2. verify bootstrap benchmark starts,
3. verify tracked product persists after reload/restart,
4. inspect stored observations,
5. verify listing timeline updates when a listing is seen again,
6. link a mission to the tracked product,
7. run mission and verify value score rendering,
8. verify pending / low-data / stale states,
9. review/reject a bad observation and confirm rollup changes,
10. verify Centre Com anchor metadata appears when available,
11. verify at least one real browser-backed Facebook path if environment permits,
12. if real Facebook verification is blocked, document the exact blocker and verify all non-blocked flows.

## 23. Risks and mitigations

### 23.1 Wrong variant matching

Risk:

- bad normalization will poison benchmark quality.

Mitigation:

- one primary tracked product per mission,
- category-aware parsing,
- penalties for ambiguity,
- review queue.

### 23.2 Asking prices are not sale prices

Risk:

- benchmark may overstate fair market value.

Mitigation:

- keep explanations honest,
- incorporate listing price-cut history where available,
- keep confidence separate from score.

### 23.3 Australia-wide coverage cost/noise

Risk:

- broad search becomes slow or noisy.

Mitigation:

- shard coverage,
- resumable background collection,
- bootstrap fast path,
- deep sweep lower priority.

### 23.4 Source instability

Risk:

- Facebook challenge/login or Centre Com fetch instability may reduce reliability.

Mitigation:

- explicit freshness/provenance states,
- background refresh,
- partial-state UX,
- fall back to latest acceptable snapshot.

### 23.5 Collision risk on shared Marketplace surfaces

Risk:

- shared Marketplace API/state files may already be dirty or in active use.

Mitigation:

- additive changes only,
- extend existing benchmark lane,
- avoid broad rewrites.

## 24. Deferred work

Defer until after v1 stabilizes:

- Gumtree full adapter
- additional retailer anchors
- multi-product benchmark pooling
- substitute-aware bargain comparisons
- sold-price inference
- ranking/alert logic driven directly by value score
- broader hardware categories with weaker normalization
- advanced analytics beyond current benchmark snapshots

## 25. Notes for the later Codex handoff

This section is **not** the Codex prompt. It records constraints the later handoff should enforce.

### 25.1 Subagents

Use subagents selectively, not freely:

- one for backend/state/benchmark implementation,
- one for frontend/BFF/UI wiring,
- one for deployment/manual verification/source-flow validation.

The parent agent must reconcile all findings into one implementation path.
No competing architecture proposals.

### 25.2 Deployment expectation

When implementation begins, Codex should be expected to:

- bring up the relevant local backend and Marketplace UI,
- apply any schema/bootstrap path required,
- verify data persists across restart where possible,
- report exact blockers if real-source verification is constrained.

### 25.3 Manual testing expectation

Codex should manually test where possible, not rely only on mocked/unit paths.

At minimum, it should try to verify:

- tracked-product creation,
- benchmark bootstrap,
- observation persistence,
- mission link + value rendering,
- stale/low-data states,
- review actions,
- restart persistence,
- at least one real browser-backed source path where environment allows.

### 25.4 Safety constraints for implementation

The later implementation handoff should explicitly forbid:

- rewriting existing Marketplace match scoring in v1,
- moving Marketplace price data into memory or financial truth,
- creating a parallel Marketplace application,
- blocking mission scans on deep benchmark refresh,
- overbuilding Gumtree before FB + Centre Com are stable.

## 26. Summary

The clean v1 is:

- one primary tracked product per mission,
- tracked products can exist standalone,
- Facebook provides the main used-market signal,
- Centre Com provides the first retail anchor,
- Gumtree is planned but can be deferred,
- value scoring is additive and explainable,
- Australia-wide collection is broad but resumable,
- manual review is reserved for ambiguous/junk cases,
- the UI must be honest about freshness, uncertainty, and data quality.
