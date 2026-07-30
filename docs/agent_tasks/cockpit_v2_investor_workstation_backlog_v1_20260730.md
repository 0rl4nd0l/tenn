# Cockpit V2 Investor Workstation Backlog

Status: ready for implementation sequencing

Programme: Cockpit V2

Prepared: 2026-07-30

Owner: Orlando

Pilot companies: BHP, EIQ, CSL, SHL

## Provenance

- Source branch: `fix/llama-router-fail-closed-v1-20260726`
- Source commit: `bed1c228a6edad46ec435ab57c8986e198492d45`
- Source tree: `38279471c8b6c7171273c0dcbba9a6d19fe57b59`
- Remote verification: unavailable; the selected source branch is local-only.
- Tenn Git guard: pass; no matching active work was found.
- Codex X run: `20260730T075419Z-bed1c228a6-10f22c`
- Codex X session: `019fb206-36a8-7c40-b6b2-307f643dc226`
- Requested/actual model: GPT-5.6 Sol / GPT-5.6 Sol
- Codex X verdict: `ACCEPTABLE_WITH_CHANGES`
- Codex X role: fresh read-only decomposition reviewer. It made no source
  changes.

Codex X found that this is an extension, consolidation, and migration programme,
not a greenfield rebuild. Existing Cockpit chat, tool, news, memory, job, and UI
machinery must be reused or explicitly retired. New parallel subsystems are out
of scope unless a ticket proves that the existing authority cannot be extended.

## Programme contract

- Build on a parallel `/v2` route. Do not redirect `/` or remove old routes
  until an independently approved cutover.
- This is permanently a single-user, private ASX/AUD workstation. Do not add
  multi-user or RBAC product work.
- Preserve the dense terminal feel, keyboard-first desktop operation, charts,
  and widgets. Mobile may be intentionally limited but must remain usable.
- Primary navigation is Today, Companies, Research, Portfolio, Activity, and
  System. Marketplace remains a separate workspace.
- Runtime UI must never substitute mock, fixture, simulated, or inferred data.
  Honest empty, stale, partial, and unavailable states are required.
- Evidence, derived insight, and personal thesis are distinct. Canonical
  personal-knowledge promotion always requires an explicit preview and
  confirmation.
- The assistant may autonomously read, search, follow news, and maintain a
  bounded discovery watchlist and scratch store. It cannot autonomously mutate
  the owner's holdings, watchlist, or canonical company memory.
- One model-independent structured agent loop owns research. Mandatory tool use
  is selected by intent. News and announcement work is canonical-local-first
  with bounded read-only web fallback when local coverage is stale or empty.
- Tool arguments, results, provenance, freshness, claim coverage, retry,
  fallback, and budgets are structured and validated. Reports retain durable
  research receipts.
- Runtime, scheduler, queue, DB, Qdrant, GPU, model, extraction, backfill,
  paid-resource, production-data, merge, deployment, and cutover actions remain
  Tier 2 or separately approval-gated as applicable.

## Execution shape

Every ticket below is independently grabbable after its dependencies clear.
Each implementation uses one fresh implementer session and one fresh independent
review session. Code delivery does not satisfy a runtime-evidence ticket.

### TICKET CXV2-001 — Freeze V2 evidence, freshness, and performance contracts

Goal:
Define the versioned shared contract that every later V2 API, tool, receipt, and
screen must use.

Context:
Existing Cockpit paths use overlapping evidence labels, freshness rules,
degraded codes, and response shapes. Canonical news and announcement ownership,
receipt storage semantics, and numeric performance budgets must be decided here
from live repository evidence before implementation diverges.

Scope:
- `shared/evidence_labels.py`
- new focused contracts under `financial-engine_v2/cockpit/core/contracts/`
- Cockpit API response models
- TypeScript contracts under `cockpit-ui/types/` or `cockpit-ui/lib/v2/`
- one architecture decision under `docs/architecture/`

Non-goals:
Tool execution, provider changes, UI pages, data migration, ingestion, or
runtime activation.

Dependencies:
None.

Acceptance:
- Evidence, derived insight, and personal thesis are distinct types.
- Sources carry stable identity, provenance, observed/published times, and
  freshness state.
- Receipts represent claims, supporting and contradicting evidence, tool
  attempts, budgets, and terminal outcome.
