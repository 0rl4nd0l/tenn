# Reconciliation

## Artifact inventory

| Input | Path | Hash/status |
| --- | --- | --- |
| Codex X design workspace | `/home/l4nd0/codex-x-orchestrator-design` | present, read-only |
| Orchestration spec | `/home/l4nd0/codex-x-orchestrator-design/ORCHESTRATOR_SPEC.md` | `29fcf6399eb1c31fcb34ee538f705db43a1c51ba5d040054924f9720d4ad14a6` |
| Transition rules | `/home/l4nd0/codex-x-orchestrator-design/TRANSITIONS.md` | `56622f3e97a64cc617f04dd7fbff2506ecd9f7b2077302c3b6898818e2d8a59b` |
| Restartability rules | `/home/l4nd0/codex-x-orchestrator-design/RESTARTABILITY_TEST.md` | `b16f1cb984f1167c0f6e14b080943772f2dd1f3fa7e2916574b4e738e1ebdcea` |
| Clean-export rules | `/home/l4nd0/codex-x-orchestrator-design/CLEAN_EXPORT_GATE.md` | `72a19152b60eb4d7af53ab03e4478efe1633893df8dafeead5e166808c5de692` |
| Tenn extraction workspace | `DATA_MISSING` | `DATA_MISSING` |
| Tenn extraction spec | `DATA_MISSING` | `DATA_MISSING` |
| Tenn extraction ADRs | `DATA_MISSING` | `DATA_MISSING` |
| Tenn extraction tickets | `DATA_MISSING` | `DATA_MISSING` |

The design workspace is an orchestration contract only. It does not contain the
Tenn extraction spec, ADRs, or tickets.

## Live work boundaries

| Work | Live identity | Touched scope | Classification rule |
| --- | --- | --- | --- |
| PR #517, current-period binding | merged as `d438cb454b56b4718c5a1c4721e48831a7b107a5`; contained in canonical `2f5a8aac38cf31ecbed3bcb50420fbd5b32ec8d7` | `docling_extract.py`, `multipass_extraction.py`, focused tests | Exact matching tickets become `SUPERSEDED` or `DONE`; never reimplement |
| PR #508, NPAT owner/OCI | open draft head `4913ef0883410fcc6436b1387fa7c17642190d05`; checks green | `multipass_extraction.py`, its tests, bounded no-write cases | Exact matching tickets are `OVERLAPS_EXISTING`; do not modify without owner instruction |
| PR #513, metric authority | open draft head `12ecb02fee3eebe9fd19527bc55a444502ec26d4`; checks green | central contract registry plus production/evaluation consumers and tests | Exact matching tickets are `OVERLAPS_EXISTING`; do not modify without owner instruction |

## Ticket reconciliation

| Ticket | Hash | Status | Evidence | Blocker | Next action |
| --- | --- | --- | --- | --- | --- |
| Ticket set unavailable | `DATA_MISSING` | `DATA_MISSING` | No ticket files exist in the design workspace; bounded local and connected-document searches found no matching programme package | Exact completed extraction workspace/spec/ADR/ticket paths are absent | Supply the existing workspace root, then hash and classify every ticket against canonical and PRs #508/#513/#517 |

No ticket is `READY`. This is not a claim that all programme work is blocked;
it is a fail-closed statement that readiness cannot be assigned without the
authoritative tickets.

## Shortest safe order

No executable ticket order is authorized yet. Once the missing artifacts are
provided, the deterministic reconciliation order is:

1. Hash the spec, ADRs, and complete ordered ticket set.
2. Mark exact PR #517 behavior `SUPERSEDED`/`DONE`.
3. Mark exact PR #508 and #513 scopes `OVERLAPS_EXISTING`.
4. Mark dependency-only tickets `DEPENDS_ON`.
5. Mark evidence/source-case gaps `DATA_MISSING`.
6. Order only the remaining independent `READY` tickets by the shortest path to
   a positive source-proven scorecard delta with zero wrong/source-unbound/
   comparative-period/side-effect regression.
7. Stop if the first candidate still touches unresolved PR #508 or #513 work.

This sequence is reconciliation logic, not a rewritten extraction plan.
