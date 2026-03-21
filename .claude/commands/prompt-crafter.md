# Prompt Crafter

Turns a task or agent outline into structured prompts following the Codex/agent prompt pattern. Can also create subagent `.md` files for `.cursor/agents/`.

## Usage

Provide:
- A **task description or agent outline** (free text).
- Optional: `"single prompt"` — skip the EXTRACT/ANALYZE/IMPLEMENT split.
- Optional: `"create agent file"` — output a ready-to-use `.cursor/agents/<name>.md`.

## Instructions

Every prompt you generate must include these sections: **SYSTEM**, **CONTEXT**, **TASK**, **INPUTS**, **REQUIREMENTS**, **OUTPUT FORMAT** (with JSON schema), **VALIDATION**.

For tasks that affect code, output **three prompts** unless "single prompt" requested:
1. **EXTRACT** — Read-only; identify relevant data/files.
2. **ANALYZE** — Determine required changes; no coding.
3. **IMPLEMENT** — Minimal targeted changes.

Each step must validate the previous step's output.

**Required output schema in every generated prompt:**
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

**Validation block** (append to every generated prompt):
- After generating your answer: confirm all requirements addressed; verify no contradictions; confirm JSON schema exact; if any fail, revise and recheck.

If "create agent file" requested: include `name` and `description` in YAML frontmatter; body = SYSTEM through VALIDATION in markdown, plus schema and validation block.

## Output Format

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
  "result": {
    "prompts": [{"name": "EXTRACT|ANALYZE|IMPLEMENT|SINGLE", "content": ""}],
    "agent_file": null
  }
}
```

Set `agent_file` to the full `.md` contents if "create agent file" was requested; otherwise `null`.

## Validation

Before returning: confirm every generated prompt has all required sections and the validation block; if code-related and not "single prompt", confirm three prompts with clear handoffs; confirm output JSON is exact and valid. If any check fails, revise and recheck.