- Owner-facing availability states are separate from raw System diagnostics.
- The ADR names canonical news and announcement authorities and projection
  boundaries without pretending absent evidence is resolved.
- Measurable budgets are approved for cached UI, uncached read UI, first tool
  trace, first accepted evidence, and terminal research.
- Existing response shapes have a compatibility and retirement table.

Focused validation:
Python and TypeScript schema round trips, contract unit tests, changed-file
lint, and `git diff --check`.

Stop:
Stop `DATA_MISSING` if source identity, freshness, or storage authority cannot
be proven without inspecting or mutating production data.

### TICKET CXV2-002 — Establish the authoritative tool safety registry

Goal:
Make one registry authoritative for tool schemas, mutation class, data tier,
timeout, retry policy, health probe, and permitted research modes.

Context:
Tool metadata is spread across definitions, executors, actions, backend clients,
and operations manifests. Autonomous research must never discover or invoke a
mutating capability.

Scope:
- `financial-engine_v2/cockpit/core/tool_definitions.py`
- `financial-engine_v2/cockpit/core/tool_executor.py`
- `financial-engine_v2/cockpit/core/tools.py`
- action guards and backend tool adapters
- YouTube lookup, transcript, ingestion, review, and channel-watch definitions
- focused registry and dispatch tests

Non-goals:
Executing tools, ingesting YouTube data, changing watchlists, running backfills,
or activating health probes.

Dependencies:
CXV2-001.

Acceptance:
- Missing or contradictory mutation metadata fails closed.
- Autonomous research receives only explicitly read-only tools.
- Every YouTube capability is classified individually by actual behavior.
- Aliases and compatibility dispatch cannot bypass the registry.
- Confirmation cannot turn an unregistered capability into an executable one.
- Duplicate legacy definitions are reconciled or marked for retirement.

Focused validation:
Registry invariant tests, complete dispatchable-tool enumeration, alias attacks,
false-read-only tests, lint, and `git diff --check`.

Stop:
Stop if any dispatch path bypasses the registry; do not weaken classification
to accommodate it.

### TICKET CXV2-003 — Consolidate Cockpit research on one structured agent loop

Goal:
Route Cockpit research through one model-independent loop whose tool, evidence,
and safety behavior does not change with inference provider.

Context:
The repository has a Cockpit `AgentLoop`, direct `tenn_chat` generation, hybrid
routing, `/api/chat`, and `/api/cockpit/chat`. Provider preference currently
changes behavior and can bypass expected tool use.

Scope:
- `financial-engine_v2/cockpit/core/agent_loop.py`
- response parsing, query intent, chat route decision, and hybrid router
- `financial-engine_v2/backend/app/routes/cockpit_api.py`
- compatibility boundaries in `routes/chat.py` and `services/tenn_chat.py`
- related focused tests

Non-goals:
Deleting compatibility endpoints, web fallback, UI work, runtime model changes,
or provider deployment.

Dependencies:
CXV2-001 and CXV2-002.

Acceptance:
- Intent fixes mandatory capability classes before model invocation.
- Provider selection changes inference transport only.
- Tool arguments and results validate against registry schemas.
- Malformed output, timeout, retry, iteration, and budget exhaustion terminate
  within configured bounds.
- `/api/cockpit/chat` is V2 authority; old paths are adapters or deprecated.
- No `api_preferred` path silently bypasses mandatory tools.

Focused validation:
Provider-parametrized loop tests, malformed schema cases, no-tool-bypass tests,
route compatibility tests, lint, and `git diff --check`.

Stop:
Stop if a provider requires a different safety or evidence path; do not add
provider-specific exceptions.

### TICKET CXV2-004 — Deliver canonical-local-first news and announcement fallback

Goal:
Guarantee local canonical retrieval first and bounded read-only web fallback
when news or announcement coverage is empty, stale, or unavailable.

Context:
Local news chunks, ASX announcements, freshness helpers, and web integrations
exist, but routing and freshness behavior are fragmented.

Scope:
- news freshness and query-intent modules
- the unified agent loop and read-only tool adapters
- existing Brave/web fetch integrations behind one provider adapter
- backend news health, query orchestration, and source registry services
- deterministic focused tests for BHP, EIQ, CSL, and SHL

