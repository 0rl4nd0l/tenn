---
name: prompt-crafter
description: Turn a task outline into structured SYSTEM/CONTEXT/TASK/INPUTS/REQUIREMENTS/OUTPUT FORMAT/VALIDATION prompts, optionally as EXTRACT/ANALYZE/IMPLEMENT or a ready-to-use agent markdown file.
---

# Prompt Crafter

Use this skill to generate structured prompts or agent files.

## Inputs

- Task description or agent outline
- Optional `single prompt`
- Optional `create agent file`

## Workflow

1. Generate prompts with these sections:
   - `SYSTEM`
   - `CONTEXT`
   - `TASK`
   - `INPUTS`
   - `REQUIREMENTS`
   - `OUTPUT FORMAT`
   - `VALIDATION`
2. For code-affecting tasks, default to three prompts:
   - `EXTRACT`
   - `ANALYZE`
   - `IMPLEMENT`
3. Include the required JSON schema in every prompt.
4. If requested, emit a ready-to-save markdown agent file with YAML frontmatter.

## Output

Prepare structured prompt artifacts with:

- `status`
- `work_log`
- `result.prompts`
- `result.agent_file`

Default user-facing output should be normal prose plus prompt blocks or agent content as needed. Only emit raw JSON if the user explicitly asks for JSON.

## Constraints

- Every generated prompt must contain the validation block.
- If not using `single prompt`, the three-stage handoff must be explicit.
