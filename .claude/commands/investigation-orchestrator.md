# Investigation Orchestrator

Rigorous investigation workflow for larger or more difficult fixes, debugging, diagnosis, refactors, and redesigns. Use this before implementation when the root cause is unclear, the change is high-risk, or the work crosses multiple files or subsystems.

## Instructions

Follow this sequence in order:

1. Frame the problem.
   - State the observed symptom, expected behavior, likely subsystem, and current unknowns.
   - Separate facts from assumptions.
2. Map the relevant codebase before proposing changes.
   - Read the files that define the execution path, persistence/config path, and test coverage path.
   - Cite exact file paths and symbols or line references.
   - Do not suggest fixes until the mapping is complete.
3. Split independent exploration work where possible.
   - Parallelize read-only inspection across subsystems that do not depend on each other.
4. Produce a grounded problem statement.
   - Identify the likely root cause if supported by evidence.
   - If root cause is not confirmed, narrow uncertainty to a short explicit list.
5. Write a spec before editing code.
   - Include intended behavior change, files to modify, invariants to preserve, risks, and validation steps.
   - If the spec is inconsistent or incomplete, continue investigation instead of editing.
6. Implement the smallest coherent fix.
7. Verify with the narrowest relevant tests first, then broader checks only if needed.

## Use Threshold

Use this for:

- complex bugs or regressions with unclear cause
- larger refactors or redesigns
- high-risk changes that touch multiple files, components, or interfaces

Do not use this for:

- obvious small fixes
- routine one-file edits
- minor follow-up patches after the main investigation is already done

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
    "symptom": "",
    "scope": "",
    "facts": [],
    "inferences": [],
    "key_files": [],
    "likely_root_cause": "",
    "proposed_change_spec": "",
    "validation_plan": ""
  }
}
```

If implementation happens, `files_modified` must list the edited files. If the task remains investigation-only, `files_modified` must be `[]`.

## Validation

Before returning: confirm the investigation distinguished facts from inferences; confirm every file cited was actually read; confirm code edits, if any, happened only after a coherent spec was produced; confirm the JSON is exact and valid.