Non-goals:
Scheduled ingestion, writing web results to canonical storage, paid-provider
activation, or browser UI.

Dependencies:
CXV2-003.

Acceptance:
- Freshness derives from source timestamps and the CXV2-001 SLA.
- Fresh local coverage suppresses unnecessary web fallback.
- Empty, stale, or unavailable local coverage records a fallback attempt.
- Web evidence is source-identified, bounded, read-only, and never labelled as
  canonical ingestion.
- Failure of both sources yields a useful explicit limitation without invented
  citations.

Focused validation:
Local-fresh, local-stale, local-empty, web-failure, malformed-result, and budget
tests for all four pilots using deterministic adapters.

Stop:
Stop if canonical records lack stable identifiers or adequate timestamps; open
the exact data-contract blocker rather than guessing freshness.

### TICKET CXV2-005 — Persist research receipts and enforce claim coverage

Goal:
Attach a durable receipt to every substantive report or conclusion and prevent
unsupported factual claims from reaching the final answer.

Context:
Sources, evidence guards, sessions, and traces exist, but there is no single
durable claim-to-evidence receipt.

Scope:
- a focused receipt model and service under backend services
- agent loop, source, and tool-call trace integration
- Cockpit receipt API endpoints
- claim-verification integration
- persistence and serialization tests

Non-goals:
UI rendering, canonical thesis promotion, production migrations, backfill, or
runtime data inspection.

Dependencies:
CXV2-003 and CXV2-004.

Acceptance:
- Each factual claim is supported, contradicted, explicitly uncertain, or
  suppressed.
- Citations resolve to stable receipt evidence and freshness metadata.
- Failed attempts, fallbacks, malformed results, and exhausted budgets remain
  in the receipt.
- Persistence is idempotent and bound to the chat/report revision.
- Contradictory evidence is preserved and affects confidence.
- Stored reports cannot outlive or silently lose their evidence identities.

Focused validation:
Serialization and persistence round trips, fabricated-citation rejection,
contradiction tests, redaction tests, lint, and `git diff --check`.

Stop:
Stop if durable storage requires a live DB migration or production write; leave
the migration/activation as an explicit later gate.

### TICKET CXV2-006 — Make ingestion health authoritative in code

Goal:
Define scheduler ownership, freshness-SLA health, progress, failure, and
recovery contracts without activating or running ingestion.

Context:
Celery news tasks, root scripts, health snapshots, Qdrant loading, cron, and
multiple stores coexist. Configuration is not proof of successful ingestion.

Scope:
- backend news tasks, Celery configuration, news health, and job tracking
- relevant root ingestion scripts and audit helpers
- pure status builders and scheduler-side-effect tests
- pipeline ownership and recovery documentation

Non-goals:
Scheduler activation, ingestion execution, queue/DB/Qdrant writes, extraction,
backfill, production-data inspection, or service changes.

Dependencies:
CXV2-001 and CXV2-002.

Acceptance:
- One documented pipeline owns each canonical stage.
- Health exposes last attempt, last success, watermarks, lag, failure,
  retryability, and SLA breach.
- Recovery commands are approval-gated actions, never health-read side effects.
- Duplicate scripts/jobs have explicit migrate, keep, or retire dispositions.
- Import and startup tests prove scheduling is not silently activated.

Focused validation:
Synthetic manifest tests, import side-effect tests, configuration lint, and
`git diff --check`.

Stop:
Stop before any runtime, queue, DB, Qdrant, scheduler, extraction, backfill, or
production-data action.

### TICKET CXV2-007 — Add the isolated V2 terminal shell

Goal:
Provide the parallel keyboard-first shell and navigation without changing the
legacy Cockpit.

Context:
The current sidebar exposes many implementation-oriented routes. V2 needs a
stable owner workflow while retaining the existing terminal character.

Scope:
- `cockpit-ui/app/v2/layout.tsx`
- `cockpit-ui/app/v2/page.tsx`
- new `cockpit-ui/components/v2/shell/`
- new `cockpit-ui/lib/v2/navigation.ts`
- existing terminal theme and UI primitives
- shell-focused component and browser tests

Non-goals:
Page data, redirecting `/`, deleting old routes, RBAC, or Marketplace feature
work.

Dependencies:
CXV2-001.

