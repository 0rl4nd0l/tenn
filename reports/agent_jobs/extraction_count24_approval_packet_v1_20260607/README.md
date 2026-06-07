# Count-24 Approval Packet After PR #306

State: `DONE_WITH_RISK`.

Mode: APPROVAL PACKET / REPORT ONLY.

Count-24 status: `NOT_AUTHORIZED`.

Generated from canonical branch
`migration/clean-runtime-baseline-reconstruct-v1` at
`b67736109db2c405171ff039c3b2f071238205db`, the PR #306 merge commit.

No count-24, count-32, extraction sample, broad extraction, broad backfill, full
ticker-universe extraction, containment mutation, DB/Qdrant/news/memory
mutation, source-PDF edit, extraction-code change, prompt/gold-label/runtime/
schema/service/model/GPU change, or unrelated cleanup was run while preparing
this packet.

## Evidence Read

- Parent task card:
  `docs/agent_tasks/extraction_post_pr301_broad_accuracy_push_v1_20260607.md`.
- Parent closeout:
  `reports/agent_jobs/extraction_post_pr301_broad_accuracy_push_v1_20260607/README.md`.
- Parent status:
  `reports/agent_jobs/extraction_post_pr301_broad_accuracy_push_v1_20260607/status.json`.
- Count-16 validation status and manifest:
  `reports/agent_jobs/extraction_post_pr301_count16_validation_v1_20260607/status.json`
  and `sample_manifest.json`.
- Count-16 failure and accepted-output taxonomy:
  `reports/agent_jobs/extraction_post_pr301_count16_taxonomy_v1_20260607/failure_taxonomy.json`
  and `accepted_output_audit.json`.
- DXC/LBL containment proof:
  `reports/agent_jobs/extraction_post_pr301_dxc_lbl_containment_v1_20260607/README.md`.

The merged evidence records:

- Final prior decision: `READY_FOR_COUNT24_APPROVAL_PACKET`.
- Prior count-16 seed: `20260602`.
- Prior count-16 result: 7 ok, 0 ok_low_confidence, 9 failed, 0 exceptions.
- Prior candidate pool count: `28633`.
- Prior ordered candidate pool hash:
  `3d99f44885fd056ac3f112d56abe95d14dd1ac9affdcd7315f860f690cdeb63f`.
- Prior sorted candidate pool hash:
  `e4d57b2cdb3e8583a3aeaf33fba5a2d959383500733473349771f80531629e7a`.
- DXC/LBL containment: no-op proof; no exact DB/Qdrant exposure found.
- Post-repair accepted-output guard:
  `validation_gate:announcement_date_period_end`; saved HUB/LBL payloads fail
  closed after the repair.

## Operator Approval Language

Count-24 remains unauthorized until the operator provides this exact approval:

```text
I APPROVE COUNT-24 ONLY for Tenn extraction validation on canonical b67736109db2c405171ff039c3b2f071238205db using seed 20260602. Do not run count-32, broad extraction, backfill, or full ticker-universe extraction.
```

Any materially different approval text is insufficient. Approval of count-24
does not approve count-32, broad extraction, backfill, full ticker-universe
extraction, containment mutation, source-PDF edits, prompt/gold-label/schema
changes, service restarts, DB/Qdrant/news/memory mutation, or runtime/model/GPU
configuration changes.

## Proposed Count-24 Strategy

- Use a bounded count-24 validation run only.
- Use seed `20260602` to preserve comparability with the post-PR301 count-16.
- Recompute the candidate pool immediately before execution.
- Select 24 documents using the same deterministic candidate ordering used by
  the post-PR301 count-16 runner.
- Write the selected-document manifest before extracting any document.
- If the candidate pool count/hash differs from prior count-16 evidence, stop
  before extraction and ask whether to approve a drifted count-24 or refresh this
  packet.

## Candidate Pool Hash Gate

Before any count-24 execution, capture:

- `candidate_pool_count`
- `candidate_pool_ordered_sha256`
- `candidate_pool_sorted_sha256`
- candidate source/query description
- candidate generation command
- canonical HEAD
- timestamp UTC

Reference values from the prior count-16:

- count: `28633`
- ordered hash:
  `3d99f44885fd056ac3f112d56abe95d14dd1ac9affdcd7315f860f690cdeb63f`
- sorted hash:
  `e4d57b2cdb3e8583a3aeaf33fba5a2d959383500733473349771f80531629e7a`

Missing hashes or unexplained drift are hard stops.

## Selected-Document Manifest Gate

The count-24 selected-document manifest must exist before the first extraction.
It must include:

- requested count, actual count, seed, canonical HEAD
- candidate pool count and hashes
- selected document IDs
- per-document index, document ID, ticker, PDF path, title, source class,
  selection seed, candidate pool hash, and canonical HEAD

Missing or invalid manifest is a hard stop.

## Runtime Readiness Gates

Before a future approved count-24 run:

- Confirm git path, branch, HEAD, remote, and clean worktree.
- Confirm canonical HEAD includes
  `b67736109db2c405171ff039c3b2f071238205db`.
- Validate the execution task card with exact `allowed_files`.
- Read registry active jobs with safe read-only evidence and stop on overlap.
- Capture runtime backend target and readiness.
- Capture loaded commit proof. If a service is used, the service must prove the
  loaded backend/extractor commit. If direct module execution is used, the run
  script must record module path and git HEAD.
- Stop if loaded commit proof is `DATA_MISSING`.

## Queue, GPU, And Process Gates

Before the run:

- Capture Redis/extraction queue lengths and unacked keys.
- List extraction/backend/worker/llama processes with PIDs and command lines.
- Capture GPU telemetry with `nvidia-smi` if available.
- If `nvidia-smi` fails, mark GPU telemetry `DATA_MISSING`; do not proceed
  unless the operator accepts that specific missing evidence.

