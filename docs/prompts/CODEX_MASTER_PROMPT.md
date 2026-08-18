# CODEX MASTER PROMPT — Tenn / financial-engine_v2

Reference-only status: this is a historical prompt template, not the current
authority for all agent work. Start with `AGENTS.md`, the active task card, and
`docs/README.md`. Use `SYSTEM_CONTRACT.md` as required policy only for product
architecture, runtime behavior, extraction, RAG, financial truth, model routing,
or data-integrity work.

This file was originally written as a broad prompt template. It is now retained
as reference material for older agent flows and must not override current repo
instructions.

---

## SYSTEM CONTRACT ENFORCEMENT (NON-NEGOTIABLE)

**[docs/architecture/SYSTEM_CONTRACT.md](../architecture/SYSTEM_CONTRACT.md) is the authoritative system specification.**

### Enforcement Rules

1. **All actions MUST comply with SYSTEM_CONTRACT.md.** No exceptions.
2. **If any instruction conflicts with the contract: STOP immediately.** Surface the violation and request clarification.
3. **Do NOT introduce:** fallbacks, substitutions, parallel implementations, or approximations that violate contract invariants.
4. **Do NOT bypass:** the canonical pipeline (`backend/app/services/pipeline_service.py`), single-source-of-truth rules, or fail-fast extraction behavior.

### Pre-Flight Check (REQUIRED before implementation)

Before implementing any change, state:

1. **Target system layer** — which of the 5 pipeline layers (SYSTEM_CONTRACT §2) does this change touch?
2. **Relevant contract rules** — which specific sections (§1–§11) govern this change?
3. **What must NOT change** — which invariants (§3) must be preserved?
4. **Why this change is safe** — how does it comply with the contract?

If you cannot answer all four: **STOP. Do not proceed.**

## MULTI-AGENT LIVE REPO CONTROL

Before implementation, follow the canonical shared policy in [AGENTS.md](../../AGENTS.md#multi-agent-live-repo-control). The repo may be live with Gemini, Codex, Claude, or other sessions active; do not treat HEAD drift as inherently bad except for fixed-baseline preservation, cleanup, checkpoint, reset, stash, branch restore, or reproducibility-validation tasks.

Every implementation-capable agent must declare lane, branch, worktree, execution mode, intended files, contested surfaces touched, collision risk, and decision before editing, then list files actually touched in the final report. If unresolved HIGH overlap risk exists, stop in BLOCKED MODE and output report only.

---

## SUBAGENT ORCHESTRATION PATTERN

Subagent use must comply with [AGENTS.md](../../AGENTS.md#multi-agent-live-repo-control): subagents may be used only for parallel repo inspection, documentation gathering, or evidence collection. The parent agent owns the final decision, implementation, validation report, and conflict reconciliation.

### SUBAGENT — CONTRACT ENFORCER (mandatory for all multi-step tasks)

Purpose: Validate planned changes against SYSTEM_CONTRACT.md before execution.

1. Read `docs/architecture/SYSTEM_CONTRACT.md`
2. For each planned change, check:
   - Does it touch a forbidden path? (§3.3, §5.2)
   - Does it introduce a fallback? (§3.4, §3.6)
   - Does it modify multiple layers? (§7.2)
   - Does it bypass the canonical pipeline? (§3.3)
3. If any violation detected: **STOP execution immediately**
4. Output: `PASS` (with rationale) or `VIOLATION` (with specific section reference)

### SUBAGENT — EVIDENCE COLLECTOR

Purpose: Inspect files, gather documentation, or collect validation evidence for the parent agent.

- Do not implement changes.
- Do not create competing Tenn architecture proposals.
- Do not take ownership of contested runtime surfaces.
- Return findings with file paths, commands, and confidence markers for parent reconciliation.

---

## FAIL-FAST RULES

| Condition | Action |
|-----------|--------|
| Contract violation detected | **STOP immediately** — surface violation, do not proceed |
| Instruction conflicts with contract | **Contract wins** — surface conflict, request clarification |
| Cannot determine target layer | **STOP** — request clarification before acting |
| Change would touch >1 pipeline layer | **STOP** — split into separate changes |
| Change would introduce a fallback | **STOP** — fallbacks are forbidden (§3.4, §3.6) |

---

## NO FALLBACK RULES

These patterns are **explicitly forbidden** by SYSTEM_CONTRACT.md:

- Returning default/empty values when real values cannot be extracted (§3.4)
- Adding `try/except` wrappers without fixing the root cause
- Creating parallel implementations of existing services (§3.3, §4.4)
- Substituting one metric for another (§3.5)
- Silently degrading functionality (§3.6)
- Using `worker/app/tasks.py` (deprecated — §5.2)
- Direct Qdrant access outside the service layer (§4.4)
- Random/UUID vector IDs (§3.2)

---

## VALIDATION PHASE

After any change:

```bash
# Lint
python -m ruff check autodev financial-engine_v2/backend scripts

# Tests
pytest autodev/tests
pytest financial-engine_v2/backend/tests
pytest scripts
```

For extraction/RAG changes, also run:
- Extraction eval fixtures
- RAG stability harness
- Canonical regression baseline

---

## REFERENCE

| Document | Purpose |
|----------|---------|
| [SYSTEM_CONTRACT.md](../architecture/SYSTEM_CONTRACT.md) | **Authoritative system specification** |
| [CLAUDE.md](../../CLAUDE.md) | Agent operating instructions |
| [AGENTS.md](../../AGENTS.md) | Codex agent skills and project context |
| [docs/architecture/00_README.md](../architecture/00_README.md) | Architecture index |
| [docs/entrypoints.md](../entrypoints.md) | Canonical boot sequence |
| [docs/validation_baseline.md](../validation_baseline.md) | 10-step validation |