Acceptance:
- Today, Companies, Research, Portfolio, Activity, and System are keyboard
  accessible with visible focus.
- Marketplace is structurally and visually separate from primary navigation.
- Desktop remains dense and terminal-like; mobile is limited but usable.
- `/` and legacy routes remain unchanged.
- V2 code imports no runtime mock or fixture data.

Focused validation:
Component tests, Playwright navigation/keyboard/mobile smoke, accessibility
checks, a V2 mock-import guard, lint, and `git diff --check`.

Stop:
Stop if implementation requires replacing, redirecting, or deleting an existing
route.

### TICKET CXV2-008 — Deliver the holdings-first session-aware Today page

Goal:
Make `/v2` immediately useful with real holdings, owner watchlist, market
session state, attention items, and freshness.

Context:
Existing home, holdings, watchlist, market-session, mover, and attention APIs
can be adapted. The current home imports mock data and must not be copied.

Scope:
- V2 Today route and components
- one V2 Today API adapter
- existing backend home routes/services only where the contract is incomplete
- Today component and browser tests

Non-goals:
Assistant discovery, company detail, synthetic movers, or recovery execution.

Dependencies:
CXV2-007.

Acceptance:
- Holdings and owner watchlist dominate the page.
- ASX session state and source timestamps are visible.
- Quotes, news, and attention items expose provenance and freshness.
- Partial, stale, empty, and unavailable states use owner language.
- Raw diagnostic codes are reachable through System, not normal page copy.
- Empty data remains empty; no mock, fixture, or simulated substitution occurs.

Focused validation:
Open, closed, stale, partial, empty, and unavailable contract/component cases;
read-only browser adapter test; no-fixture guard.

Stop:
Stop if a displayed value cannot be traced to a backend source; omit it rather
than infer it.

### TICKET CXV2-009 — Add the reusable company workspace aggregate contract

Goal:
Expose one provenance-aware backend aggregate for any company workspace.

Context:
Price, exposure, financial truth, announcements, news, documents, memory,
risks, and chat context currently arrive through overlapping routes.

Scope:
- a focused company workspace service
- V2 company aggregate routes and response models
- adapters over existing financial truth, news, document, and memory services
- aggregate contract tests for BHP, EIQ, CSL, and SHL

Non-goals:
UI implementation, ticker-specific defaults, thesis mutation, data backfill, or
retiring existing routes.

Dependencies:
CXV2-001, CXV2-004, and CXV2-005.

Acceptance:
- One response contract supports all four pilots.
- Each section reports source identity, freshness, and availability.
- Evidence, derived insight, and personal thesis remain separate.
- Partial sections do not make the whole workspace appear complete.
- Missing coverage is honest and never filled by fixtures or ticker-specific
  fabrication.
- Company chat context is ticker-bound and can explicitly broaden for a
  comparison.

Focused validation:
Aggregate tests for complete, partial, empty, stale, and error cases for each
pilot; schema round trips; lint; `git diff --check`.

Stop:
Stop if a pilot requires silent backfill, production-data mutation, or bespoke
fabricated defaults.

### TICKET CXV2-010 — Deliver reusable pilot Company workspaces

Goal:
Render complete company workspaces for BHP, EIQ, CSL, and SHL from the shared
aggregate contract.

Context:
The UI should consolidate existing price, financial, announcement, document,
memory, risk, and chat capabilities rather than duplicate them.

Scope:
- `cockpit-ui/app/v2/companies/`
- `cockpit-ui/components/v2/company/`
- `cockpit-ui/lib/v2/company-api.ts`
- reuse of existing chart, document, evidence, and chat primitives
- company-focused component and browser tests

Non-goals:
Backend source redesign, ticker-specific pages, automatic promotion, data
backfill, or retirement of legacy pages.

Dependencies:
CXV2-007 and CXV2-009.

Acceptance:
- One reusable workspace renders all four pilots.
- Price/exposure, financials, announcements/news, documents, thesis, risks,
  evidence, and company-aware chat/actions are reachable.
- Evidence, derived insight, and personal thesis are visually distinct.
- Empty sections explain why and expose freshness/provenance.
- Cross-company comparison requires an explicit scope broadening.
- No V2 company component imports runtime fixtures.

Focused validation:
Browser scenarios for all pilots with partial, empty, stale, and failed
sections; keyboard navigation; no-fixture guard.