After the run:

- Queues must return to baseline or every residual item must be explained.
- No orphaned extraction/backend/worker/llama process may remain from the run.
- GPU process list must return to baseline or every residual process must be
  explained.

Unknown live queue payloads, process ownership conflict, or missing baselines are
hard stops.

## Accepted-Output Audit

Every `ok` and `ok_low_confidence` row must be audited for:

- source-document class: financial report or explicitly justified unknown
  document
- source-bound period type and period end
- half-year period end not equal to a leading announcement date
- source-bound scale, not `unknown`
- no EBITDA or net operating income accepted as canonical EBIT
- metric value provenance, including row/page/source text where available
- sanity checks for revenue, cash end, shares outstanding, and impossible
  magnitudes
- non-AUD handling as `ok_low_confidence` unless a separate policy exists

Special rechecks:

- HUB/LBL-like half-year announcement-date rows must fail closed.
- DXC-like net operating income as EBIT must fail closed.
- `director_interest_notice` and all other noncandidate classes must not appear
  as accepted outputs.

## Side-Effect Audit

Capture before and after:

- git status
- source-PDF diff/staged audit
- DB file mtimes/sizes for configured DB paths
- Qdrant collection/point counts if reachable
- Redis queue lengths and unacked keys
- news/memory store mutation indicators where applicable
- process and GPU baselines

The final count-24 report must include:

- `db_files_changed`
- `qdrant_changed`
- `news_route_used`
- `memory_mutated`
- `source_pdfs_changed`
- `queues_clean_after_run`
- `unexpected_processes_after_run`

## Stop Conditions

Stop before extraction if:

- exact operator approval is absent
- canonical HEAD does not include PR #306 merge commit
- task-card validation fails
- registry shows overlapping extraction/evaluation work
- candidate pool count/hash is missing or has unexplained drift
- selected-document manifest is missing or invalid
- loaded commit proof is missing
- runtime/backend is unavailable
- queue/GPU/process baseline is unavailable

Stop after preserving artifacts if:

- any accepted output has unsafe source-bound truth evidence
- any side-effect anomaly appears
- an exception occurs
- the run attempts to widen into count-32, broad extraction, backfill, or full
  ticker-universe extraction

## Containment Plan

If unsafe accepted rows appear:

1. Stop after count-24; do not proceed to count-32.
2. Record exact document ID, ticker, run ID, metric, row reference, provenance,
   DB row key, and Qdrant point ID where present.
3. Snapshot affected DB/Qdrant rows or record `DATA_MISSING` for missing exact
   identifiers.
4. Write a containment approval packet.
5. Obtain explicit operator approval before any DB/Qdrant mutation.

Allowed without extra approval: report unsafe rows, classify taxonomy, and write
report artifacts.

Forbidden without extra approval: delete/update DB rows, delete/update Qdrant
points, run broad cleanup, or rerun extraction/backfill.

## Thresholds

Green:

- exceptions = 0
- unsafe accepted outputs = 0
- side-effect anomalies = 0
- every `ok_low_confidence` row is explained
- at least 12 of 24 are `ok` or explainably `ok_low_confidence`
- failed rows are acceptable only when fail-closed and classified

Yellow:

- exceptions = 0
- unsafe accepted outputs = 0
- side-effect anomalies = 0
- residual `DATA_MISSING` is bounded and non-blocking
- action: taxonomy/report only; no count-32 approval

Red:

- any unsafe accepted output
- any exception
- any side-effect anomaly
- invalid candidate pool hash or selected manifest
- action: stop, preserve artifacts, prepare containment or blocker report

Count-32 graduation is not authorized by this packet. It requires a separate
approval after count-24 taxonomy and side-effect audit.

## Remaining Risks

- WHC 2022 scale root cause remains unresolved.
- Prior `nvidia-smi` failed during count-16, so GPU telemetry may remain
  `DATA_MISSING`.
- PR #301 artifacts omitted accepted-row refs/provenance and extraction run IDs.
- Route-level DXC/LBL exposure checks were not run because exact DB/Qdrant
  matches were absent.
- Count-24 may reveal new unsafe accepted-output classes not seen in count-16.

## DATA_MISSING

- Current runtime loaded-commit proof was not collected because this packet does
  not start services or runtime.
- Current queue/GPU/process baselines were not collected because count-24
  execution is not authorized.
- Future candidate pool count/hash and selected-document manifest are pending
  until approved execution preflight.

## Files Touched

- `docs/agent_tasks/extraction_count24_approval_packet_v1_20260607.md`
- `reports/agent_jobs/extraction_count24_approval_packet_v1_20260607/README.md`
- `reports/agent_jobs/extraction_count24_approval_packet_v1_20260607/approval_packet.json`
- `reports/agent_jobs/extraction_count24_approval_packet_v1_20260607/status.json`
- `reports/agent_jobs/extraction_count24_approval_packet_v1_20260607/validation.json`
- `reports/agent_jobs/extraction_count24_approval_packet_v1_20260607/raw_commands.log`

## Files Intentionally Not Touched

- extraction source code
- source PDFs
- prompts
- gold labels
- schemas
- DB/Qdrant/news/memory/runtime/service/model/GPU config
- post-PR301 source reports

## Next Recommended Prompt

```text
Approve or reject the count-24 run using the exact approval language in
reports/agent_jobs/extraction_count24_approval_packet_v1_20260607/README.md.
If approved, create a separate execution task card and run only count-24 after
fresh canonical HEAD, registry, runtime, queue, GPU/process, candidate-pool hash,
selected-manifest, and loaded-commit proof gates pass. Do not run count-32,
broad extraction, backfill, or full ticker-universe extraction.
```
