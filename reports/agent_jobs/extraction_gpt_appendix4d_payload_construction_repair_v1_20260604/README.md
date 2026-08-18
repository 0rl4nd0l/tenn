# GPT Appendix 4D Payload Construction Repair

Generated: 2026-06-04T12:02:27.263000+00:00

## Outcome

Narrow safe extension implemented and tested. The exact GPT Appendix 4D target now produces the expected source-bound payload in the targeted report-local full-multipass-equivalent verification.

No random sample, count-16/count-24 sample, broad extraction, backfill, production DB write, Qdrant/news/memory mutation, source PDF edit, prompt/gold-label change, runtime/model/GPU config change, service restart, or schema migration was run.


## Prior Artifacts Read

- `extraction_gpt_appendix4d_targeted_verification_after_pr294_v1_20260604`: direct gate proof passed for the exact PDF with `revenue=150804000`, `np_attributable=15463000`, source-bound `H/2024-06-30`, and wrapper disclosures.
- `extraction_gpt_appendix4d_end_to_end_after_pr294_v1_20260604`: full multipass failed with `period_type=Q`, `period_end=null`, `revenue=null`, `np_attributable=15462000`, wrapper fields absent, and `validation_gate:missing_period_end`.
- `extraction_appendix4d_wrapper_gate_current_origin_v1_20260604`: PR #294 wrapper gate simulation passed only when required source-bound context and disclosure evidence were present.

## Root Cause

The PR #294 validation gate was correct, but the full multipass payload was not carrying the source-bound Appendix 4D evidence into validation.

1. The annual period-end regex also matched the `year ended` substring inside `half year ended`, so source period-end evidence became ambiguous and `period_end` stayed null.
2. The wrapper source evidence was not propagated into `source_bound`; the payload assembled `source_bound` from pass4 payload values, preserving `Q/null` when pass4 or pass1 was wrong.
3. There was no deterministic Appendix 4D/4E wrapper-summary metric construction step, so pass4 could keep the attached/member row `15,462` and miss the Appendix 4D summary revenue row `150,804`.
4. Wrapper disclosure evidence existed in the source document but was never assembled into the validation payload.

The evidence loss happened in source period detection and validation payload assembly, with pass4 preserving the wrong/missing metric values. The source classifier and parser saw Appendix 4D evidence; the issue was propagation and wrapper-summary construction.

## Fix Made

- Made the annual source period-end detector stop matching inside `half year ended`.
- Added a narrow Appendix 4D/4E source-bound wrapper payload builder for early source sections/tables.
- For structurally identified wrappers, source period evidence can correct pass1 `report_type`/`period_end` before metric extraction.
- The wrapper builder carries source-bound `period_type`, `period_end`, `scale`, `currency`, wrapper subtype, disclosure evidence, and the two required canonical metrics.
- It prefers Appendix wrapper summary rows for `revenue` and `np_attributable`; NTA, dividends, record date, and associates/JV remain disclosure-only.
- The deterministic confidence lift is only applied when both required canonical metrics came from wrapper source rows.

## Before / After Payload

Before, from prior end-to-end verification:

```json
{
  "currency": "AUD",
  "final_status": "failed",
  "gate_error": "validation_gate:missing_period_end",
  "metrics": {
    "np_attributable": 15462000,
    "revenue": null
  },
  "period_end": null,
  "period_type": "Q",
  "scale": "thousands",
  "source": "prior end-to-end verification supplied in task context",
  "source_bound": null,
  "wrapper_disclosures": null
}
```

After targeted verification:

```json
{
  "currency": "AUD",
  "final_status": "ok",
  "gate_error": null,
  "metrics": {
    "ebit": null,
    "np_attributable": 15463000.0,
    "revenue": 150804000.0
  },
  "period_end": "2024-06-30",
  "period_type": "H",
  "provenance": {
    "np_attributable": "appendix_wrapper:page_2:Net profit after income tax expense from ordinary activities",
    "revenue": "appendix_wrapper:page_2:Total revenues and other income"
  },
  "row_refs": {
    "np_attributable": "Net profit after income tax expense from ordinary activities",
    "revenue": "Total revenues and other income"
  },
  "scale": "thousands",
  "source_bound": {
    "currency": "AUD",
    "document_subtype": "appendix4d",
    "document_title": "Appendix 4D - GPT Management Holdings Limited",
    "period_end": "2024-06-30",
    "period_type": "H",
    "scale": "thousands"
  },
  "source_document_classification": {
    "canary_candidate_allowed": true,
    "definition": "Source metadata has explicit annual, half-year, quarterly, or appendix financial-report evidence and may proceed through normal extraction gates.",
    "document_class": "financial_report",
    "evidence": [
      "appendix_4d_source_phrase"
    ],
    "extraction_candidate_allowed": true,
    "reason": "appendix_4d_source_phrase"
  },
  "source_period_end_evidence": {
    "hits": [
      {
        "evidence": "For the half year ended 30 June 2024",
        "period_end": "2024-06-30",
        "period_type": "H",
        "reason": "half_year_ended_explicit_date"
      },
      {
        "evidence": "for the half year ended 30 June 2024",
        "period_end": "2024-06-30",
        "period_type": "H",
        "reason": "half_year_ended_explicit_date"
      },
      {
        "evidence": "for the half year ended 30 June 2024",
        "period_end": "2024-06-30",
        "period_type": "H",
        "reason": "half_year_ended_explicit_date"
      }
    ],
    "period_end": "2024-06-30",
    "period_type": "H",
    "reason": "half_year_ended_explicit_date"
  },
  "wrapper_disclosures": [
    "Net tangible assets per security",
    "Dividends / distributions",
    "Record date for determining entitlement",
    "Details of associates and joint ventures entities"
  ]
}
```

## Targeted GPT Result

- Final status: `ok`
- Gate error: `None`
- `period_type`: `H`
- `period_end`: `2024-06-30`
- `scale`: `thousands`
- `currency`: `AUD`
- `revenue`: `150804000.0`
- `np_attributable`: `15463000.0`
- Wrapper disclosure evidence: Net tangible assets per security, Dividends / distributions, Record date for determining entitlement, Details of associates and joint ventures entities

Verification mode: `report_local_full_multipass_equivalent_exact_pdf_real_parser_mocked_llm_outputs`. This used the exact PDF and real parser output, with mocked prior-bad LLM outputs because no clean live LLM runtime was configured in the isolated worktree.

## Count-16 Rerun

A count-16 bounded rerun was not run. The targeted GPT gate is now green in the report-local equivalent path, so a bounded rerun is conditionally justifiable only after operator approval, live runtime readiness, and any separate broad-harness contract blockers are confirmed clean.

## Remaining DATA_MISSING

- Live LLM-backed exact-PDF full multipass verification was not run in this isolated worktree.
- No count-16/count-24 bounded rerun was run.
- No production persistence was exercised.

## Validation

- Task card validate: passed.
- Registry overlap and claim: passed.
- Focused pytest: passed, 11 tests.
- py_compile touched Python files: passed.
- Ruff touched Python files: passed.
- Targeted exact GPT verification: passed, final status ok.
- JSON validation for report artifacts: passed.
- git diff --check: passed.
- check-diff: passed.
