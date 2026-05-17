# Final Migration Baseline Conflict Resolution Record

- Current branch: `migration/clean-runtime-baseline-20260517`
- Final head: `6c6748fe87e57b9d3b6c890e8551e7c288bc51b0`

## Result
- Integrated required-before-migration commits: **2**
- Deferred required-before-migration commits: **3**

## Integrated commits
1. `2de6abb0448340bea1ee34450e1985e738a9419b` -> cherry-picked as `420d1181d3a5b8e873acac60fb394e9f93bcfc26`
2. `420b3b173f12446f9c801dacb0db5a927aec1d68` -> cherry-picked as `26b9b027214e5bca74d73ec2e43224a7560f16c9`

## Deferred commits
1. `c102f3f21505a01a8333b2f442dc2403cf67b509` (delete/add conflict)
2. `d147dad8ca67688d6a08b200c3a7e9fff95605ec` (blocked by dirty `docs/validation_baseline.md`)
3. `80f71c50cdff151cea014a36a865e34b1331622e` (reverted due non-allowed-file churn)

## Hard stops and blockers
- Existing dirty/untracked files outside allowed_files prevented claim and clean overlap checks.
- No further commits applied in this run to avoid contract-safe scope drift.
