# Source Label Fixture Expansion Audit

Job: `source_label_fixture_expansion_v1_20260524`
GitHub issue: #56
Lane: Provenance
Execution mode: AUDIT ONLY
Branch: `audit/repo-hygiene-safe-audits-v1-20260525`
Base evidence commit: `b12e906676e3066a32ab1451018fa818f3b8a725`

## Decision

The issue-exact audit acceptance is met as a coverage/gap report. No fixtures,
tests, source-label semantics, product code, or runtime/data surfaces were
changed in this pass.

Fixture implementation is intentionally deferred: source-label semantics are a
hard-boundary surface, and current worktree inventory shows active source-label
and Cockpit provenance branches. This pass therefore proves current coverage,
separates positive and negative gaps, and recommends a bounded child fixture
task rather than editing sensitive test surfaces from the closeout branch.

## Confirmed Coverage

- Backend evidence guard positives and negatives exist in
  `financial-engine_v2/backend/tests/test_chat_evidence_guard.py`:
  price data satisfies price-trend evidence, filing-only context does not verify
  price trends, missing financial rows become `metric_extraction_missing`,
  `financial_truth` plus `claim_verified` satisfies financial metric
  requirements, recent-news claims need claim-verified event/news evidence, and
  raw support flags do not self-promote to recent-news events.
- Backend UI-source construction coverage exists in
  `financial-engine_v2/backend/tests/test_build_ui_sources.py` for local
  context, price query sources, financial-truth document/row sources, memory
  sources, news hits, and no-hit source items.
- Chat UI actionability coverage exists in
  `cockpit-ui/lib/cockpit-chat-actionability.test.ts`: market-data gaps,
  metric-extraction gaps, degraded runtime, no-hit sources, snippet-only
  context, non-verified context taxonomy, and claim-verified metadata mapping.
- Home contract coverage exists in `cockpit-ui/lib/cockpit-home-contract.test.ts`
  for trust-level mapping, `unknown_unclassified` fallback,
  DATA_MISSING-without-reason detection, and preventing context/no-hit/missing
  or degraded labels from upgrading to verified trust.
- Historical source-label report evidence exists in
  `reports/source_label_semantics_20260506_144411/05_test_matrix.md`, which
  lists A2M local-news support/no-hit, memory context, external web context,
  unknown source type, and UI trust-label coverage.

## Positive / Negative Separation

Positive covered cases:

- Claim-verified financial truth source satisfies financial metric requirements.
- Claim-verified recent-news event satisfies recent-update requirements.
- Price source identifiers satisfy market-price / technical trend requirements.
- Home trust labels display `claim_verified` distinctly from weaker labels.

Negative covered cases:

- Filing-only context does not verify a market-price trend claim.
- Missing canonical financial rows mark metric extraction as missing.
- Price data alone does not satisfy recent-news event evidence.
- Context news or filings without claim verification remain insufficient.
- Raw support flags do not self-promote to recent-news event evidence.
- No-hit, degraded, missing, context-only, unknown, snippet-only, memory, and
  external web context stay non-verified in UI actionability surfaces.

## Gaps

See `gap_register.json` and `fixture_coverage_map.json` for machine-readable
rows. Main gaps:

- Coverage is spread across backend and frontend tests; there is no single
  issue-exact source-label fixture matrix.
- Live-source, historical-source, weak-source, and DATA_MISSING categories are
  not represented as a unified cross-surface fixture taxonomy.
- Existing tests cover many semantics but do not prove all labels across API,
  SSE, reload persistence, Home handoff, source drawer, and chat actionability
  in one stable fixture bundle.
- Exact fixture edits are deferred because source-label semantics are
  hard-boundary and active source-label/provenance branches exist.

## Recommended Child Implementation

Open a dedicated safe-extension issue for `source_label_fixture_matrix_v1`.
Allowed files should be explicit test/fixture files only, with no source-label
semantic changes. The child should add a table-driven fixture matrix that covers
positive and negative cases across backend evidence guard, source construction,
chat actionability, and Home trust labels.

## Validation

- Task-card validate: passed.
- Registry list-active before claim: passed with `active_jobs: []`.
- Registry check-overlap: passed.
- Registry claim/release: passed.
- JSON validation for `status.json`, `validation.json`,
  `fixture_coverage_map.json`, `gap_register.json`, and `diff-check.json`:
  passed.
- `git diff --check` and `git diff --cached --check`: passed.
- Task-card `check-diff`: passed.
- Targeted test commands attempted but environment tooling was unavailable:
  bare `pytest` was not on PATH and `pnpm` was not on PATH. No source files were
  changed, so artifact validation is the closeout gate for this audit-only pass.

## DATA_MISSING

- Current targeted test execution is DATA_MISSING due missing local `pytest` and
  `pnpm` commands in this shell.
- No new fixture implementation was attempted.
- No live runtime/source-label UI route was sampled during this report-only
  pass.

## Hard-boundary Compliance

No source-label semantics, canonical truth, financial metrics, production data,
DB/Qdrant/news/memory stores, parser/extraction routing, prompts, gold labels,
runtime/model/service config, backend/frontend product code, or unrelated dirty
files were changed.
