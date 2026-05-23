# Future Action Matrix

These are future actions only. Phase 3F performed none of them.

| Candidate group | Classification | Future action | Notes |
|---|---|---|---|
| Phase 2 `strategy_lab_artifact_v1` docs, JSON schema, and fixtures | authoritative candidate | `COMMIT_TO_BASELINE_CANDIDATE` | Treat as the primary schema baseline if approved. |
| Phase 2 task card | task-history evidence | `COMMIT_TO_BASELINE_CANDIDATE` | Preserve if the phase chain should be auditable in git. |
| Phase 2 report bundle | report evidence | `FORCE_ADD_REPORT_EVIDENCE_CANDIDATE` | `reports/` is ignored, so this requires explicit force-add approval. |
| Phase 2B helper doc/module/test/fixtures | pending-review helper | `KEEP_PENDING_REVIEW` | Keep out of runtime/backend wiring until separately approved. |
| Phase 2B raw payload summaries and normalized helper artifacts | pending-review helper/report evidence | `KEEP_PENDING_REVIEW` | Useful as helper evidence only; not canonical financial truth. |
| Phase 2B helper material conflicting with Phase 2 authoritative schema | duplicate/superseded | `SUPERSEDE_WITH_AUTHORITATIVE_SCHEMA` | `strategy_lab_artifact_v1` stays authoritative. |
| Phase 2B task card/report bundle | task-history/report evidence | `FORCE_ADD_REPORT_EVIDENCE_CANDIDATE` | Preserve only if explicit report/task-history preservation is desired. |
| Phase 3A adapter docs and mock payloads | active candidate, currently staged | `COMMIT_TO_BASELINE_CANDIDATE` | Requires a separate decision because the additions are staged in that worktree. |
| Phase 3A staged task card/report files | task-history/report evidence, currently staged | `DATA_MISSING_REVIEW_REQUIRED` | Needs an explicit unstage/commit/archive decision before consolidation. |
| Phase 3B unique mock vectors and unittest | active candidate | `COMMIT_TO_BASELINE_CANDIDATE` | Preserve as the reconciled mocked-test handoff if approved. |
| Phase 3B copied Phase 2/3A docs | duplicate consolidation copies | `SUPERSEDE_WITH_AUTHORITATIVE_SCHEMA` | Use Phase 2/3A source copies as the authority, not Phase 3B duplicates. |
| Phase 3B report bundle | report evidence | `FORCE_ADD_REPORT_EVIDENCE_CANDIDATE` | Force-add only if report evidence should live in git. |
| Phase 3B `strategy_lab_quantdinger_framework_v1_20260520` bundle | older duplicate | `ARCHIVE_ONLY` | Preserve externally or archive; do not make it current baseline. |
| Phase 3B pycache | generated | `EXCLUDE_GENERATED` | Do not preserve. |
| Phase 3C mock transport docs, fixtures, and unittest | active candidate | `COMMIT_TO_BASELINE_CANDIDATE` | Preserve as latest offline mock transport evidence if approved. |
| Phase 3C copied Phase 2/3A/3B docs and vectors | duplicate consolidation copies | `SUPERSEDE_WITH_AUTHORITATIVE_SCHEMA` | Use original authoritative candidates where possible. |
| Phase 3C report bundle | report evidence | `FORCE_ADD_REPORT_EVIDENCE_CANDIDATE` | Force-add only if report evidence should live in git. |
| Phase 3C `strategy_lab_quantdinger_framework_v1_20260520` bundle | older duplicate | `ARCHIVE_ONLY` | Preserve externally or archive; do not make it current baseline. |
| Phase 3C pycache | generated | `EXCLUDE_GENERATED` | Do not preserve. |
| Phase 3D task card | task-history evidence | `COMMIT_TO_BASELINE_CANDIDATE` | Currently untracked in the current checkout. |
| Phase 3D report bundle | report evidence | `FORCE_ADD_REPORT_EVIDENCE_CANDIDATE` | Current ignored report bundle should be preserved if the chain is saved. |
| Phase 3E task card | task-history evidence | `COMMIT_TO_BASELINE_CANDIDATE` | Currently untracked in the current checkout. |
| Phase 3E report bundle | report evidence | `FORCE_ADD_REPORT_EVIDENCE_CANDIDATE` | Immediate Phase 3F input; preserve if the chain is saved. |
| Phase 3F task card and report bundle | task-history/report evidence | `FORCE_ADD_REPORT_EVIDENCE_CANDIDATE` | This report should be preserved if Phase 3G is drafted from it. |
| Proof of committed consolidated baseline | missing evidence | `DATA_MISSING_REVIEW_REQUIRED` | No current evidence proves the candidate files are already saved in baseline. |

## Required Future Sequencing

Before any production-module task card:

1. Draft a Phase 3G consolidation/save task card only.
2. In that draft, enumerate exact paths to save, force-add, archive, or exclude.
3. Include a separate decision for the staged Phase 3A additions.
4. Include preservation of Phase 3D and Phase 3E task cards if task-history
   continuity is desired.
5. Decide whether ignored report bundles under `reports/agent_jobs` should be
   force-added or left as external local evidence.
6. Exclude Phase 3B and Phase 3C pycache files.
7. Preserve a Project Memory save block after the decision is stable, so later
   work does not confuse helper candidates with authoritative baseline.
8. Only after explicit user approval for actual consolidation mutation should a
   save/commit/archive execution task be run.
9. Only after consolidation evidence is saved or deliberately rejected should a
   production-module implementation task-card draft be considered.
