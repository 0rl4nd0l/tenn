# Parked Entry: extraction-data-missing-20260604

- Status: `DATA_MISSING`
- Lane: Repo Hygiene
- Source: extraction worktree merge-parking inventory dated 2026-06-04

## Missing Paths Preserved Visibly

- `/tmp/tenn-appendix4d-profit-after-tax-alias-v1`
- `/tmp/tenn-appendix4d-contract-decision-v1`
- `/tmp/tenn-extraction-contract-restore-v1`
- `/tmp/tenn-canonical-appendix4d`
- `/tmp/tenn-appendix4d-validation`

## Related Repo-Side Signals

- `appendix4d_alias_worktree -> /tmp/tenn-appendix4d-profit-after-tax-alias-v1`
- `appendix4d_contract_decision_worktree -> /tmp/tenn-appendix4d-contract-decision-v1`

## Why Parked

These paths were registered or referenced during the audit, but they were not
present to inspect. The gap itself is part of the hygiene problem and should
remain visible until a human confirms whether the historical contents matter.

## Recommended Next Action

If historical contents are needed, recover or inspect the missing paths outside
this registry setup task. Do not infer that the newer live worktrees fully
replace the missing ones without human confirmation.
