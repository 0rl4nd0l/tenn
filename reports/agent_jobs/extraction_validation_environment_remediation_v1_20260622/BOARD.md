# Tenn Review Board: Extraction Validation Environment Remediation

## Evidence Inspected

- Current branch: `safe/extraction-metric-improvement-sprint-v1-20260622`.
- Current HEAD before remediation: `69641812e5cce58ffbd25807fa5b214e12930df5`.
- Registry: no active jobs before claim.
- Ledger: committed ledger exists; live ledger `DATA_MISSING`.
- Existing PR: draft PR #384 is the active branch to update.
- Sprint evidence: focused pytest was unavailable; full guard replay hung in a
  local LLM request; full WHC/EDU replay hung in Docling extraction.
- Prior guidance: validation-environment autonomy allows ephemeral validation
  dependencies when repo/runtime environments lack standard test tools.

## Perspectives

### Architect

Finding: the root problem is a missing validation-control-plane entrypoint, not
JAY extraction behavior. Agents had to improvise pytest execution and replay
timeout policy.

Risk: putting pytest into runtime requirements would pollute production-style
envs and still not bound Docling/LLM hangs.

Recommended action: add a repo-native pytest fallback runner and a bounded
case timeout in the no-write replay runner.

### Skeptic / Red Team

Finding: an automatic timeout can hide slow-but-legitimate replay behavior if
it is treated as success.

Uncertainty: local model latency varies across hosts.

Recommended action: timeout must be configurable, appear in artifacts, and
derive `DATA_MISSING` rather than `PASS`.

### Product / Value

Finding: the user needs future agents to complete the validation story or fail
early with precise evidence. A helper command provides more value than another
report-only warning.

Recommended action: update the open draft PR so the remediation lands with the
JAY fix that exposed the problem.

### Validation / Test

Finding: pytest absence and replay hangs are both validation-surface failures.
The fix needs direct unit coverage plus at least one live invocation of the
fallback pytest command.

Recommended action: test the helper with stdlib tests, run the helper against
its own pytest file, and extend replay runner unit tests for timeout
classification.

### Repo Hygiene / Git Guard

Finding: task-card validation and registry overlap are clean. Live ledger is
missing, so fallback duplicate search is required and was clean for this exact
implementation.

Recommended action: proceed within the new task card and update PR #384.

### Domain Context

Finding: for Financial Truth extraction, failed validation must not become a
product pass. Infrastructure/runtime uncertainty should stay `DATA_MISSING`.

Recommended action: case timeout should contribute to infrastructure failure
count and make the replay aggregate `DATA_MISSING`.

## Chair Decision

Decision: `proceed`.

Rationale: the real root problem is validation tooling fragility. The selected
change is narrow, reportable, and avoids mutating runtime venvs, dependency
lockfiles, production data, or extraction semantics.
