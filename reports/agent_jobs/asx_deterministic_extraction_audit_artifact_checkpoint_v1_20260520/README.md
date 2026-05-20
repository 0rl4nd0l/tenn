# ASX deterministic extraction audit artifact checkpoint

## Confirmed facts

- Runtime path: `/home/l4nd0/tenn-runtime` resolves to `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`.
- Runtime branch before checkpoint: `migration/clean-runtime-baseline-reconstruct-v1`.
- Runtime HEAD before checkpoint: `2e7163147052`.
- Source worktree: `/home/l4nd0/tenn-asx-deterministic-extraction-audit-v1-20260519`.
- Source branch: `audit/asx-deterministic-extraction-extension-v1-20260519`.
- Source HEAD: `0b8c4d942be5`.
- The target ASX audit task card and report directory did not already exist in the runtime branch before copy, so no newer report was overwritten.
- The source artifact bundle was limited to one task card and nine report files.
- Secret and broad personal-data pattern checks found no credential, email, or phone-number matches. The only credential-pattern check hit was the method name `anthropic` in `extension_point_inventory.json`.
- Registry overlap was clean before claim.
- Registry claim succeeded for `asx_deterministic_extraction_audit_artifact_checkpoint_v1_20260520`.

## DATA_MISSING

- No extraction, Docling, OCR, comparator, DB, Qdrant, runtime, memory, news, Cockpit, parser, prompt, or gold-label validation was run during this checkpoint.
- The final checkpoint commit hash cannot be embedded in this report before the commit object exists. The final closeout records the created commit hash.
- Registry release updates the tracked checkpoint `status.json` after the initial commit. That released status is folded into the final checkpoint commit with `git commit --amend`.

## Exact artifacts preserved

| Artifact | Source worktree path |
| --- | --- |
| `docs/agent_tasks/asx_deterministic_extraction_extension_audit_v1_20260519.md` | `/home/l4nd0/tenn-asx-deterministic-extraction-audit-v1-20260519/docs/agent_tasks/asx_deterministic_extraction_extension_audit_v1_20260519.md` |
| `reports/agent_jobs/asx_deterministic_extraction_extension_audit_v1_20260519/DATA_MISSING.md` | `/home/l4nd0/tenn-asx-deterministic-extraction-audit-v1-20260519/reports/agent_jobs/asx_deterministic_extraction_extension_audit_v1_20260519/DATA_MISSING.md` |
| `reports/agent_jobs/asx_deterministic_extraction_extension_audit_v1_20260519/README.md` | `/home/l4nd0/tenn-asx-deterministic-extraction-audit-v1-20260519/reports/agent_jobs/asx_deterministic_extraction_extension_audit_v1_20260519/README.md` |
| `reports/agent_jobs/asx_deterministic_extraction_extension_audit_v1_20260519/comparator_artifact_plan.md` | `/home/l4nd0/tenn-asx-deterministic-extraction-audit-v1-20260519/reports/agent_jobs/asx_deterministic_extraction_extension_audit_v1_20260519/comparator_artifact_plan.md` |
| `reports/agent_jobs/asx_deterministic_extraction_extension_audit_v1_20260519/deterministic_parser_plan.md` | `/home/l4nd0/tenn-asx-deterministic-extraction-audit-v1-20260519/reports/agent_jobs/asx_deterministic_extraction_extension_audit_v1_20260519/deterministic_parser_plan.md` |
| `reports/agent_jobs/asx_deterministic_extraction_extension_audit_v1_20260519/diff-check.json` | `/home/l4nd0/tenn-asx-deterministic-extraction-audit-v1-20260519/reports/agent_jobs/asx_deterministic_extraction_extension_audit_v1_20260519/diff-check.json` |
| `reports/agent_jobs/asx_deterministic_extraction_extension_audit_v1_20260519/document_type_classifier_plan.json` | `/home/l4nd0/tenn-asx-deterministic-extraction-audit-v1-20260519/reports/agent_jobs/asx_deterministic_extraction_extension_audit_v1_20260519/document_type_classifier_plan.json` |
| `reports/agent_jobs/asx_deterministic_extraction_extension_audit_v1_20260519/extension_point_inventory.json` | `/home/l4nd0/tenn-asx-deterministic-extraction-audit-v1-20260519/reports/agent_jobs/asx_deterministic_extraction_extension_audit_v1_20260519/extension_point_inventory.json` |
| `reports/agent_jobs/asx_deterministic_extraction_extension_audit_v1_20260519/no_regression_gate_map.json` | `/home/l4nd0/tenn-asx-deterministic-extraction-audit-v1-20260519/reports/agent_jobs/asx_deterministic_extraction_extension_audit_v1_20260519/no_regression_gate_map.json` |
| `reports/agent_jobs/asx_deterministic_extraction_extension_audit_v1_20260519/status.json` | `/home/l4nd0/tenn-asx-deterministic-extraction-audit-v1-20260519/reports/agent_jobs/asx_deterministic_extraction_extension_audit_v1_20260519/status.json` |

## Reports force-added

- The `reports/agent_jobs/...` paths are ignored by the repo and must be staged with `git add -f`.
- The checkpoint commit force-added only:
  - `reports/agent_jobs/asx_deterministic_extraction_extension_audit_v1_20260519/`
  - `reports/agent_jobs/asx_deterministic_extraction_audit_artifact_checkpoint_v1_20260520/`

## Registry and git closeout

- Registry claim status: claimed successfully before artifact copy.
- Registry release status: released successfully after the initial commit.
- Final git status: verified clean after folding the released `status.json` into the final checkpoint commit.

## Preserved ASX audit result

- Verdict: `ASX_DETERMINISTIC_EXTENSION_READY_FOR_DESIGN`.
- Truth status: `CANONICAL_TRUTH_SAFE`.
- Main conclusion: the safe extraction path is fixture/schema-first and comparator-first:
  1. ASX document-type fixture/schema contract.
  2. Pure classifier module and unit tests.
  3. Read-only comparator artifact schema with `canonical_write=false`.
  4. Deterministic sidecar parser prototypes.
  5. Gate run/report before any parser routing or canonical writes.

## Explicit non-actions

This checkpoint did not run extraction, Docling, OCR, comparator tools, DB/Qdrant/runtime/memory/news/Cockpit validation, parser changes, prompt changes, gold-label changes, canonical writes, Docker Compose edits, runtime config edits, or source-code edits.

## Project Memory save recommendation

Save this checkpoint as a memory item after commit: ASX deterministic extraction extension audit artifacts were preserved into `/home/l4nd0/tenn-runtime` on `migration/clean-runtime-baseline-reconstruct-v1`; the preserved conclusion is fixture/schema-first and comparator-first, with comparator artifacts read-only and `canonical_write=false`.
