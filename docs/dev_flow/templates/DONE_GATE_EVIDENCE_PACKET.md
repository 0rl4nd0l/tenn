# Done Gate Evidence Packet

Use this compact packet before claiming a Tenn task is complete.

## Intent

- original intent:

## Task Context

- task card:
- issue:
- PR:
- branch:
- HEAD:
- mutation mode:

## Scope

- allowed_files check: `PASS | FAIL | DATA_MISSING | not applicable`
- files changed:
  - `<path>`
- forbidden surfaces:
  - product/runtime/data/extraction/DB/Qdrant/news/memory/source-PDF/gold-label/prompt/service:

## Validation

| Command | Exit | Result |
| --- | --- | --- |
| `<exact command>` | `<code>` | `<summary or raw-log path>` |

validation_result: `PASS | FAIL | DATA_MISSING`

## Evidence

- `<artifact or evidence path>`

## Risk

- risk classification: `LOW | MEDIUM | HIGH | BLOCKED | DATA_MISSING | OWNER_DECISION_REQUIRED`
- known limitations:
- unresolved blockers:
- owner decisions needed:

## Git Status

```text
<git status --short --untracked-files=all>
```

Ignored report artifacts note:

## Final Claim

final_claim: `DONE | NOT DONE | BLOCKED | DATA_MISSING | OWNER_DECISION_REQUIRED`

reason:

next safe action:

## Checklist

- [ ] Intent restated.
- [ ] Task card / issue / PR named or marked `not applicable`.
- [ ] Mutation mode recorded.
- [ ] `allowed_files` checked.
- [ ] Exact changed files listed.
- [ ] Forbidden surfaces explicitly touched/not touched.
- [ ] Validation commands and results recorded.
- [ ] Evidence artifacts listed.
- [ ] Risk, limitations, blockers, and owner decisions stated.
- [ ] Fresh git status captured.
- [ ] Next safe action is concrete.
