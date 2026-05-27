# Recommended Next Queue

## Top 10

| Rank | Issue | Bucket | Reason |
| --- | --- | --- | --- |
| 1 | #106 [Repo Hygiene] Normalize raw Jam-captured GitHub issues into Tenn issue contract | run now | M0/control-plane unblocker: normalizes raw #40/#41/#53/#55/#61 so future agents can safely act or close duplicates. |
| 2 | #115 [Repo Hygiene] Add report-only Codex nightly lock-up audit | review now | Branch/worktree loss-risk control: first local lock-up report exists; decide closeout or runner follow-up before branch evidence drifts. |
| 3 | #112 [Runtime] Add final-status observability for nightly news scheduling | review/publish now | Local final-status observability fix exists on current branch ahead of origin; issue remains open and should not be lost. |
| 4 | #114 [Runtime] Nightly news fetch fails because canonical ASX ticker universe is missing | review/publish now | Local ticker-universe repair exists on current branch ahead of origin; issue remains open and should not be lost. |
| 5 | #105 [CI] Split PR #39 lint-and-test failure clusters after closed CI audit | run now | Unblocks PR #39, the largest current draft/unstable PR and the current branch PR head. |
| 6 | #104 [Evaluation] Cross-route evidence-envelope regression matrix for chat, news, Home, and source drawer | run now | High-risk evidence-envelope regression matrix across chat/news/Home/source drawer; foundational for trust and UI claims. |
| 7 | #107 [Query Orchestration] Chat cannot use visible Holdings and Watchlist context for analyst workflows | run now | Blocks #119 and directly affects analyst chat usefulness using visible Holdings/Watchlist context. |
| 8 | #95 [Reporting] Audit Cockpit source drawer semantics for context-only and degraded evidence | run now | Trust/provenance source-drawer semantics; ready and bounded audit with clear acceptance path. |
| 9 | #100 [Memory] Audit YouTube transcription to strategy-memory integration | run now | Parent audit for YouTube transcription to strategy-memory integration; unblocks #101/#102/#103. |
| 10 | #113 [Runtime] Resolve remaining llama-server :8001 owner evidence gap | run now | Runtime owner/provenance follow-up from #82; bounded read-only evidence gap with M6 value. |

## Run After Blocker

| Issue | Run After | Reason |
| --- | --- | --- |
| #119 [Query Orchestration] Chat treats audit/context prefix as ticker and proposes news ingest | after #107 | Audit token/ticker misclassification depends on visible-context routing root cause. |
| #120 [Query Orchestration] Pending action proposal can block the next normal chat prompt | after #119 | Pending action-state bug should follow the ticker/action proposal routing audit. |
| #101 [Provenance] Persist YouTube source metadata and transcript timing through commentary chunks | after #100 | Source metadata persistence should follow the transcription-to-memory parent audit. |
| #102 [Evaluation] Add YouTube intake quality gates for low-signal and speculative transcripts | after #100 | Intake quality gates should follow the transcription-to-memory parent audit. |
| #103 [Reporting] Add Home memory-candidate queue for commentary takeaways | after #100 | Home memory-candidate queue depends on the memory/commentary intake audit. |
| #98 [Financial Truth] Align persisted metric schema with extractor contract | after active Financial Truth job clears | Adjacent extraction contract parity work is currently claimed in registry. |
| #97 [Evaluation] Generate extracted-payload scorecard for confirmed metric coverage | after DATA_MISSING resolved | Needs real actual payloads/source-PDF reviewability evidence before scorecard claims. |
| #96 [Query Orchestration] Most PDF-path documents lack terminal extraction | after DATA_MISSING resolved | Terminal extraction coverage needs current corpus evidence before remediation. |
| #99 [Provenance] Make real-gold source PDFs reviewable without committing raw filings | after source-PDF policy evidence | Needs review of real-gold source PDFs without committing raw filings. |

## Audit First

