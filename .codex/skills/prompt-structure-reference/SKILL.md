---
name: prompt-structure-reference
description: Reference the structured prompt schema and chaining pattern used in this repo. Use when creating or validating prompts, agents, or staged EXTRACT/ANALYZE/IMPLEMENT workflows.
---

# Prompt Structure Reference

Use this skill as a reference, not an implementation workflow.

## Mandatory Prompt Sections

- `SYSTEM`
- `CONTEXT`
- `TASK`
- `INPUTS`
- `REQUIREMENTS`
- `OUTPUT FORMAT`
- `VALIDATION`

## Required Output Schema

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

## Chaining Pattern

For code-affecting tasks:

1. `EXTRACT`
2. `ANALYZE`
3. `IMPLEMENT`

Each stage should validate the previous stage's output.

## Validation Block

Append checks that confirm:

- all requirements addressed
- no contradictions
- exact JSON schema
- revise and recheck on failure
