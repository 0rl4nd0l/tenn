# Code Review

Status: CLEAN after actionable findings repaired

The bounded review identified two cross-repository enforcement defects:

- Canonical identity was derived from the Tenn fallback instead of the selected
  target upstream/base.
- Greyhound's Stop hook could not enforce a claimed V2 run without an explicit
  environment or marker selector.

The final follow-up also rejects self-published topic refs as canonical, binds
automatic selection to the claimed task-card hash, and fails closed on
unscoped registry corruption. Explicit environment and marker selection now
uses active-claim/hash authority on every hook event before selected-card
metadata is trusted, and partial V2-like records with unscopable worktrees fail
closed. The selector also inspects every readable non-stale target-worktree
card before treating its record as V1: an unchanged V2 card remains authority
even if version, fingerprint, and all semantic identity fields are stripped.
The same card bytes drive version detection and hash verification. Unchanged
and missing-card V1 records remain silent. Card authority is inspected before
discarding an unscopable record, closing the combined stripped-identity plus
missing/invalid-worktree bypass while preserving readable V1 silence. A
missing or corrupt `task_card_sha256` cannot discard V2 authority declared by
the card; it is an additional record defect.
Portable discovery now prefers the stable
`~/tenn-semantic-anti-loop-v2-canonical` root before scanning arbitrary
alphabetic `~/tenn-*` worktrees and still falls through when it is absent. No
ledger append, publication, runtime, data, service, timer, or registry-pointer
mutation was performed by this repair; bounded publication is authorized only
after the remaining gates pass.

The final independent adversarial review reported no remaining critical,
warning, or suggestion findings. It rechecked card drift, V2-to-V1 downgrade,
partial and fully stripped active records, missing or invalid worktree and card
hash fields, stale-named corrupt records, genuine V1 compatibility, and stable
control-plane discovery.
