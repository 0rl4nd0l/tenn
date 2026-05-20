# Comparator Artifact Plan

Job: `asx_deterministic_extraction_extension_audit_v1_20260519`

Comparator artifacts are read-only. They must never write canonical truth, alter gold labels, control parser routing, or run through shared runtime surfaces such as `:8001` strict extraction/eval comparator work.

## Common Artifact Shape

Each backend/parser comparator should normalize to:

```json
{
  "artifact_type": "parser_comparator_artifact",
  "canonical_write": false,
  "document_id": "string",
  "source_pdf": "string",
  "source_sha256": "string",
  "parser_backend": "string",
  "parser_version": "string_or_DATA_MISSING",
  "generated_by": "report_or_comparator_lane",
  "pages": [],
  "tables": [
    {
      "table_id": "string",
      "page": 1,
      "bbox": null,
      "caption": "string",
      "headers": [],
      "rows": [],
      "cells": []
    }
  ],
  "normalized_metric_candidates": [],
  "warnings": [],
  "abstain_reasons": []
}
```

## MinerU

Current state: no MinerU implementation or direct reference was found in the inspected surfaces.

Plan:
- Treat as an external parser candidate only.
- Emit table/cell geometry and text to the common artifact shape.
- Compare against Docling evidence binding and fixture labels.

Hard stop:
- No MinerU output can become canonical truth.

## Chandra

Current state: no Chandra implementation or direct reference was found in the inspected surfaces.

Plan:
- Treat as an external parser candidate only.
- Require parser version, source checksum, table geometry, and deterministic row ordering before comparison.

Hard stop:
- No cloud/remote parser output can be used as production truth.

## Marker

Current state: no relevant Marker parser implementation was found; `marker` hits in the inspected tree were unrelated news vector marker files.

Plan:
- If later tested, normalize Markdown/table output into the common artifact shape.
- Preserve source page/table binding; generic Markdown alone is insufficient evidence.

Hard stop:
- Generic Markdown is never canonical truth.

## TATR / Table Transformer

Current state: no TATR/Table Transformer implementation or direct reference was found in the inspected surfaces.

Plan:
- Treat as table-detection comparator only.
- Require page/bbox/table id evidence and row/cell reconstruction diagnostics.

Hard stop:
- Detection without row/column value binding cannot score metric truth.

## pdfplumber / Camelot / pypdfium2

Current state:
- `pdfplumber` was not found.
- `pypdfium2` appears only in an eval fixture note as a known garbled-output limitation.
- Camelot exists as script-only cashflow fallback and is explicitly forbidden as a backend dependency by tests.

Plan:
- Keep Camelot isolated to script/report lanes.
- Use pdfplumber/pypdfium2 only as comparator adapters if a later task adds them under explicit allowed files.
- Normalize every output to table/page/row/column evidence.

Hard stop:
- Do not add heavy parser dependencies to backend requirements.
- Do not use fallback output outside cashflow-scoped evidence.

## Comparator Evaluation Rules

- Comparator artifacts can support DATA_MISSING analysis and fixture design.
- Comparator artifacts can identify Docling failure modes.
- Comparator artifacts can suggest deterministic parser tests.
- Comparator artifacts cannot change extraction prompts, parser routing, gold labels, runtime config, DB rows, Qdrant, memory, Cockpit, or source labels.