| Issue | Classification | Reason |
| --- | --- | --- |
| #72 [Financial Truth] Appendix 4C candidate sidecar parser v1 | HIGH_RISK_NEEDS_AUDIT_FIRST | P0 Financial Truth parser-adjacent issue lacks state/type/milestone; run only with fresh task card and registry proof. |
| #55 Cockpit backend restart route has no local auth or CSRF guard while frontend is LAN-bound | HIGH_RISK_NEEDS_AUDIT_FIRST | Security-sensitive restart route issue has no labels/milestone; audit first before any remediation. |
| #83 [Query] News projection materialization/parity repair planning v1 | READY_TO_RUN | Open issue has state:ready and no obvious blocker. |
| #88 [Memory] System fitness and improvement audit v1 | READY_TO_RUN | Open issue has state:ready and no obvious blocker. |
| #108 [Reporting] Hide auto-diagnostic Codex repair controls from normal chat users | READY_TO_RUN | Open issue has state:ready and no obvious blocker. |
| #91 History screen turns documents without job timestamps into Just now 0ms completed jobs | READY_TO_RUN | Open issue has state:ready and no obvious blocker. |
| #90 GPU Activity reports no GPU processes while llama-server is healthy | READY_TO_RUN | Issue body has a conditional active-task blocker; current registry shows only a Financial Truth job, so revalidate before claiming. |

## Defer

| Issue | Classification | Reason |
| --- | --- | --- |
| #117 [Reporting] Investigate Marketplace home-location setup gap in mission flow | READY_TO_RUN | Lower unblocker value or M5 overloaded; keep visible but do after control-plane/query blockers. |
| #118 [Reporting] Audit Thesis Audit first-run guidance and source selection workflow | READY_TO_RUN | Lower unblocker value or M5 overloaded; keep visible but do after control-plane/query blockers. |
| #116 [Reporting] Audit News empty-state value and proactive context handoff | READY_TO_RUN | Lower unblocker value or M5 overloaded; keep visible but do after control-plane/query blockers. |
| #93 Marketplace Matches and Alerts empty states do not explain mission state or next action | READY_TO_RUN | Lower unblocker value or M5 overloaded; keep visible but do after control-plane/query blockers. |
| #92 Watchlist empty state does not turn existing portfolio or chat context into useful next actions | READY_TO_RUN | Lower unblocker value or M5 overloaded; keep visible but do after control-plane/query blockers. |
| #49 News lookback filter is visible but ignored by the production search request | NEEDS_FOLLOWUP | Lower unblocker value or M5 overloaded; keep visible but do after control-plane/query blockers. |
| #47 Verification page emits controlled/uncontrolled Select warning in production UI | NEEDS_FOLLOWUP | Lower unblocker value or M5 overloaded; keep visible but do after control-plane/query blockers. |
| #46 Cockpit production UI does not automatically switch to a mobile-safe layout on narrow viewports | NEEDS_FOLLOWUP | Lower unblocker value or M5 overloaded; keep visible but do after control-plane/query blockers. |
| #45 Disable Vercel Analytics script in local Cockpit runtime to avoid 404 console noise | NEEDS_FOLLOWUP | Lower unblocker value or M5 overloaded; keep visible but do after control-plane/query blockers. |
| #42 Cockpit landing page buries core Home panels below Strategy Lab audit cards | NEEDS_FOLLOWUP | Lower unblocker value or M5 overloaded; keep visible but do after control-plane/query blockers. |

## Close / Supersede Candidates

Do not close anything from this audit. These are candidates for a later approved closeout/normalization task.

| Issue | Reason |
| --- | --- |
| #40 failure to request a search | duplicate/data-missing candidate via #106 normalization |
| #41 missing data | duplicate/data-missing candidate via #106 normalization |
| #112 [Runtime] Add final-status observability for nightly news scheduling | closeout candidate only after local ahead commits are published/reviewed |
| #114 [Runtime] Nightly news fetch fails because canonical ASX ticker universe is missing | closeout candidate only after local ahead commits are published/reviewed |
| #115 [Repo Hygiene] Add report-only Codex nightly lock-up audit | close or supersede with runner-integration follow-up after operator decision |
