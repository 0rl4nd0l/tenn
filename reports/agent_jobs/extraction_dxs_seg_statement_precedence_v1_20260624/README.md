# DXS/SEG Statement Precedence Safe Extension

Status: DONE_WITH_RISK / PARTIAL.

This report records the issue #97 DXS/SEG-only safe extension authorized from
`reports/agent_jobs/extraction_issue97_gate_blocker_source_review_v1_20260624/BOARD_DECISION.json`.

## Scope Boundaries

- In scope: DXS stapled/group statement selection; SEG Appendix 4D wrapper
  versus full financial statement precedence.
- Out of scope: ANZ bank policy, candidate-review approval, net-debt semantics,
  broad parser rewrites, global metric mapping, prompts, schema, gold fixtures,
  source PDFs, runtime services, DB, Qdrant, Redis, news, memory, model, GPU, and
  production data.

## Runtime Functionality Proof

This is extractor and no-write evaluation work, not live runtime mutation. The
scoped intended output changed in the report-local replay and scorecard: DXS and
SEG statement-precedence metrics now score correctly. The full approved-15 #97
pre-persistence gate still fails, so production extraction functionality is not
proven by this report.

result: PARTIAL

| Field | Required evidence |
| --- | --- |
| intended output | DXS/SEG no-write extraction payloads and approved-15 #97 scorecard rows for statement-precedence metrics. |
| live output location | Report-local artifacts under `reports/agent_jobs/extraction_dxs_seg_statement_precedence_v1_20260624/`; no live DB/API/store mutation intended. |
| pre-run max timestamp or count | Prior approved-15 source-review packet showed DXS/SEG statement-precedence blockers; this run started from `BOARD_DECISION.json` and baseline evidence in `source_review_board_decision.json`. |
| post-run max timestamp or count | `raw_replay_after_fix/validation.json`: `PARTIAL`, 15 cases, 12 accepted, 3 fail-closed, 0 failed, side-effect pass. |
| rows/files inserted or updated after run start | Report artifacts only; no forbidden surface mutation per `raw_replay_after_fix/side_effect_audit.json`. |
| readiness/gate status | `scorecard_gate_after_fix.json`: `gate_status=fail`, `decision=blocked`. |
| exact command/query used | Full command is logged in `validation.json`; primary replay command wrote `logs/replay_after_fix.log` and scorecard artifacts. |
| result: WORKING / PARTIAL / BROKEN / DATA_MISSING | PARTIAL |
| remaining blocker | Full approved-15 gate blockers remain outside this scoped statement-precedence fix: BHP/MIN wrong values, RMS cashflow/capex missing, SEG shares outstanding missing, fail-closed GRE/QBE/TCL, and ambiguous quarantines. |

## Validation Summary

- Focused DXS/SEG precedence tests: 6 passed.
- Full `test_multipass_extraction.py`: 243 passed, 1 warning.
- Ruff on changed code/tests: passed.
- Approved-15 no-write replay: `PARTIAL`, 12 accepted, 3 fail-closed, 0 failed, side-effect pass.
- Approved-15 scorecard gate: failed/blocked.

## Next Recommended Prompt

`/goal Continue from reports/agent_jobs/extraction_dxs_seg_statement_precedence_v1_20260624/validation.json. Preserve the DXS/SEG statement-precedence fix. Triage the remaining approved-15 #97 blockers only by owner-approved lane: SEG shares outstanding, RMS cashflow/capex, BHP/MIN wrong NP, GRE/QBE/TCL fail-closed, or ambiguous quarantine policy. Do not widen into ANZ bank policy, net-debt semantics, candidate-review approval, gold fixtures, source PDFs, prompts, schema, DB, Qdrant, Redis, news, memory, model/GPU, or runtime state without explicit approval.`
