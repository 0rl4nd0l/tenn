# Cloud-3 Extraction-Truth Eval Evidence Report (2026-04-21)

## 1) Reproducible Run Metadata

- Worktree: `/mnt/sdb2/home/l4nd0/tenn-codex-cloud-20260421-122136/c3-extraction-truth-real-gold-eval`
- Branch: `cloud/c3-extraction-truth-real-gold-eval-20260421-122136`
- Commit SHA: `1c62c7538eda5f80fdd3939a0d0dd6519d225c81`
- Run window (UTC): up to `2026-04-21T02:53:37Z`
- Backend target: `http://127.0.0.1:8000/api/extraction-eval/real-gold`
- Canonical dataset expectation: `financial-engine_v2/data/extraction_gold_real`

Commands executed for this task:

1. `bash scripts/setup_eval_cloud.sh`
2. `financial-engine_v2/.venv/bin/python -m pytest -c pytest.ini scripts/test_run_real_extraction_eval.py -q`
3. `financial-engine_v2/.venv/bin/python scripts/run_real_extraction_eval.py --help`
4. Probe (full lane started, then runtime-bounded):
   - `financial-engine_v2/.venv/bin/python scripts/run_real_extraction_eval.py --backend-url http://127.0.0.1:8000 --results-json reports/cloud3/extraction_real_eval_results_2026-04-21.json --report-path reports/cloud3/extraction_real_eval_summary_2026-04-21.md --timeout-seconds 5400`
5. Explicit short-timeout probe for blocker capture:
   - `PYTHONUNBUFFERED=1 financial-engine_v2/.venv/bin/python scripts/run_real_extraction_eval.py --backend-url http://127.0.0.1:8000 --limit 1 --results-json reports/cloud3/extraction_real_eval_results_probe_timeout_2026-04-21.json --report-path reports/cloud3/extraction_real_eval_summary_probe_timeout_2026-04-21.md --timeout-seconds 30`

## 2) Execution Outcome and Blockers

### 2.1 Setup workflow

- `setup_eval_cloud.sh` created venv and installed requirements, then failed at validation with:
  - `/financial-engine_v2/.venv/bin/python: No module named pytest`
- Minimal unblock applied in-session:
  - `financial-engine_v2/.venv/bin/pip install pytest`

### 2.2 Required validation commands

- `scripts/test_run_real_extraction_eval.py`: **8 passed** (warning: unknown pytest config option `asyncio_default_fixture_loop_scope`).
- `scripts/run_real_extraction_eval.py --help`: **passed**.

### 2.3 Local runtime blocker (precise)

Short-timeout probe failed with explicit runtime evidence:

- `RuntimeError: backend real-gold job timed out after 30s (task_id=c96e69440ca94289b91d741ba4e57e55, last_status=running)`

Additional API status probe evidence:

- `POST /api/extraction-eval/real-gold?background=true` returned `202` with task IDs.
- Task state remained `status=running` during polling without completion in probe window.

Interpretation: endpoint is reachable and scheduling jobs, but this environment is runtime-bound for real-gold completion under current load.

## 3) Closest Reproducible Completed Subset Used for Taxonomy

Because fresh local full-run completion was blocked by runtime, taxonomy below is grounded in the latest completed canonical artifacts plus prior runtime-hardened baseline:

Primary completed artifacts:

- `/mnt/sdb2/home/l4nd0/tenn/reports/extraction_real_eval_results_canonical_repeat_run1.json`
- `/mnt/sdb2/home/l4nd0/tenn/reports/extraction_real_eval_results_canonical_repeat_run1_summary.json`
- `/mnt/sdb2/home/l4nd0/tenn/reports/extraction_real_eval_summary_canonical_repeat_run1.md`

Cross-check completed artifacts (same outcome profile):

- `/mnt/sdb2/home/l4nd0/tenn/reports/extraction_real_eval_results_canonical_default_ports_summary.json`

Baseline comparison artifacts (pre-timeout regression profile):

- `/mnt/sdb2/home/l4nd0/tenn/reports/extraction_real_eval_results_runtime_hardened_2026-04-15.json`
- `/mnt/sdb2/home/l4nd0/tenn/reports/extraction_real_eval_results_runtime_hardened_2026-04-15_summary.json`

## 4) Failure Taxonomy