Stop:
Stop if the UI must infer section completeness or tool success from prose.

### TICKET CXV2-011 — Deliver persistent Research with trace and receipts

Goal:
Provide persistent chats and reports with a concise live tool trace, expandable
validated detail, and durable receipts.

Context:
Existing full chat, session stores, source drawer, SSE events, and claim
verification should be migrated and reused.

Scope:
- `cockpit-ui/app/v2/research/`
- `cockpit-ui/components/v2/research/`
- refactoring of existing chat and source components where appropriate
- backend-authoritative session/report persistence integration
- receipt and trace API integration

Non-goals:
Canonical promotion, discovery automation, deleting `/full-chat`, or
browser-storage-only authority.

Dependencies:
CXV2-005 and CXV2-007.

Acceptance:
- Sessions and report revisions survive reload through backend authority.
- Trace shows capability, state, duration, retry, and fallback succinctly.
- Validated arguments/results are expandable and safely redacted.
- Conclusions link to durable receipts and claim evidence.
- Malformed output, failure, and budget exhaustion remain useful and visible.
- UI never infers successful tool use from assistant prose.

Focused validation:
SSE reducer tests, persistence reload test, malformed-event test,
browser-visible receipt test, and redaction checks.

Stop:
Stop if persistence or trace authority would fall back silently to browser-only
state.

### TICKET CXV2-012 — Add confirmed personal-knowledge promotion

Goal:
Let important conclusions offer a specific, auditable promotion into canonical
personal knowledge.

Context:
Company memory, user thesis memory, memory events, action previews, and thesis
audit already overlap with this requirement.

Scope:
- existing company and thesis memory services
- memory event and action preview/execute boundaries
- V2 company and Research promotion components
- audit, preview, cancel, and confirmation tests

Non-goals:
Automatic promotion, direct overwrite, general memory redesign, or production
mutation during code validation.

Dependencies:
CXV2-005, CXV2-010, and CXV2-011.

Acceptance:
- Promotion identifies the exact conclusion, target, receipt, and evidence.
- Preview shows the proposed new revision and contradiction status.
- Explicit confirmation is required immediately before mutation.
- Cancel leaves canonical memory unchanged.
- Audit history records actor, source receipt, before/after revision, and time.

Focused validation:
Preview/cancel/confirm tests with isolated temporary storage and a browser
confirmation test.

Stop:
Stop before shared or production-data mutation; implementation proof uses
isolated test storage only.

### TICKET CXV2-013 — Separate assistant discovery from owner state

Goal:
Give the assistant its own bounded discovery watchlist and scratch research
store with explicit promotion boundaries.

Context:
The owner watchlist, watchlist scanner, research situation memory, and alerts
must not become an autonomous write path into owner state.

Scope:
- existing Cockpit research and watchlist services
- a distinct discovery namespace and bounded scratch-store service
- V2 Research discovery UI
- registry permissions and explicit promotion preview
- isolation, expiry, and budget tests

Non-goals:
Automatic owner-watchlist, portfolio, or company-memory mutation; unbounded
crawling; paid search; or scheduler activation.

Dependencies:
CXV2-002, CXV2-005, CXV2-011, and CXV2-012.

Acceptance:
- Assistant discovery and owner state use distinct schemas and namespaces.
- Scratch records have explicit TTL, capacity, query budget, and receipts.
- Read/search/select autonomy stays within configured budgets.
- Promotion to owner watchlist or company memory requires confirmation.
- Existing scanner paths receive explicit reuse, migration, or retirement
  decisions.

Focused validation:
Namespace isolation, capacity/expiry, budget, autonomous read-only, and
confirmation-boundary tests.

Stop:
Stop if any autonomous path can mutate owner holdings, watchlist, or canonical
company memory.

### TICKET CXV2-014 — Deliver the Portfolio workspace

Goal:
Present real owner positions, exposure, performance context, risks, and company
research links without invented valuations.

Context:
Holdings and home portfolio endpoints exist, but V2 needs provenance-aware
portfolio semantics and honest partial pricing.

Scope:
- `cockpit-ui/app/v2/portfolio/`
- `cockpit-ui/components/v2/portfolio/`
- existing holdings and portfolio backend services/routes
- existing chart primitives
- portfolio component and service tests

