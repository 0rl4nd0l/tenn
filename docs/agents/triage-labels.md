# Triage Labels

Generic engineering skills often use five canonical triage roles. Tenn does not
use those labels directly. Tenn's issue labels are structured by lane, mode,
risk, type, priority, and state.

Do not create Matt-style labels such as `needs-triage`, `needs-info`, or
`ready-for-agent` in Tenn. Use the existing Tenn vocabulary after live label
verification.

## Canonical Role Mapping

| Generic role | Tenn label guidance | Notes |
| --- | --- | --- |
| `needs-triage` | `state:needs-review` | Use when a maintainer or reviewer must evaluate scope, evidence, or ownership. |
| `needs-info` | `state:data-missing` plus `question` when appropriate | Use when required evidence or user/reporter input is missing. |
| `ready-for-agent` | `state:ready` plus `task:codex-ready` when explicitly agent-ready | Only use when the issue is fully specified and safe for scoped execution. |
| `ready-for-human` | `state:needs-review` | Tenn does not currently have a dedicated human-implementation label. Explain the human decision needed in the issue body or report. |
| `wontfix` | `wontfix` | Existing GitHub default label; use only with explicit closeout approval. |

## Common Tenn Label Families

- `lane:*`: primary work area, for example `lane:evaluation`,
  `lane:financial-truth`, `lane:provenance`, `lane:query-orchestration`, and
  `lane:repo-hygiene`.
- `mode:*`: work mode, for example `mode:audit`, `mode:result-review`,
  `mode:safe-extension`, and `mode:issue-closeout`.
- `risk:*`: blast-radius or uncertainty level.
- `type:*`: issue type, for example `type:docs`, `type:control-plane`,
  `type:validation-gap`, or `type:bug`.
- `state:*`: current state, for example `state:ready`, `state:running`,
  `state:blocked`, `state:data-missing`, `state:needs-review`,
  `state:needs-followup`, `state:parked`, or `state:superseded`.

## Mutation Rule

Label mutation is a GitHub write action. Do not apply or remove labels without
explicit approval for the current task. When approval exists, verify live labels
first because Tenn label vocabulary may drift.
