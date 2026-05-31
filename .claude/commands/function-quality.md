# Function Quality

Deep-reasoning feature analyst. Systematically analyzes code, docs, and tests for a named feature; outputs findings in `/code-fix`-compatible format.

## Usage

Provide a **feature name** (e.g. "pdf ingestion", "metric extraction", "news pipeline", "ticker sync") and an optional **scope_hint** (e.g. "backend only", "scripts/news_pipeline").

## Instructions

Run two phases in order:

### Phase 1 — EXTRACT (read-only)
- Locate all code, tests, config, and docs that implement or describe the feature.
- Identify: entry points (CLI, API, Celery tasks); data flow (inputs, outputs, storage); dependencies; tests and their coverage.
- Record in work_log: assumptions, sources_used, files_read. Do not modify any file.

### Phase 2 — ANALYZE
Check for:
- **Correctness**: Logic errors, wrong assumptions, misuse of APIs, incorrect types or units.
- **Gaps**: Missing error handling, validation, tests, undocumented behavior, missing edge cases.
- **Inaccuracies**: Docs/code mismatches, misleading names or comments, outdated config.
- **Inefficiencies**: Redundant work, unnecessary I/O, missing caching or batching.
- **Robustness**: Resource leaks, race conditions, silent failures.
- **Consistency**: Divergence from project patterns and `docs/architecture/SYSTEM_CONTRACT.md`.

Classify each finding: **critical** (must fix), **warning** (should fix), **suggestion** (consider). For each: file, location (line range or symbol), issue (one clear sentence), fix_example (concrete — must be passable directly to `/code-fix`).

## Output Format

```json
{
  "status": "SUCCESS | DATA_MISSING | ERROR",
  "work_log": {
    "assumptions": [],
    "sources_used": [],
    "files_read": [],
    "files_modified": [],
    "validation_checks": []
  },
  "result": {
    "feature": "",
    "summary": "",
    "critical": [{"file": "", "location": "", "issue": "", "fix_example": ""}],
    "warnings": [{"file": "", "location": "", "issue": "", "fix_example": ""}],
    "suggestions": [{"file": "", "location": "", "issue": "", "fix_example": ""}],
    "implementation_notes": ""
  }
}
```

`files_modified` must be `[]` — this skill does not edit files. Pass result to `/code-fix` to apply.

## Validation

Before returning: confirm EXTRACT was read-only and all artifact paths are in work_log.files_read; confirm every finding has file, location, issue, and fix_example concrete enough for `/code-fix`; confirm JSON is exact and valid. If any check fails, revise and recheck.
