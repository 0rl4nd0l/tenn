# Extraction No-Write Harness Source and Runner Safety Repair

Job: `extraction_no_write_harness_source_runner_safety_v1_20260620`

Task card:
`docs/agent_tasks/extraction_no_write_harness_source_runner_safety_v1_20260620.md`

## Scope

Focused PR #379 repair for two code-review findings:

- source snapshots now include each selected source PDF's parent directory tree,
  so sidecar files written next to source PDFs are detected;
- top-level runner exceptions are classified before `DATA_MISSING` is reported,
  so unexpected runner bugs produce a failing synthetic result row.

## Evidence

- `baseline_preflight/validation.json`: no-write guard-corpus preflight result.
- `baseline_preflight/side_effect_audit.json`: side-effect surface audit.
- `validation.json`: command-level validation summary.
- `PR_REVIEW.md`: local code-reviewer pass.
- `diff-check.json`: task-card allowlist check.
