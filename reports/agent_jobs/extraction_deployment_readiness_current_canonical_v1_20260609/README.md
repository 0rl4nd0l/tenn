# Extraction Deployment Readiness Closeout

Generated: 2026-06-09T06:40:26Z

Status: `DONE_WITH_RISK`.

This is an audit-only closeout. It did not run count-24, count-32, random
samples, broad extraction, backfill, or full ticker-universe extraction.

## Current Checkout

- worktree: `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`
- branch: `safe/cockpit-news-context-date-filter-merge-packets-preserve-v1-20260609`
- HEAD: `932284857b02f469429482d1e9080870ca55a7a1`
- remote canonical: `ee839fd9d7cd438aa1f6953642ef3bb0080b252a`
- current HEAD is ancestor of remote canonical: true
- approved count-24 target `bf133f06047360545905b2950830645fe9649d98` is ancestor of remote canonical: true
- read-only registry: `active_jobs=[]`, `lock_acquired=false`

## Recently Addressed PRs

- PR #336 merged: HUB half-year period binding from source evidence.
  Merge commit: `356c495d8a6f3fb09d1cf3d2aa7d3a79b0a6e448`.
- PR #331 merged: CTN quarterly source evidence precedence.
  Merge commit: `c5c39d128a6e1ea23415f08803844677add1efdd`.
- PR #309 merged: count-24 approval packet preservation.
  Merge commit: `bfe3a77ec6692d5052eefec7454461e75459f7e3`.
- PR #196 merged: cockpit operations backfill review gate.
  This was observed as canonical-head context, not extraction-readiness proof.

## Count-24 Evidence

Count-24 was completed separately in:
`/home/l4nd0/tenn-count24-bounded-validation-current-canonical-v1-20260609`

- commit: `cc2a2df5a3eef0b0d43a300620d8d33aeea63d6a`
- approved target: `bf133f06047360545905b2950830645fe9649d98`
- seed: `20260602`
- verdict: `COUNT24_SUCCESS_WITH_RISK`
- total: 24
- ok: 11
- ok_low_confidence: 1
- failed: 12
- exceptions: 0
- unsafe accepted outputs: 0
- accepted outputs missing row refs or extraction run id: 12

Failure taxonomy:

- `classifier_low_confidence:0.0`: 1
- `source_noncandidate:board_change_notice`: 1
- `source_noncandidate:meeting_or_proxy_notice`: 2
- `source_noncandidate:operational_project_update`: 1
- `source_noncandidate:pre_results_segment_re_presentation`: 1
- `source_noncandidate:share_sale_or_gross_proceeds_announcement`: 1
- `validation_gate:announcement_date_period_end`: 1
- `validation_gate:insufficient_metrics`: 1
- `validation_gate:metric_label_mismatch`: 1
- `validation_gate:scale_unknown`: 2

## Open Readiness Blockers

- Issue #73 remains open: Financial Truth extraction redesign parent tracker.
- Issue #96 remains open: most PDF-path documents lack terminal extraction.
- Issue #97 remains open: extracted-payload scorecard for confirmed metric
  coverage.
- Issue #286 remains open: field-level provenance and accounting number parsing.

## Deployment Readiness Decision

Financial metric extraction is not ready for broad deployment.

The current evidence proves bounded progress only:

- PR #336 fixed a specific title-only period-end safety hole.
- PR #331 fixed a specific CTN source-type precedence problem.
- Count-24 completed without side-effect mutation and without unsafe accepted
  outputs.

The current evidence does not prove broad accuracy:

- 12 of 24 count-24 documents still failed.
- All 12 accepted outputs lack page/table/row refs or an extraction run id in
  the report-local row shape.
- Failure classes still include source classification gaps, scale recovery
  gaps, insufficient metric capture, metric-label mismatch, and low-confidence
  classification.
- The local `safe/extraction-count32-approval-packet-post-count24-v1-20260609`
  branch is only an approval-packet artifact; it is not count-32 execution
  evidence and does not authorize count-32 by itself.

## Root-Cause Summary

The remaining problem is not one isolated parser bug. The extraction path still
needs:

- field-level provenance that survives into accepted rows;
- deterministic accounting-number parsing and scale binding;
- stronger source-document classification for presentations, meetings,
  operational updates, and financial-report wrappers;
- metric ontology/label gates that distinguish canonical financial values from
  adjacent disclosure labels;
- scorecard coverage that can compare extracted payloads against confirmed
  evidence before promotion.

## Unsafe Actions Avoided

- count-24 not run in this closeout
- count-32 not run
- random sample not run
- broad extraction not run
- backfill not run
- full ticker-universe extraction not run
- GitHub issue/PR mutation not performed
- DB, Qdrant, Redis, news, memory, source PDFs, prompts, gold labels, runtime
  config, schema, services, model/GPU config, and production data not mutated

## Next Approval Boundary

Before any count-32 or broader run, create a separate approval packet that
states the exact canonical commit, seed, count, source root, runner, side-effect
guards, and accepted-output audit criteria. Do not infer count-32 approval from
the count-24 result or from the local count-32 packet branch.