Non-goals:
Broker integration, trade execution, simulated valuation, tax reporting, or
multi-user portfolios.

Dependencies:
CXV2-008 and CXV2-010.

Acceptance:
- Positions show price source, as-of time, and unavailable states.
- Exposure/performance charts use only returned real observations.
- Risks and conclusions link to company evidence and receipts.
- Position mutations remain explicit confirmed owner actions.
- A partially priced portfolio never appears as a complete total.

Focused validation:
Complete, partial-price, stale, and empty portfolio cases plus browser chart
provenance checks.

Stop:
Stop if cost basis or market value would require inference from absent data.

### TICKET CXV2-015 — Deliver real Activity and persisted job history

Goal:
Show genuine research, ingestion, extraction, and action progress/history
without conflating configured jobs with executed jobs.

Context:
Operations, History, job tracker, ops store, action jobs, and SSE streams
overlap substantially.

Scope:
- `cockpit-ui/app/v2/activity/`
- `cockpit-ui/components/v2/activity/`
- existing job tracker, ops store, operations routes, and SSE projections
- Activity and reconnect tests

Non-goals:
Starting/stopping jobs, scheduler activation, synthetic progress, or deleting
legacy Operations/History pages.

Dependencies:
CXV2-005, CXV2-006, and CXV2-007.

Acceptance:
- Activity distinguishes queued, running, succeeded, failed, cancelled, and
  unknown.
- Progress is persisted evidence or labelled indeterminate.
- History survives reload and links to logs, artifacts, and receipts.
- Recovery actions show approval tier before invocation.
- Configured scheduling never appears as recent success without run evidence.

Focused validation:
Job-event projection tests, SSE reconnect, persistence reload, and stale/unknown
browser states.

Stop:
Stop if progress must be estimated without a persisted event or authoritative
stage.

### TICKET CXV2-016 — Deliver actionable System health

Goal:
Centralize freshness, tool health, failures, and recovery guidance while keeping
internal jargon out of normal workflows.

Context:
Health currently spans status bars, settings, operations, Intel Pulse, news,
chat readiness, and host/GPU dialogs.

Scope:
- `cockpit-ui/app/v2/system/`
- `cockpit-ui/components/v2/system/`
- a read-only backend health aggregation
- ingestion and tool-registry health projections
- existing status components where reusable

Non-goals:
Automatic recovery, service restart, model load, scheduler activation, active
external probes, or exposing secrets/host paths.

Dependencies:
CXV2-002, CXV2-006, CXV2-007, and CXV2-015.

Acceptance:
- System offers owner-facing summaries plus expandable diagnostics.
- Tool health shows last observation, latency, error class, and retryability.
- Freshness breaches identify affected owner capabilities.
- Recovery is read-only guidance or an approval-gated preview.
- Normal Today, Company, and Research views contain no raw degraded codes.
- Secret values and private host paths are redacted.

Focused validation:
Health aggregation, redaction, normal-UX code-absence, and System diagnostic
visibility tests.

Stop:
Stop before invoking recovery or probing paid, external, runtime, or
production-data resources.

### TICKET CXV2-017 — Add deterministic prompt-driven research acceptance

Goal:
Encode required research success and failure behavior as repeatable,
model-independent tests.

Context:
Existing agent tests are broad and browser tests are mostly mocked; neither
proves the release contract.

Scope:
- a focused Cockpit acceptance suite
- deterministic backend adapters and contract fixtures
- receipt, trace, freshness, and claim assertions
- a machine-readable acceptance manifest

Non-goals:
Live models, live web, production data, runtime success claims, or activation.

Dependencies:
CXV2-004, CXV2-005, CXV2-009, and CXV2-011.

Acceptance:
- Covers latest news, ASX announcements, evidence-backed thesis update,
  cross-company comparison, stale/empty fallback, unavailable sources,
  malformed tool output, budget exhaustion, and contradictory evidence.
- Exercises BHP, EIQ, CSL, and SHL where applicable.
- Fails on fabricated citations, silent tool bypass, wrong freshness, missing
  receipts, or fixture-marked runtime payloads.
- Assertions are semantic rather than exact-prose matches.
- Results are machine readable and runtime-state preserving.

Focused validation:
Run only the deterministic acceptance suite, lint changed files, and run
`git diff --check`.

