# Codex Cloud Queue - 2026-04-21

## Purpose

Prepare five scoped Codex Cloud work items with explicit ownership, branch naming, validation gates, and acceptance criteria.

## Contract Preflight

- Target layer: Ops/docs/task orchestration only (no ingestion, extraction logic, storage schema, retrieval logic, or cockpit runtime behavior changes).
- Relevant contract rules: `docs/architecture/SYSTEM_CONTRACT.md` sections 1, 2, 3, and 4 (authority, layer boundaries, extraction/data invariants).
- Must not change: backend authority, retrieval boundaries, extraction truth rules, vector/data invariants.
- Safety: this queue setup creates task briefs and branch/worktree scaffolding only; no production codepaths or data stores are modified.

## Execution Board

Queue root: `/mnt/sdb2/home/l4nd0/tenn-codex-cloud-20260421-122136`

| Task | Owner | Branch | Worktree Path | Estimated Runtime | Success Criteria | Brief |
|---|---|---|---|---|---|
| Cloud-1 extraction-quality gap audit | Analysis | `cloud/c1-extraction-quality-gap-audit-20260421-122136` | `/mnt/sdb2/home/l4nd0/tenn-codex-cloud-20260421-122136/c1-extraction-quality-gap-audit` | 2-4h | Ranked root-cause findings for `shares_outstanding` gaps with patch-ready plan and touched-file list | [cloud-1](./cloud-briefs/2026-04-21-cloud-1-extraction-quality-gap-audit.md) |
| Cloud-2 cockpit-routing regression tests | Testing | `cloud/c2-cockpit-routing-regression-tests-20260421-122136` | `/mnt/sdb2/home/l4nd0/tenn-codex-cloud-20260421-122136/c2-cockpit-routing-regression-tests` | 2-3h | Added/updated routing regression tests pass in focused lane | [cloud-2](./cloud-briefs/2026-04-21-cloud-2-cockpit-routing-regression-tests.md) |
| Cloud-3 extraction-truth real-gold eval pass | Eval | `cloud/c3-extraction-truth-real-gold-eval-20260421-122136` | `/mnt/sdb2/home/l4nd0/tenn-codex-cloud-20260421-122136/c3-extraction-truth-real-gold-eval` | 2-5h | Reproducible evaluation artifact plus ranked failure taxonomy and top fix candidates | [cloud-3](./cloud-briefs/2026-04-21-cloud-3-extraction-truth-real-gold-eval.md) |
| Cloud-4 system-contract conformance matrix update | Docs | `cloud/c4-system-contract-conformance-matrix-20260421-122136` | `/mnt/sdb2/home/l4nd0/tenn-codex-cloud-20260421-122136/c4-system-contract-conformance-matrix` | 1-2h | Updated conformance matrix with explicit invariant-risk list and evidence links | [cloud-4](./cloud-briefs/2026-04-21-cloud-4-system-contract-conformance-matrix.md) |
| Cloud-5 multipass extraction performance profile | Performance | `cloud/c5-multipass-extraction-performance-profile-20260421-122136` | `/mnt/sdb2/home/l4nd0/tenn-codex-cloud-20260421-122136/c5-multipass-extraction-performance-profile` | 2-4h | Benchmark table, hotspot breakdown, and low-risk optimization plan with validation approach | [cloud-5](./cloud-briefs/2026-04-21-cloud-5-multipass-performance-profile.md) |

## Setup Commands

From repo root:

```bash
bash scripts/setup_codex_cloud_queue.sh --dry-run
bash scripts/setup_codex_cloud_queue.sh
```

After setup, for each created worktree:

```bash
cd <worktree_path>
git push -u origin <branch_name>
git rev-parse HEAD
```

Use each brief file in this folder as the Cloud handoff prompt body.
