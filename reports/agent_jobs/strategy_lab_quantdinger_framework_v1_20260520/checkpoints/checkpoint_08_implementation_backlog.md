# M8 - Follow-On Implementation Backlog

Primary output: `task_card_outlines.md`.

## Backlog Verdict

Recommended next safe phase: Phase 0 fit audit.

Do not proceed directly to implementation, UI, runtime, MCP, Docker, paper trading, or live execution. The next task should stay audit/design-only and may inspect QuantDinger source/API schemas without running services.

## Phase Summary

| Phase | Name | Mode | Proceed? |
| --- | --- | --- | --- |
| 0 | Fit audit | audit_only | yes |
| 1 | Isolated sandbox | audit_only / safe_extension | after Phase 0 |
| 2 | Artifact store/schema | safe_extension | after schema approval |
| 3 | Safe adapter/MCP client wrapper | safe_extension | after sandbox proof |
| 4 | Chat-first workflows | safe_extension | after adapter |
| 5 | Strategy Lab tab | safe_extension | after artifacts/review queue |
| 6 | Robustness engine | safe_extension | after backtest corpus |
| 7 | Factor Lab | safe_extension | after factor schema |
| 8 | Risk reports | safe_extension | after risk schema |
| 9 | Portfolio Lab | safe_extension | after local_personal_data guard |
| 10 | Autonomous research loops | safe_extension | after review queue |
| 11 | Paper-execution review only | blocked/audit_only | separate explicit approval |
| 12 | Live execution | blocked | separate project |

## Hard Sequence Gates

- Phase 0 must prove safe fit before any install/runtime.
- Phase 1 must be isolated and non-production.
- Phase 2 must land schema/storage before adapters.
- Phase 3 must be Tenn-owned and policy-gated.
- Phase 4/5 must not create UI shortcuts to sidecar controls.
- Phase 10 must not run without review queue and no-trade regression gates.
- Phase 11 is review only.
- Phase 12 is rejected from this framework.

## DATA_MISSING

- No future task cards were created outside this report.
- No permanent docs path was written.