Stop:
Move any test requiring a live model, live source, or production data to
CXV2-020; do not weaken the assertion.

### TICKET CXV2-018 — Add browser-visible and measurable performance gates

Goal:
Verify V2 behavior in a real browser and enforce the CXV2-001 UI and research
performance budgets.

Context:
Existing Playwright coverage can prove presentation but not live research.
Deterministic browser evidence and later live evidence must remain distinct.

Scope:
- `cockpit-ui/tests/v2/`
- Playwright configuration only where necessary
- V2 timing instrumentation and SSE timing metadata
- performance-result schema and validation documentation

Non-goals:
Live Tier 2 execution, production load tests, runtime deployment, or cutover.

Dependencies:
All of CXV2-008 through CXV2-017.

Acceptance:
- Browser tests verify traces, receipts, citations, freshness, failure UX,
  keyboard operation, and absence of simulated runtime data.
- Shell/read UI budgets are separate from research budgets.
- Research measures time to first trace, first accepted evidence, and terminal
  result.
- Reports include environment, sample count, and distributions.
- Deterministic evidence is never labelled as live runtime proof.

Focused validation:
Focused V2 Playwright, changed-file frontend lint/typecheck, and performance
report schema tests.

Stop:
Stop if a timing result cannot state environment, sample count, and measurement
boundaries.

### TICKET CXV2-019 — Prepare private-access activation and evaluation runbook

Goal:
Define exact approval-gated Tailscale/private-access, ingestion, provider,
service, store, model, evaluation, rollback, and cleanup steps without executing
them.

Context:
Private single-user access still needs safe binding, origin, secret, and API
behavior. Scheduler, DB, Qdrant, model, web, extraction, and backfill actions
cross Tier 2 boundaries.

Scope:
- a new Cockpit V2 activation/evaluation runbook
- existing startup/runtime documentation and configuration examples
- an immutable live-evidence manifest schema
- command risk classification tests where practical

Non-goals:
Tailscale changes, deployment, service activation, migrations, ingestion,
backfill, model loading, paid calls, merge, or cutover.

Dependencies:
CXV2-006, CXV2-017, and CXV2-018.

Acceptance:
- Each command is labelled read-only or Tier 2 and names its exact target.
- Tailscale binding, browser origin, API key/secret handling, and rollback are
  explicit without adding RBAC.
- Approval is granular by service, scheduler, store, model, provider, and
  backfill.
- Preconditions, timeout, expected evidence, rollback, and stop conditions are
  defined.
- Deterministic evidence cannot be confused with real-data evidence.
- No startup path silently performs activation.

Focused validation:
Static runbook review, documentation lint, command classification tests, and
`git diff --check`.

Stop:
Stop at the first Tier 2 command and request approval for that exact action.

### TICKET CXV2-020 — Approval gate: run real pilot tool and news acceptance

Goal:
After explicit approval, prove real tool use, news synthesis, and browser-visible
receipts for BHP, EIQ, CSL, and SHL.

Context:
This is the first ticket allowed to gather live runtime evidence. Code and
deterministic tests cannot satisfy it.

Scope:
- only the exact services, stores, providers, and evidence paths approved from
  CXV2-019
- immutable live result manifests and browser captures
- no required product-code changes

Non-goals:
Unapproved backfill, mutation beyond the grant, unbounded paid resources, merge,
deployment beyond the grant, or cutover.

Dependencies:
CXV2-019 and explicit Tier 2 approval.

Acceptance:
- The agreed prompt suite runs against real canonical local data and the
  approved web fallback.
- Receipts prove tool order, provenance, freshness, contradictions, and claim
  coverage.
- All four pilots have browser-visible traces and receipts or explicit failed
  evidence.
- Failure prompts prove useful recovery without fabricated citations or silent
  bypass.
- Performance evidence uses the approved budgets, environment, timestamps,
  sample counts, and distributions.
- Data gaps remain failures or limitations; fixtures cannot close them.

Focused validation:
Approved prompt suite, browser walkthrough, receipt audit, freshness sampling,
and immutable result manifest validation.

Stop:
Stop on missing approval, unexpected mutation, budget threshold, provenance
failure, stale source identity, or unsafe recovery request.

### TICKET CXV2-021 — Contract duplicate paths and issue a readiness verdict

