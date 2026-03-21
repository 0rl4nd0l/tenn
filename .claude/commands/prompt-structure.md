# Prompt Structure Reference

Reference for structured prompt and chaining patterns used across agents in this repo.

## Mandatory sections in every prompt

| Section | Purpose |
|---------|---------|
| **SYSTEM** | Rules and constraints; no chain-of-thought; use audit log |
| **CONTEXT** | Component + repository context |
| **TASK** | One clear objective |
| **INPUTS** | Exact available artifacts (files, logs, tables) |
| **REQUIREMENTS** | Explicit technical criteria |
| **OUTPUT FORMAT** | Strict JSON schema (see below) |
| **VALIDATION** | Checks to run before returning |

## Required output schema (minimum)

```json
{
  "status": "SUCCESS | DATA_MISSING | ERROR",
  "work_log": {
    "assumptions": [],
    "sources_used": [],
    "files_read": [],
    "files_modified": [],
    "validation_checks": []
  },
  "result": {}
}
```

No chain-of-thought — use the audit log instead of reasoning prose.

## Prompt chaining (when task affects code)

Output three prompts unless a single prompt is requested:

1. **EXTRACT** — Read-only; identify relevant data/files.
2. **ANALYZE** — Determine required changes; no coding.
3. **IMPLEMENT** — Minimal targeted changes.

Each step must validate the previous step's output.

## Validation block (append to every prompt)

- After generating your answer: confirm all requirements addressed.
- Verify no contradictions.
- Confirm JSON schema exact.
- If any fail, revise and recheck.

## Feature analysis → fix workflow

1. Run `/function-quality` with the feature name. Returns `critical`, `warnings`, `suggestions` with `file`, `location`, `issue`, `fix_example`.
2. Pass result to `/code-fix`. It applies critical → warnings → suggestions and suggests tests.
