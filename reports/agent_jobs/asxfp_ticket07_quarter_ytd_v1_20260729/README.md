# ASXFP Ticket 07 quarter-only and year-to-date observations

Status: READY FOR FINAL REVIEW

- behavioral_validation_commit:
  `38f7f2bcb23fa8d385570dd3875bc3f3596b6d47`
- behavioral_validation_tree:
  `377adce419f60e83ed9306139b3cd5eb589e5996`

- frozen_predecessor_commit:
  `ef78e5afd78601edcdf42357881d794c57a03a08`
- frozen_predecessor_tree:
  `206b7dae80d9f47d4bea887800333df83153d290`
- repair_branch:
  `codex-x/20260729T161925Z-ef78e5afd7-e826af`

- stacked_base: `f063c2a4cb4b9c677f35498de4b80f31dba55ba6`
- stacked_tree: `fb4017c006650a27de517461be9b3e1221a4f52c`
- canonical_ancestor: `b01885d6cd55242339662e91d18141aeb725f089`
- authoritative_ticket_sha256:
  `6c3630e469e58e5b7974bc687fa63ca3be8935d6a8b1a4cf049896098044d488`
- protected_corpus_access: prohibited
- tier_2_actions: not authorized
- merge_allowed: false
- implementer_predecessor_commit:
  `b3b1a52657c05539762f810a92ce245e3ad83f3b`
- implementer_predecessor_tree:
  `88f7f7f0946b800da3ac1608b730fb8f06ffcbac`
- branch: `codex-x/20260729T154855Z-b3b1a52657-63fa28`

## Objective

Preserve distinct source-bound `period_only` and `year_to_date` immutable
observations from one quarterly announcement, reject comparative/date
masquerading, and expose both through an additive profile read without changing
legacy rows.

## Implementer evidence

Preflight:

- exact HEAD and tree matched the implementer predecessor above;
- tracked state was clean; launcher-owned control artifacts were untracked;
- stacked base ancestry check exited 0;
- the committed stacked-base-to-HEAD path set contained only the task card and
  allowlisted goal/report files;
- the task card records the authoritative ticket digest above and
  `agent_job_contract.py validate` returned `ok: true` with no issues;
- the referenced `.scratch` authoritative issue was absent from this
  worktree, so its digest could not be independently recomputed.

RED:

- tests were added first at the existing public staging and profile-read
  seams for two bases in one document, distinct IDs, sibling isolation,
  column binding, comparative/prior/date rejection, migration/ORM alignment,
  additive deterministic reads, and legacy compatibility.

Validated GREEN/static evidence:

- the controller ran the focused suite with `uv run`, supplying `pytest`,
  `pytest-asyncio`, `SQLAlchemy==2.0.36`, `pydantic` 2.x, and
  `python-dateutil`, against
  `financial-engine_v2/backend/tests/test_financial_observations.py`; it
  returned `45 passed`;
- the controller ran the adjacent contract suite with `uv run`, also supplying
  `pydantic-settings`, against
  `test_financial_metric_contract.py` and `test_asx_extraction_contracts.py`
  while excluding
  `existing_callers_export_registry_compatibility_names`; it returned
  `14 passed, 1 deselected`;
- controller-run `python3 -m py_compile` passed for the changed service and
  focused test;
- controller-run `uvx --from ruff==0.15.6 ruff check` passed for the changed
  service and focused test;
- controller-run `git diff --check` passed.

These commands were run by the controller against the exact behavioral
validation commit/tree recorded above. They were not executed by this offline
report worker.

## Candidate behavior

The candidate adds explicit independent `period_observations` members,
closed `period_only`/`year_to_date` bases, basis-bound current-quarter/YTD
source cells, strict source-text scope/end evidence, independent metric/member
abstention, distinct UUIDv5 identities, a forward-only 0012 constraint
expansion with matching ORM metadata, and deterministic sparse
`observation_only` `/financials` rows. Legacy `Q`/`H`/`A`, single-period,
Ticket 05 revenue alias, Ticket 06 ten-metric, conflict-safe insert, immutable
provenance, and caller-owned transaction behavior remain supported.

## Final repair evidence

The final reviewer findings are repaired in behavioral validation commit
`38f7f2bcb23fa8d385570dd3875bc3f3596b6d47`, tree
`377adce419f60e83ed9306139b3cd5eb589e5996`:

- ambiguous slash dates fail closed, while unambiguous D/M/Y and M/D/Y dates
  remain supported;
- new `period_observations` evaluate the entire hits collection unanimously
  and reject metadata, announcement, comparative, and malformed siblings,
  while legacy observations retain seed-era existential `source_text`
  tolerance;
- explicit announcement, lodgement, release, publication, and report date
  labels are rejected anywhere in new-member quotes, while legitimate
  reporting-period wording remains accepted.

The controller-run focused, adjacent, compile, Ruff, and diff checks recorded
above validate these repairs against that exact code commit/tree. This worker
only repairs the evidence report and does not claim to have executed those
commands. Its report-only/evidence-only changes alter no product blob.

## Closeout boundary

No PDF/protected corpus, holdout, runtime, extraction, OCR, model, evaluation,
database, migration execution, service, queue, Qdrant, GPU, production data,
publication, push, merge, activation, or deployment action occurred.

The eventual report-only containing commit changes no product blob. Therefore
the exact code commit/tree recorded as the behavioral validation anchor above,
not a recursive hash of this report's containing commit, is the authoritative
anchor for the controller-run validation evidence.
