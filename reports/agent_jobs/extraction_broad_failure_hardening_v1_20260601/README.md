# Extraction Broad Failure Hardening V1

## Summary

Implemented the first code follow-up from the broad-failure source classification report.

Changes:

- Source classification now blocks AGM/result/poll notices and narrow unaudited financial updates without formal statements before backend metric extraction.
- The broad robustness helper now filters title-classified non-candidates before random sampling and records candidate-filter counts in run metadata.
- Appendix 4D/4E summary rows with explicit full-dollar values now resolve to `scale=units` when no scaled unit header is present.
- Invalid EBIT evidence from generic pre-tax rows is abstained/null, not substituted. The existing validation gate still fails unclean payloads that were not abstained.

No runtime extraction, canary run, broad backfill, backend/worker/router startup, datastore write, source-PDF mutation, prompt/schema/gold-label change, Cockpit UI change, or GitHub mutation was performed.

## Current Probe Evidence

Exact five-failure filename filter probe:

- Retained candidates: GTE, CAF.
- Excluded: ARL `meeting_results_notice`, HNG `unaudited_financial_update_without_formal_statements`, TLS `meeting_results_notice`.

No-runtime `/data/asx/docs` inventory probe:

- Input financial-performance PDFs: 28,633.
- Candidate PDFs after title filter: 26,462.
- Excluded PDFs: 2,171.
- Reason counts: `advisory_only_document=50`, `meeting_results_notice=2116`, `unaudited_financial_update_without_formal_statements=5`.

## Validation

Passed:

- Task-card validate, active-job list, overlap check, and claim.
- Focused multipass/broad helper pytest: `6 passed, 187 deselected`.
- Full touched test files: `193 passed`.
- Adjacent advisory pre-canary pytest: `2 passed, 14 deselected`.
- Adjacent terminal candidate manifest pytest: `5 passed, 27 deselected`.
- Ruff on touched Python files.
- `py_compile` on touched Python files.
- Exact five-failure no-runtime filename probe.
- `/data/asx/docs` no-runtime inventory probe.
- `git diff --check`.
- Code-review artifact: no critical, warning, or suggestion findings.

## Architecture Review

The `.cursor/rules/` files referenced by the local `architecture-check` skill are absent in this checkout. The enforced `SYSTEM_CONTRACT.md` and AGENTS/CLAUDE rules were used instead.

Verdict: compliant. The change stays inside backend extraction/evaluation helper behavior, keeps backend as source of truth, does not create a fallback or parallel truth source, does not infer or substitute metric values, and keeps source PDFs/data stores immutable.

## Remaining Work

This is still not full ticker-universe extraction graduation.

Next safe step:

- Run a new bounded broad robustness sample against `/data/asx/docs` after fresh runtime/GPU/router gates, then compare status distribution against the prior 8-document sample.
- If the sample improves but still exposes failures, classify the new failures before widening to a larger count.
