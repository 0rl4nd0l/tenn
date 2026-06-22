# Decisions

## Decision

Proceed no further than a report-only classification in this run.

JAY `04438122-c607-4c53-bb41-2e3864c06479` is source-bound and extractable enough to justify the next evidence lane, but not enough to justify direct product-code mutation from this task card.

## Rationale

- The PDF is present and readable.
- The saved count-24 run had only title-based source classification and produced `validation_gate:insufficient_metrics:0`.
- The source PDF and docling cache both show a Q3 FY23 trips/revenue table with a `Net Revenue` row.
- The extraction prompt explicitly treats `Net revenue` as a valid revenue label.
- For quarterly payloads, one non-null canonical metric is sufficient to pass the minimum metric count gate after other gates pass.
- One adjacent same-family JAY market-update candidate exists and has the same table pattern, so this is not purely a one-document anomaly.
- The current task card does not allow parser/classifier/prompt/product-code writes, no-write fixture expansion, or GitHub mutation.

## Outcome

- classification: `extractable_market_update_family_source_bound`
- confidence: `medium`
- product_change_recommended_now: `false`
- stop_state: `NO_PRODUCT_FIX_PROVEN_IN_THIS_TASK`
- next_action: create a narrow no-write replay/fixture packet for the JAY market-update family and only then decide whether a product lane is justified.

## Boundaries Preserved

- No broad extraction.
- No count sample, backfill, or full-universe extraction.
- No DB, Qdrant, Redis, news, runtime, source-PDF, gold-label, prompt, dependency-file, parser, classifier, multipass, ontology, or product-code writes.
- No GitHub mutation.
- No merge, rebase, cherry-pick, reset, stash, clean, branch deletion, or worktree deletion.

## Owner Boundary

Owner approval is still needed before pushing/opening a PR for the accumulated local report/control-plane commits, and before any product-code implementation lane for JAY.
