# Trust Foundation Next Phase Long-run

Lane: Evaluation
Branch: `safe/trust-foundation-next-phase-longrun-v1-20260524`
Worktree: `/home/l4nd0/tenn-trust-foundation-next-phase-longrun-v1-20260524`
Execution mode: `safe_extension_with_audit_read_only_children`
Contested surfaces touched: `financial-engine_v2/backend/app/routes/cockpit_api.py`
Collision risk: `MEDIUM-HIGH`, controlled by isolated worktree, task cards, registry claim, focused tests, and no-write audit boundaries.
Decision: `proceed_completed_on_isolated_branch`

## Confirmed Facts

- Canonical `/home/l4nd0/tenn` resolves to `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`.
- Canonical branch is `migration/clean-runtime-baseline-reconstruct-v1`.
- Canonical HEAD advanced to `594df2dd19d72d8a047f581e7793204b9d873f7f` while this work ran; `a71a4fbeb447` remains an ancestor.
- This work used isolated branch `safe/trust-foundation-next-phase-longrun-v1-20260524` from `a71a4fbeb4477a3fbe25ffc27c15c9a2e09e52b8`.
- Controller and child task cards validated.
- Registry overlap check passed and final registry active jobs were `[]`.
- No Qdrant, news SQLite, memory, Postgres, canonical financial truth, parser, extraction, Docker, cron, systemd, model, GPU, or runtime topology writes were performed.

## Child Outcomes

- `recent_news_positive_claim_verified_fixture_v1_20260524`: implemented. Positive `recent_news_event` fixtures now prove deterministic recent-event evidence can verify recent-news/update claims. UI `claim_verified_source_count` is now requirement-aware after guard enrichment.
- `memory_fanout_suppression_quarantine_design_v1_20260524`: audit/design complete. Prior inventory artifacts still show 4 suspicious source-fanout clusters covering 17 active selectable entries. No live memory mutation was performed. Recommended next step is operator-reviewed exact-entry read-path quarantine, not deletion or broad source-fanout hiding.
- `a2m_news_projection_path_discovery_v1_20260524`: read-only discovery complete with `DATA_MISSING` reduced. Qdrant has 24 A2M-matching points and retrieval code is list-aware. Canonical/default SQLite paths remain absent at checked locations, so SQLite/projection parity remains missing rather than an A2M alias or ranking failure.
- `eval_spine_normalizer_usage_followup_v1_20260524`: implemented. Added `scripts/reporting/README.md`, extended the normalizer to accept the current audit artifact shape, added tests, and generated report-local sample artifacts preserving 10/24, 15/39, and 146/73/70/3 boundaries.

## DATA_MISSING

- Full source text/spans and operator preserve/suppress/expire decisions for the 17 memory fanout candidates.
- Actual `news_articles.sqlite` path if moved outside checked canonical/NVMe/HDD paths.
- Nightly fallback refresh success/failure evidence for materializing `news.sqlite`.
- SQLite-to-Qdrant row parity because the source SQLite files were absent.
- Current `confirmed_metric_coverage` extracted-payload accuracy proof; the artifact normalized here is breadth inventory only.
- Canonical merge status for this isolated branch; the branch is committed/parked for review rather than merged into the live canonical branch.

## Regressions

- Fixed: Eval Spine normalizer produced an empty sample from the current audit `summary`/`metrics` artifact shape.
- Open: memory fanout candidates remain selectable until an approved read-path quarantine guard is implemented.
- Open: A2M SQLite/projection parity remains unresolved because the configured/default SQLite files are absent.
- No focused test regressions were found.

## Validation Summary

- Backend source-label tests: `74 passed`.
- Eval Spine reporting tests: `11 passed`.
- Ruff on touched Python files: passed.
- JSON artifacts: 12 parsed successfully.
- CSV artifacts: expected row counts matched.
- Task-card validation: passed for controller and 4 child cards.
- Registry overlap: passed.
- `git diff --check`: passed.
- Controller `check-diff`: see `diff-check.json`.

## Save Recommendation

`SAVE_RECOMMENDED`: keep the isolated branch commit and review/merge it into current canonical after checking the one-commit canonical drift from `594df2dd`.

## Next Safe Prompts

- Implement operator-approved exact-entry company-memory read-path quarantine using `candidate_quarantine.json`.
- Add a read-only news runtime path health check for configured SQLite paths, nightly fallback output, Qdrant point counts, and A2M count.
- Add a Cockpit/reporting display plan for Eval Spine normalized manifests without runtime writes.
- Merge or cherry-pick the isolated branch onto current canonical after a fresh overlap and focused test pass.
