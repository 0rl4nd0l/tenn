# Docs Current State Consolidation V1 Report

## Verdict

Docs-only safe extension proceeded after audit. Collision risk was MEDIUM overall and HIGH only for audit-time PR #387-controlled control-plane status and task-ledger files, which were intentionally not touched. Publish preflight on 2026-06-23T06:58:39Z found PR #387 merged and the target branch advanced to `f195e90d464f49916f6626242ca26d74580dc0a1`.

This job improved agent navigation by adding `docs/README.md` as the canonical documentation source map, wiring it from top-level agent entrypoints, demoting stale current-state snapshots, and refreshing stale skill-surface metadata. It did not modify runtime/product/extraction/data behavior and did not prove runtime functionality. Runtime docs were updated only where checked code/config evidence supported safer current wording.

## Current Repo Evidence

- Worktree: `/home/l4nd0/tenn-docs-current-state-consolidation-v1-20260623`
- Branch: `docs/current-state-consolidation-v1-20260623`
- HEAD: `e402bf38e5b959f56c1bed6b35e18ba7371cd8f6`
- Upstream at audit closeout: `origin/migration/clean-runtime-baseline-reconstruct-v1` at `e402bf38e5b959f56c1bed6b35e18ba7371cd8f6`
- Upstream at publish preflight: `origin/migration/clean-runtime-baseline-reconstruct-v1` at `f195e90d464f49916f6626242ca26d74580dc0a1`
- Task card: `docs/agent_tasks/docs_current_state_consolidation_v1_20260623.md`
- Registry: claimed active record for this job after read-only list/overlap checks showed no active conflicts; released cleanly at closeout.
- Ledger: live ledger `DATA_MISSING`; committed ledger exists and was empty in this run.

## Docs Inspected

Inspected top-level agent files, docs indexes/source-map candidates, runtime/setup docs, architecture index and contract, dev-flow docs, registry docs, repo-backed skills, Claude reference docs, task-card/report archive counts, and targeted stale-current references. See `doc_inventory.json` and `evidence_manifest.json`.

## Docs Changed

See `changed_docs_summary.md` for exact file-level summary.

## Conflicts Resolved

- Runtime startup scope conflict: resolved by scoping `docs/startup.md` as full-stack Docker/user-launcher mode and preserving `docs/entrypoints.md` as agent runtime-entrypoint context.
- Prompt authority conflict: resolved by marking `docs/prompts/CODEX_MASTER_PROMPT.md` reference-only and removing current all-agent authority wording.
- Skill-surface stale metadata: refreshed to current HEAD with limited verification scope.
- Current-state fragmentation: reduced by adding `docs/README.md` and reference banners on stale snapshots.

## Conflicts Not Resolved

- PR #387 controlled `CONTROL_PLANE_STATUS.md`, `CONTROL_PLANE_OPEN_WORK.md`, and task-ledger docs during the audit. This job avoided those files. Publish preflight found PR #387 merged, so the conflict is no longer active but the files remain intentionally untouched by this docs-source-map job.
- Live task ledger remains `DATA_MISSING` at the resolved shared registry path.
- Runtime functionality remains `DATA_MISSING`; read-only checks observed llama.cpp, Redis, and Ollama listeners only, with no backend/Cockpit/Qdrant/Postgres functionality proof.
- Runtime path/model docs were refreshed from checked launcher/verifier/model-routing files; `cockpit_api.py` default model path drift remains a separate code/runtime follow-up.

## Runtime Functionality Proof

No runtime functionality was claimed by this docs job. The table is included so
future agents do not mistake read-only listener/service evidence for a working
runtime.

| Field | Evidence |
| --- | --- |
| intended output | Documentation navigation/source-map artifacts only; no runtime output intended. |
| live output location | `DATA_MISSING` for runtime output; report artifacts under `reports/agent_jobs/docs_current_state_consolidation_v1_20260623/`. |
| pre-run max timestamp or count | `DATA_MISSING`; no runtime baseline captured because runtime mutation/probing was out of scope. |
| post-run max timestamp or count | `DATA_MISSING`; no runtime output queried after edits. |
| rows/files inserted or updated after run start | Runtime rows/files: `DATA_MISSING`; docs/report files changed only. |
| readiness/gate status | Docs validation passed after final report refresh; runtime readiness not checked. |
| exact command/query used | Read-only service/listener commands only: `systemctl --user show llama-cpp-router.service`, `ss -ltnp`, and filtered `docker ps`. |
| result | `DATA_MISSING` |
| remaining blocker | Runtime proof requires a separate runtime task with approved endpoint/store probes. |

result: DATA_MISSING

## Future Agent Reading Path

1. `AGENTS.md`
2. Active task card under `docs/agent_tasks/`
3. `docs/README.md`
4. Relevant `.agents/skills/*/SKILL.md`
5. Only the selected runtime, architecture, registry, report, or historical reference doc

## Save Recommendation

Project Memory save: `RECOMMENDED`. Reason: the repo now has a canonical docs source map and this run found a recurring live-ledger/PR #387 collision pattern useful for future Tenn docs/control-plane sessions.

Merge parking: not used. No parked work was merged or unparked. Publish preflight found PR #387 already merged; if a future branch again conflicts with control-plane status or ledger surfaces, park/review it as docs-only rather than editing those surfaces opportunistically.

New GPT session: optional after commit/PR handoff only; not required for completing validation in this run.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/docs_current_state_consolidation_v1_20260623.md`: PASS
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/docs_current_state_consolidation_v1_20260623.md --no-write-report`: PASS
- `python3 scripts/agent_job_contract.py check-report-artifacts docs/agent_tasks/docs_current_state_consolidation_v1_20260623.md`: PASS
- `python3 scripts/agent_job_registry.py list-active --read-only --repo-root .`: PASS; one matching active job after claim, no active jobs after release
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/docs_current_state_consolidation_v1_20260623.md --repo-root .`: PASS
- `git diff --check`: PASS
- `python3 -m json.tool status/doc_inventory/doc_conflict_matrix/evidence_manifest`: PASS
- `changed markdown link sanity script`: PASS; 14 markdown files checked
- `markdownlint changed docs`: DATA_MISSING; markdownlint not installed
- `stale reference grep on changed docs`: PASS; no stale closeout/runtime-overclaim phrases found in changed docs/report files
- `forbidden path guard`: PASS

## Final Diff Guard

Parent diff guard found changed files inside the exact task-card allowlist after the allowlist was tightened for literal repo validators. Final subagent reviewer reported three blockers: stale closeout artifacts, untracked canonical source-map/task-card files, and overly strong runtime verification wording. The first and third were remediated in the report/docs; the second is handled by staging the untracked canonical docs before commit.
