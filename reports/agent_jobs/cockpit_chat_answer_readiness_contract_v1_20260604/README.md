# Cockpit Chat Answer Readiness Contract v1

Date: 2026-06-04
Lane: Query Orchestration
Mode: SAFE EXTENSION

## Outcome

Implemented capability-scoped chat readiness for Cockpit and gated `/full-chat`
normal financial analysis presentation when evidence/runtime capabilities are not
ready.

## Key Evidence

- `/api/cockpit/chat/readiness` returns `answer_ready=false` and
  `normal_analysis_allowed=false` for BHP/CSL/MIN/A2M/ZZZZZZ in the isolated
  profile, with explicit blockers for financial rows, filings, and local
  news/RAG.
- BHP stateless revenue prompt no longer emits the unverified revenue body after
  `DATA_MISSING`; it returns `unverified_numeric_claims_suppressed` and
  `sufficient_for_analysis=false`.
- `/full-chat` desktop and mobile render a first-viewport readiness blocker
  band with no console/page/request failures.

## Verification

- Backend: 12 focused/adjacent tests passed.
- Frontend: 5 focused Vitest tests passed.
- Lint: touched-file lint passed; one unrelated existing warning in
  `components/cockpit/marketplace/mission-screen.tsx`.
- Build: `next build` compiled, then failed on an unrelated existing TypeScript
  error in `lib/cockpit-chat-presentation.ts` outside this task-card allowlist.
