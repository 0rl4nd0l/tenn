# Next Child Task Recommendation

Recommended next child task: C02 from PR #39 / issue #105 CI cluster split.

## Candidate Scope

- Lane: Evaluation with Query Orchestration support.
- Mode: audit-first safe extension.
- Target: Cockpit chat/session `llm_client` contract drift.
- Evidence source: PR #39 `lint-and-test` run `26439822448`.

## Hard Stops

- Do not combine C02 with C03-C13.
- Do not mutate DB, Qdrant, news, memory, parser routing, prompts, gold labels,
  runtime/model/GPU config, or Cockpit UI unless a new task card explicitly
  allows it.
- Do not push PR #39 or close #105 without separate operator approval.

## Rationale

C01 is now locally reconciled and preserve-ready. PR #39 remains red because
other clusters are still unresolved or unproven. The next highest-signal cluster
visible in the existing CI failure set is the repeated `llm_client` unexpected
keyword argument failure across Cockpit service/session tests.
