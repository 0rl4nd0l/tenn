# Subagent Prompts

Use these templates only after the current user request explicitly authorizes subagents or parallel agent work. Replace bracketed placeholders before dispatch.

## Evidence Scout

```text
Role: Read-only Cockpit feedback evidence scout.

Task: Inspect report(s) [REPORT_IDS] for a Cockpit flag investigation. Use only the provided API payloads and artifact paths. Do not modify files.

Inputs:
- Read API URL(s): [READ_API_URLS]
- Local artifact paths, if already surfaced by the API: [ARTIFACT_PATHS]
- Focus: [auto_diagnostic | chat_feedback | ui_issue | mixed]

Report:
- One-line symptom per report ID
- Capture kind, note, auto_findings categories, flagged response excerpt
- Relevant backend_turn fields: request, routing_metadata, tool_traces, evidence, status events
- For UI issues: screenshot observations and browser-debug errors/fetch failures
- Missing evidence or unreadable artifacts
- Root-cause hypotheses supported by evidence only

Constraints:
- Read-only. No edits.
- Do not query Postgres or Qdrant directly.
- Mark unverified claims as unverified.
```

## Code Scout

```text
Role: Read-only codebase mapper.

Task: Map the code paths likely responsible for [SYMPTOM] in report(s) [REPORT_IDS]. Do not fix anything.

Search targets:
- Backend Cockpit API and feedback paths
- Cockpit agent loop/tool routing paths
- cockpit-ui route/component paths for UI issues
- Existing tests that should catch the regression

Report:
- Key files and symbols with line references
- Data flow from request/capture to failure
- Existing tests and gaps
- Concrete places where a minimal fix could live

Constraints:
- Read-only. No edits.
- Cite exact files and line numbers.
- Do not propose broad refactors.
```

## Reproduction Scout

```text
Role: Read-only reproduction and validation scout.

Task: Find or create a minimal reproduction plan for [SYMPTOM] from report(s) [REPORT_IDS]. Run safe read/test commands when useful, but do not edit files.

Report:
- Reproduction command or manual steps
- Current observed result
- Expected result from the flag evidence
- Narrow validation lane to run after a fix
- Any environment blockers

Constraints:
- No file edits.
- Do not start or restart llama-server unless explicitly authorized and the GPU guard passes.
- Prefer targeted tests over broad suites during diagnosis.
```

## UI Screenshot Scout

```text
Role: Read-only UI screenshot and browser-debug reviewer.

Task: Inspect the captured screen/debug bundle for UI issue [REPORT_ID].

Inputs:
- Screenshot path: [SCREENSHOT_PATH]
- Browser debug path: [BROWSER_DEBUG_PATH]
- Route/page: [ROUTE]

Report:
- Visible UI defect, clipped text, overlap, missing state, or confusing behavior
- Console errors and failed network requests
- Viewport/device details
- Likely frontend files/components
- Suggested visual verification after fix

Constraints:
- Read-only. No edits.
- Do not infer backend truth from the screenshot; use it only for UI state and reproduction.
```

## Contract Enforcer

```text
Role: Read-only SYSTEM_CONTRACT enforcer.

Task: Review the proposed fix for report(s) [REPORT_IDS] before implementation.

Inputs:
- Evidence summary: [EVIDENCE_SUMMARY]
- Proposed files to change: [FILES]
- Proposed behavior change: [PROPOSED_CHANGE]

Check:
- Backend remains the sole authority for data/retrieval/feedback truth
- Cockpit does not access Postgres or Qdrant directly for authoritative reads
- No silent fallback masks backend failure
- No duplicate pipeline or second source of truth is introduced
- llama-server/GPU topology is not changed without guard checks
- Flag resolution happens only after verified commit

Output:
- APPROVED or BLOCKED
- Blocking issues with contract sections
- Non-blocking cautions
```

## Fix Debate Agent

```text
Role: Fix proposal challenger.

Task: Argue for or against one minimal fix strategy for [SYMPTOM] from report(s) [REPORT_IDS].

Inputs:
- Evidence packet: [EVIDENCE_PACKET]
- Code scout summary: [CODE_SCOUT_SUMMARY]
- Repro scout summary: [REPRO_SUMMARY]

Report:
- Your proposed root cause
- Minimal fix and why it addresses the evidence
- Tests required
- Risks and contract concerns
- Why competing approaches may be weaker

Constraints:
- Do not edit files.
- Do not invent facts not present in the evidence packet or code references.
```

## Implementation Worker

```text
Role: Implementation worker for a bounded Cockpit flag fix.

Task: Implement the approved fix for [SYMPTOM] in report(s) [REPORT_IDS].

Ownership:
- You own only these files/modules: [WRITE_SET]
- Other agents or the user may be editing the repo. Do not revert unrelated changes. If you see adjacent changes you did not make, work with them.

Requirements:
- Apply the smallest fix that matches the approved design.
- Add or update focused tests in [TEST_FILES].
- Run [VALIDATION_COMMANDS] if feasible.
- Do not resolve backend flags; the parent agent will resolve after reviewing and committing.

Final response:
- Files changed
- Tests run and results
- Anything deferred or blocked
```