## 4.1 Latest canonical completed run (`generated_at=2026-04-21T02:19:25.625557Z`)

Headline summary:

- Documents: `10`
- Metric accuracy: `25.00% (6/24)`
- Context accuracy: `40.00% (4/10)`
- Trust match: `4/10`
- Trust distribution: `trusted=4`, `quarantine=6`, `abstain=0`

Failure modes (document/context level):

| Failure mode | Count |
| --- | ---: |
| `extractor_timeout` (`docling exceeded ...`) | 6 docs |
| `context_mismatch:period_type` | 6 |
| `context_mismatch:period_end` | 6 |
| `context_mismatch:currency` | 6 |
| `context_mismatch:scale` | 6 |

Affected tickers (quarantined docs):

| Ticker | Quarantined docs |
| --- | ---: |
| `BHP` | 2 |
| `RIO` | 2 |
| `MIN` | 1 |
| `QBE` | 1 |

Metric statuses in quarantined documents:

| Metric | `quarantine` count |
| --- | ---: |
| `revenue` | 6 |
| `operating_cash_flow` | 6 |
| `net_debt` | 6 |

Interpretation: this run is dominated by parser/runtime timeout-driven quarantines rather than numeric metric mismatches.

## 4.2 Baseline comparison (`runtime_hardened_2026-04-15`)

Headline summary:

- Metric accuracy: `87.50% (21/24)`
- Context accuracy: `100%`
- Trust match: `8/10`

Residual metric failure taxonomy from that run:

| Failure mode | Count | Example document |
| --- | ---: | --- |
| `metric_revenue:wrong` | 1 | `bhp_a_2025-06-30` |
| `metric_net_debt:missing` | 1 | `bhp_a_2025-06-30` |
| `metric_net_debt:wrong` | 1 | `min_h_2025-12-31` |
| `validation_gate` (status inconsistency) | 1 | `gre_q_2025-09-30` |

Interpretation: when timeout pressure is removed/managed, the remaining high-value quality issues are concentrated in BHP/MIN metric truth and one quarterly validation-gate consistency issue.

## 5) Top 10 Fix Candidates (Ranked)

Ranking basis: expected eval gain first, then implementation risk. Items marked `Inference` are derived from artifact patterns and must be validated with tests.

| Rank | Fix candidate | Expected gain | Risk | Evidence basis |
| --- | --- | --- | --- | --- |
| 1 | Add deterministic timeout fallback from docling -> alternate parser in canonical real-gold path | Very high | Medium | 6 timeout-quarantined docs in latest canonical run |
| 2 | Pre-route heavy annual/half-year PDFs away from docling when prior runs show repeated timeout for same source file | Very high | Medium | Same BHP/RIO/MIN/QBE files repeatedly timeout |
| 3 | Persist and reuse per-document parser success manifests to skip known-failing parser path | High | Low-Med | Repeated canonical runs show identical failure profile |
| 4 | Add per-document progress heartbeat in task status payload (running->phase/page counters) | Medium (ops/debug) | Low | Tasks remain `running` with no intermediate visibility |
| 5 | Enforce bounded retries per document with explicit terminal failure reason taxonomy | Medium | Low | Current runtime failures collapse into broad timeout outcomes |
| 6 | Re-harden BHP FY25 current-period selection for `revenue` under fallback parser path | Medium | Medium | Runtime-hardened baseline shows `revenue:wrong` on BHP FY25 |
| 7 | Reconcile `net_debt` emit vs abstain rules across explicit-note/table/derived paths | Medium | Medium | Runtime-hardened baseline shows BHP missing + MIN wrong net_debt |
| 8 | Normalize quarterly validation gate so metric-correct quarterly docs are not marked failed | Low-Med | Low | `gre_q_2025-09-30` trust ok but `validation_gate` issue present |
| 9 | Add canonical lane regression test asserting no context-null quarantine on trusted fixtures after timeout fallback | Medium (prevents relapse) | Low | Canonical run quarantines trusted fixtures via context nulls |
| 10 | Make `setup_eval_cloud.sh` guarantee pytest availability (direct dependency or guarded install) | Low (workflow) | Low | Reproducibility break: setup script fails before validations |

## 6) Notes on Contract Safety

This task produced analysis/docs artifacts only. No extraction logic, evaluator rules, database writes, or vector-store behavior was changed.

