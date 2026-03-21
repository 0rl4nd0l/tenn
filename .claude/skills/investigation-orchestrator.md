---
name: investigation-orchestrator
description: Rigorous investigation and redesign methodology — subagent-driven exploration, structured brainstorming gate, spec-before-plan discipline, and parallel research agents. Use for any fix, debug, investigation, or redesign of a non-trivial system.
trigger: fix, investigate, debug, redesign, refactor, diagnose, broken, failing, incorrect, improve accuracy
type: process
rigidity: rigid
---

# Investigation Orchestrator

This is a **rigid process skill**. Follow it exactly. Do not adapt away steps because a task feels simple. The gate before implementation is the entire point.

## When This Applies

Any task involving:
- "fix" / "broken" / "failing" on a non-trivial system
- "investigate" / "diagnose" / "find out why"
- "redesign" / "refactor" with system-wide impact
- "improve accuracy / reliability / correctness"

Simple one-file edits with obvious fixes do not require this process.

---

## Phase 1 — Explore Before Everything

**Before asking any question or proposing anything**, dispatch an Explore subagent to map the system:

```
Dispatch: Explore subagent
Task: Map [subsystem] fully — key files, classes, functions, data flows,
      known gaps, TODOs, existing tests. Report file paths and line numbers.
      Do NOT suggest fixes — only map what exists.
```

Do not proceed until the Explore agent returns. Never design from memory or assumptions.

---

## Phase 2 — Structured Brainstorming (rigid gate)

Invoke the `superpowers:brainstorming` skill. Follow it exactly, including:

### 2a. Clarifying questions — one at a time
- Multiple choice where possible
- Never batch more than one question per message
- Stop when you understand: primary pain point, success criteria, constraints, ground truth availability

### 2b. Visual companion
- Offer for architecture questions (data flow, component relationships, approach comparisons)
- Use browser for content that IS visual; terminal for text/conceptual questions
- Decide per question, not per session

### 2c. Propose exactly 3 approaches
- Trade-offs for each
- Lead with your recommendation and reasoning
- Never skip to design without proposing alternatives

### 2d. Section-by-section design approval
- Maximum 5 named sections (e.g. Architecture, Extraction Layer, Multi-pass Design, Eval Harness, Error Handling)
- Present one section at a time in the visual companion
- Get explicit "yes" before advancing to next section
- Never batch all sections at once

### Hard gate
**No code, no implementation plan, no file edits until design is approved section by section.**

---

## Phase 3 — Spec With Codebase-Grounded Review

### 3a. Write the spec
Save to `docs/superpowers/specs/YYYY-MM-DD-<topic>-design.md`. Include:
- Problem statement (root causes, not symptoms)
- Chosen approach and rationale
- Architecture overview (pipeline diagram)
- Component designs (what each does, inputs, outputs)
- Data contracts (exact shapes — verify against real code)
- Failure taxonomy (every failure mode, strategy, DB status)
- Validation gates (hard blocks vs soft warnings, with distinct named fields)
- Eval harness (ground truth format, tolerance table, regression gate)
- Test suite (what's new, what's updated, what's unchanged — be explicit)
- Files changed table (every file, status: new/replaced/modified/unchanged)
- Out of scope (explicit list)

### 3b. Dispatch a spec reviewer subagent — read the actual codebase
```
Dispatch: general-purpose subagent
Role: Spec document reviewer
Task:
  1. Read the spec at [path]
  2. Read the actual files named in the spec's "Files Changed" table
  3. Verify: completeness, internal consistency, data contract accuracy,
     dependency existence, test feasibility
  4. Return: APPROVED or ISSUES_FOUND with numbered list (critical/major/minor)
  5. Do NOT approve if critical or major issues remain
```

**The reviewer must read real files, not just the spec in isolation.** This catches:
- Data contract mismatches between old and new code
- Missing dependencies
- Guards that break when modules are deleted
- Underspecified "modified" files

### 3c. Fix and re-dispatch (max 3 iterations)
- Fix all critical and major issues
- Re-dispatch the reviewer with the same instructions
- If 3 iterations pass without approval, surface to user

### 3d. User review gate
After reviewer approves: ask user to read the committed spec before implementation planning begins.

---

## Phase 4 — Implementation Planning

Only after user approves the spec: invoke `superpowers:writing-plans`.

---

## Parallel Agent Patterns

Use parallel dispatch (multiple Agent tool calls in one message) for:
- Independent codebase exploration tasks (e.g. "map extraction" AND "map test suite" simultaneously)
- Spec reviewer + other research running concurrently
- Multiple subsystem investigations with no shared state

Never parallelize tasks with sequential dependencies.

---

## Provenance Thinking (applies to every output)

Every extracted value, claim, or design decision must trace to a source:
- Code claims → file path + line number
- Design decisions → explicit reasoning, not convention
- Metric values → row reference in the source table
- Failures → named failure mode with strategy and DB status

No silent failures. No unverifiable claims. If evidence is absent, say so.

---

## Confidence Markers

When reasoning about repo state:
- **Confirmed** — directly verified from source file
- **Inferred** — derived from pattern or context
- **Speculative** — not grounded in current evidence; flag before acting

---

## Regression Traceability (mandatory before session end)

Before ending any session that produced working changes:
1. Commit all working state as `milestone(<subsystem>): <what works>`
2. Commit all incomplete state as `wip(<subsystem>): <description>`
3. Leave working tree clean
4. Never end with uncommitted state

If a milestone cannot be verified as working, it is `wip`, not `milestone`.

---

## Anti-Patterns (do not do these)

| Temptation | Reality |
|-----------|---------|
| "I know this codebase, skip Explore" | Memory is stale. Explore runs first, always. |
| "The design is obvious, skip brainstorming" | Unexamined assumptions cause rework. |
| "I'll batch all design sections" | Section-by-section approval catches misalignment early. |
| "The spec looks right, skip the reviewer" | The reviewer catches data contract mismatches you cannot see from memory. |
| "This is just a simple fix" | Simple fixes that touch shared interfaces need the same rigor. |
| "I'll commit at the end" | Milestone commits enable `git bisect`. End-of-session commits destroy traceability. |
