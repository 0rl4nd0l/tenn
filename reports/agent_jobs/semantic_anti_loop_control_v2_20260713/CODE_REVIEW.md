# Code Review

## Initial Integrated Review

Result: changes requested and repaired.

The review reproduced and required fixes for:

- malformed contract versions downgrading V2 enforcement;
- stale exact decisions outranking newer conflicts;
- prospective entries blocking or loop-stopping unrelated offline work;
- target-repository registry configuration being ignored;
- unreadable active-job state failing open for V2;
- equivalent evidence hashes producing different fingerprints;
- contradictory decision/outcome pairs and non-JSONL live ledgers;
- V2 terminal closeout accepting a V1 board continuation goal;
- weak decision-delta sentinels and types; and
- zero process status for V2 hard-stop classifications.

The first code-fixer pass added targeted regressions. A second integrated
review then identified seven remaining fail-closed and consistency gaps:

- explicit null contract versions could still downgrade to V1;
- corrupt active-registry records could still fail open;
- closeout did not yet require a durable matching decision entry;
- old evidence-pair blockers could leak into a changed evidence pair;
- explicit cross-track dependencies could not be represented;
- missing task-card paths could return process status zero; and
- board reopen conditions did not normalize list values.

The second code-fixer pass repaired all seven findings with targeted
regressions. Final validation reported:

- combined control-plane suite: 208 passed, 13 subtests passed;
- portable guard suite: 34 passed;
- Ruff: passed; and
- `py_compile` and `git diff --check`: passed.

## Final Post-Fix Review

Result: clean. The reviewer rechecked all seven final fixes, the current diff,
the focused suites, static checks, and a secret-pattern scan. It reported no
critical, warning, or suggestion findings.

## Deferred Suggestion

The reviewer suggested a single-pass or indexed ledger search for scale. It is
deferred because it does not affect the correctness of the pilot and would
widen this remediation.