Goal:
Adapt or retire obsolete Cockpit paths only after V2 equivalence is proven, then
produce a go/no-go readiness dossier.

Context:
`/full-chat`, `/news`, `/holdings`, `/memory`, `/history`, `/operations`,
`/settings`, legacy chat routes, and `tenn_chat` may overlap with V2 but cannot
be removed prematurely.

Scope:
- compatibility adapters and deprecation markers
- route/component caller audit
- focused regression tests
- a release-readiness dossier

Non-goals:
Redirecting `/`, deleting recoverable data, merge, production deployment,
service change, or authorizing cutover.

Dependencies:
CXV2-020.

Acceptance:
- Every overlapping path has a keep, migrate, adapter, or retire decision.
- Retired code has zero production callers and a rollback path.
- Legacy routes remain green until independently approved cutover.
- Dossier lists live results, failures, freshness, performance, security, and
  unresolved risks.
- Completion states readiness only and cannot authorize cutover.

Focused validation:
Mechanical caller search, compatibility tests, all focused V2 suites, lint, and
`git diff --check`.

Stop:
Stop if an old path still supplies unique required behavior or real pilot
evidence is incomplete.

### TICKET CXV2-022 — Approval gate: choose parallel operation or cutover

Goal:
Obtain a separate owner decision on continuing parallel operation, limited
opt-in, or making V2 the preferred/default Cockpit.

Context:
Passing code and acceptance tickets is necessary but never sufficient authority
for cutover. Redirecting `/`, changing launcher defaults, merging, deploying,
and restarting services are distinct actions.

Scope:
- a decision record
- only separately authorized routing or deployment configuration

Non-goals:
Automatic redirect, implicit merge/deploy/restart, data migration, or
destructive cleanup.

Dependencies:
CXV2-021 and explicit cutover approval.

Acceptance:
- Owner reviews the readiness dossier and unresolved limitations.
- Decision explicitly selects continue-parallel, limited opt-in, or cutover.
- Observation window and rollback triggers are approved.
- Merge, deploy, routing, runtime, and cleanup actions each receive exact
  authority before execution.

Focused validation:
Decision-record completeness. Operational validation belongs to the separately
authorized action.

Stop:
Always stop before redirect, merge, deployment, service alteration, data
mutation, or destructive cleanup unless that exact action is approved.

## Dependency map

```text
CXV2-001
├── CXV2-002 ── CXV2-003 ── CXV2-004 ── CXV2-005
│   └── CXV2-006
└── CXV2-007 ── CXV2-008 ── CXV2-014

CXV2-001 + CXV2-004 + CXV2-005 ── CXV2-009
CXV2-007 + CXV2-009 ── CXV2-010
CXV2-005 + CXV2-007 ── CXV2-011
CXV2-005 + CXV2-010 + CXV2-011 ── CXV2-012
CXV2-002 + CXV2-005 + CXV2-011 + CXV2-012 ── CXV2-013
CXV2-008 + CXV2-010 ── CXV2-014

CXV2-005 + CXV2-006 + CXV2-007 ── CXV2-015 ── CXV2-016
CXV2-004 + CXV2-005 + CXV2-009 + CXV2-011 ── CXV2-017
CXV2-008..017 ── CXV2-018
CXV2-006 + CXV2-017 + CXV2-018 ── CXV2-019
CXV2-019 + explicit Tier 2 approval ── CXV2-020
CXV2-020 ── CXV2-021
CXV2-021 + explicit cutover approval ── CXV2-022
```

Initial parallel frontier after CXV2-001:

- CXV2-002 tool safety registry
- CXV2-007 V2 shell
- CXV2-006 after the registry clears
- Today and contract preparation after the shell clears

## Programme stop conditions

- Do not claim remote verification for the local-only source branch.
- Do not absorb or delete the user's `.playwright-cli/` files.
- Do not use code, deterministic fixtures, configuration, or CI as proof of
  live ingestion, live tool use, real-data coverage, activation, or cutover.
- Do not repair missing pilot data by simulation, ticker-specific defaults, or
  silent backfill.
- Do not create a second chat, news, memory, job, or operations authority
  without first proving the existing authority cannot be extended.
- Stop at the first action outside the active ticket or the first Tier 2
  boundary without exact approval.
