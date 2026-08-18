# Review Board

Decision: `proceed`

## Architect

- Evidence: base-to-head diff, routing architecture, task cards, live bind
  mounts, and runtime proof.
- Finding: the change separates non-metric interactive/tool traffic from the
  deterministic metric-extraction route without altering extraction prompts,
  schemas, or model selection.
- Uncertainty: the UI process is absent, but it is outside the API-routing
  architecture and predates activation.
- Risk: live runtime currently depends on the local task worktree until merge.
- Action: publish and merge the coherent three-commit branch.

## Skeptic / Red Team

- Evidence: shared-token proof, llama journal, DB/news deltas, container IDs,
  and forbidden-service baselines.
- Finding: the proof used the real routing-state token but did not start an
  actual extraction. This is strong route-class evidence, not a full extraction
  run.
- Uncertainty: API availability and cost remain external dependencies.
- Risk: merge could be misreported as full Cockpit UI recovery.
- Action: proceed only with the scope limitation stated explicitly.

## Product / Value

- Evidence: normal and GPU-exclusive chat responses and non-metric tool route.
- Finding: Cockpit can remain responsive while extraction protects the local
  GPU, with truthful provider/model/reason metadata.
- Uncertainty: UI availability prevents end-user browser confirmation.
- Risk: Anthropic outage during extraction intentionally fails fast.
- Action: merge the route fix; diagnose UI separately.

## Validation / Test

- Evidence: 14 launcher tests, 53 focused routing/provenance tests, Ruff,
  contract/diff checks, code review, HTTP 200 proofs, zero persistence delta,
  empty queues, and cleared token.
- Finding: code and live intended-output proof pass.
- Uncertainty: no real extraction was started by design.
- Risk: the duplicate Celery nodename warning reduces inspector clarity but
  both replies were empty and it does not invalidate routing proof.
- Action: proceed; retain the warning as a non-blocking follow-up.

## Repo Hygiene / Git Guard

- Evidence: full portable guard, live and committed ledgers, registry,
  canonical remote head, branch history, status, and GitHub PR search.
- Finding: guard passes, worktree is clean, canonical base is unchanged, and no
  existing PR or duplicate active Cockpit lane exists.
- Uncertainty: task card originally prohibited GitHub writes; the current
  explicit owner approval supersedes that owner boundary for push/PR/merge.
- Risk: stop on canonical drift, conflicts, or required-check failure.
- Action: push this branch and open one PR to
  `migration/clean-runtime-baseline-reconstruct-v1`.

## Domain

- Evidence: routing metadata and tests for `multipass_extraction` versus
  `news_memo_extractor`.
- Finding: metric extraction remains on the deterministic local route;
  non-metric work moves to Anthropic during GPU-exclusive activity.
- Uncertainty: production extraction throughput was not measured.
- Risk: none for financial-number provenance because no extraction outputs,
  prompts, gold labels, or source data changed.
- Action: proceed.

## Chair

The root problem is shared-router contention, and the branch fixes the route
class rather than one request. This is not a report-only loop: code, runtime,
and live intended-output evidence all advanced. The minority concern about the
synthetic activity token and absent UI is credible but non-blocking when the
merge claim remains limited to API routing. Proceed with push, PR, required
checks, and merge under the owner's explicit approval.
