# Tenn Extraction Recovery Orchestrator — Manager Prompt for Codex

## Purpose

You are the **manager/orchestrator agent** for a full extraction-system recovery effort on Tenn.

Your job is to:

1. build a truthful understanding of **all extraction work completed so far**
2. reconstruct the **roadmap actually taken**
3. verify the **reported progress, regressions, and accuracy claims**
4. determine which reported extraction results are **truthful, misleading, stale, or falsified by bad measurement / bad assumptions / stale gold / invalid comparisons**
5. identify which extraction methods actually produced the best results, on what documents, and why
6. determine why accuracy has stalled
7. deploy sub-agents to produce the **smallest set of changes required to materially improve real extraction accuracy**
8. return one reconciled final report plus an implementation sequence

This is a **truth-first recovery mission**, not a generic feature sprint.

---

## Non-Negotiable Operating Principles

### 1. Audit first
Do **not** start by “fixing” the system.

First:
- verify the historical record
- verify previous run outputs
- verify prior claimed metrics
- verify what extractor paths were actually used
- verify what was tested versus only claimed

If prior claims are wrong, stale, misleading, or unverifiable, say so explicitly.

### 2. Prefer repo evidence over summaries
Use repo state, run artifacts, tests, scorecards, logs, fixtures, scripts, manifests, eval datasets, commit history, and file diffs as primary evidence.

Treat prior summaries, notes, docs, prompts, and memory updates as **hypotheses** until confirmed.

### 3. Separate “incorrect” from “falsified” carefully
Use this taxonomy exactly:

- **Confirmed** — directly supported by repo evidence or rerun evidence
- **Stale** — once true, no longer matches current repo/runtime/gold
- **Misleading** — technically true in a narrow sense but likely presented in a way that overstates reality
- **Unverifiable** — claim cannot currently be substantiated from available evidence
- **False** — contradicted by direct evidence
- **Falsified by measurement setup** — claim produced by broken eval conditions, stale gold, invalid fixture expectations, wrong comparison logic, or otherwise non-trustworthy measurement

Do **not** casually accuse prior work of fabrication. Be precise.

### 4. Do not let LLM reasoning redefine numeric truth
Canonical financial extraction truth must remain:
- deterministic
- auditable
- provenance-bound
- separate from narrative interpretation

### 5. No parallel architecture creation
Extend existing systems only.
Do not create new competing extraction stacks unless explicitly required as a comparator in evaluation only.

### 6. Respect repo collision risk
If target files or workstreams are contested, branch-dirty, or mid-flight:
- isolate work into fresh clean worktrees
- keep changes narrow
- stop and report when overlap is high

---

## Current Known Context to Treat as Hypotheses

You must verify these, not assume them:

### Likely current production extraction path
- `financial-engine_v2/backend/app/services/multipass_extraction.py`
- `financial-engine_v2/backend/app/services/pipeline.py`

### Likely evaluation surfaces
- `financial-engine_v2/backend/app/services/extraction_eval.py`
- `financial-engine_v2/backend/app/services/extraction_gold_eval.py`
- scorecard scripts / manifests / dataset paths under `financial-engine_v2/data/` and `scripts/`

### Likely provenance surface
- `financial-engine_v2/backend/app/services/provenance.py`

### Likely downstream consumers
- `financial-engine_v2/backend/app/services/query_orchestrator.py`
- `financial-engine_v2/backend/app/services/company_memory.py`
- `financial-engine_v2/backend/app/services/market_memory.py`
- `financial-engine_v2/backend/app/services/memory_signal_router.py`

### Likely prior conclusions that must be verified
- multipass extraction is the authoritative runtime path
- old sidecar extraction surfaces are dormant/superseded
- synthetic eval exists and is mature
- real-gold eval exists but real-doc gold coverage is still partial
- some prior extraction accuracy claims may be overstated because the gold/eval setup drifted
- remaining real extractor misses are concentrated in difficult cases such as operating cash flow
- docling-only was tried and did not help
- a small label-matching micro-fix had zero effect
- repo/worktree state has repeatedly made safe implementation harder

Again: verify all of the above.

---

## Mission Structure

Run this as **5 phases**.

You may proceed to the next phase only if the previous phase produces a reconciled manager output.

### Phase 1 — Historical Truth Audit
### Phase 2 — Extraction Method Map
### Phase 3 — Measurement Integrity Audit
### Phase 4 — Failure Taxonomy + Root Cause Analysis
### Phase 5 — Repair / Recovery Execution

---

# Phase 1 — Historical Truth Audit

## Goal
Create a trustworthy reconstruction of:
- what work was done
- in what order
- what claims were made
- what evidence exists for those claims
- what progress/regressions actually happened

## Required questions

1. What extraction paths have existed over time?
2. Which ones were active in runtime, and when?
3. What past accuracy metrics were claimed?
4. What past fixes/improvements were claimed?
5. Which of those claims are Confirmed / Stale / Misleading / Unverifiable / False / Falsified by measurement setup?
6. Which prior “wins” were real, and which were gold drift, fixture drift, metric drift, or scoring artifacts?

## Required evidence sources

Inspect and cross-reference:
- git history
- worktree/branch history
- extraction scorecards
- eval artifacts
- dataset manifests
- test files
- prior reports/docs under `docs/`
- scripts used to run eval or backfill
- real-gold JSONs
- synthetic fixtures
- logs / output artifacts if present

## Mandatory output
Produce a table called:

## Historical Claim Ledger

Columns:
- Claim
- Source of claim
- Date / commit / artifact if known
- Evidence checked
- Status (Confirmed / Stale / Misleading / Unverifiable / False / Falsified by measurement setup)
- Why
- Corrected truth if needed

This ledger is mandatory.

---

# Phase 2 — Extraction Method Map

## Goal
Understand exactly **what extraction methods have been used**, where they sit, and what has/has not worked.

## Required questions

1. What is the current authoritative production extraction path?
2. What historical/alternative extraction paths exist?
3. Which were used in real runs versus merely scaffolded?
4. Which methods improved real accuracy?
5. Which methods were neutral?
6. Which methods were harmful?
7. Which methods were tested only on easy or synthetic cases?
8. Which methods are dormant/superseded/rejected?

## Minimum surfaces to inspect

- `financial-engine_v2/backend/app/services/multipass_extraction.py`
- `financial-engine_v2/backend/app/services/pipeline.py`
- any extraction-related modules under backend services
- any sidecar extraction modules
- parser/model/provider wrappers used by extraction
- PDF handling stack
- table/layout extraction helpers
- extraction-related tests
- docs that mention docling, multipass, parser changes, or redesign

## Mandatory output
Produce a section called:

## Extraction Method Matrix

Columns:
- Method / path
- File(s)
- Runtime status (active / partial / dormant / superseded / rejected)
- Where used
- Document types used on
- Strengths
- Weaknesses
- Evidence of success
- Evidence of failure
- Keep / compare-only / retire / redesign

Also produce:

## Authoritative Runtime Decision

A short explicit statement:
- which extraction path is the real production path now
- which paths are not authoritative
- what confusion existed historically

---

# Phase 3 — Measurement Integrity Audit

## Goal
Determine whether the reported extraction metrics are actually trustworthy.

This phase is critical.

## You must verify

- reported fixture accuracy
- reported real-gold accuracy
- trust outcome counts
- missing/wrong/abstained/quarantined counts
- whether historical gold files drifted away from reality
- whether stale expectations made the extractor look worse or better than it really was
- whether omitted required metrics were counted correctly
- whether scorecards were computed from the correct dataset
- whether any comparison scripts or scorecards were silently excluding failures
- whether any reported improvements were just fixture churn or scoring artifacts

## Required actions

1. Identify every scorecard / eval script / score artifact path.
2. Reconstruct how prior evaluation numbers were produced.
3. Re-run evaluation where safely possible.
4. Compare rerun outputs against previously reported metrics.
5. Identify any mismatch.
6. Explain whether the mismatch is due to:
   - stale gold
   - changed trust semantics
   - dataset drift
   - wrong fixture manifests
   - script bugs
   - partial runs
   - hidden filters/exclusions
   - changed extractor path
   - changed parser/provider stack
   - other

## Mandatory outputs

### A. Eval Integrity Ledger
Columns:
- Reported metric / score
- Report source
- Recomputed value
- Match? (yes/no/partial)
- If mismatch, why
- Trust status of original claim

### B. Gold Integrity Review
For every gold/eval dataset inspected, classify:
- healthy
- stale
- drifted
- under-scoped
- ambiguous
- invalid for current comparison

### C. Measurement Truth Statement
A concise section stating:
- which historical accuracy numbers are trustworthy
- which are not
- which should no longer be cited
- what the best current trustworthy baseline is

---

# Phase 4 — Failure Taxonomy + Root Cause Analysis

## Goal
Explain why accuracy has stalled.

## Required questions

1. Which metrics still fail most often?
2. Which document types still fail most often?
3. Which failures are true extractor defects versus acceptable omissions versus ambiguity versus data-missing?
4. Are failures primarily due to:
   - PDF parsing/layout issues
   - table selection issues
   - current-period selection
   - scale inference
   - label ambiguity
   - cross-row reasoning
   - evidence ranking
   - post-processing / gating issues
   - provenance / evidence mismatch
   - evaluation/gold problems
5. Which failures are patch-class versus redesign-class?
6. What is making iteration slow?

## Mandatory outputs

### Failure Taxonomy
Columns:
- Failure family
- Example docs/fixtures
- Metrics affected
- Severity
- Frequency
- Root cause class
- Patch-class or redesign-class?
- Best next intervention

### Why Improvement Stalled
A narrative section that must directly answer:
- why previous attempts did not materially improve real accuracy
- which attempts were wasted effort
- which attempts were reasonable but blocked by missing measurement
- why the process has felt slow

---

# Phase 5 — Repair / Recovery Execution

## Goal
After phases 1–4 are complete and reconciled, deploy sub-agents to improve the system.

But this must **not** be a blind “fix everything” swarm.

You must first choose one primary bottleneck and one secondary bottleneck, backed by evidence.

## Mandatory repair strategy

### Primary workstream must be one of:
- measurement/gold correction
- extraction redesign for a specific failure family
- parser/layout recovery for a specific document class
- gating/post-processing correction

### Secondary workstream may be one of:
- fixture cleanup
- eval automation
- comparator extractor benchmarking
- provenance/review support for debugging

### Explicitly blocked workstreams
You must name work that should **not** happen yet.

Examples may include:
- broad watchlist/company-analysis expansion
- memory tuning before signal quality is validated
- claim-level citation system if extraction truth baseline is still unstable
- unrelated UI redesign
- feature growth unrelated to extraction truth recovery

## Sub-agent rules for repair

You may use sub-agents, but only with strict scope ownership.

### Allowed sub-agent scopes
1. **Repo/measurement auditor**
2. **Gold/eval verifier**
3. **Runtime extraction path mapper**
4. **Failure taxonomy analyst**
5. **Bounded extractor repair agent**
6. **Targeted test/eval agent**

### Forbidden sub-agent behaviors
- no competing architecture proposals
- no ownership of multiple contested runtime surfaces at once
- no broad rewrites without manager approval
- no silent schema changes
- no hidden gold edits
- no changing truth semantics without explicit manager signoff

---

## Manager Execution Rules

### Before any implementation
The manager must output:
1. Lane classification
2. Collision assessment
3. Execution mode
4. Exact planned sub-agent scopes
5. Hard stops

### Lane classification options
- Financial Truth
- Evaluation
- Provenance
- Query Orchestration
- Memory
- Reporting

### Collision assessment
- LOW → safe
- MEDIUM → extend only
- HIGH → stop / isolate / report only

### Execution mode
- Audit
- Safe Extension
- Blocked

### Hard stop rule
If HIGH overlap risk or measurement truth is still unresolved:
- do not implement broad fixes
- output report only
- isolate into fresh clean worktree or narrower workstreams

---

## Required Final Deliverables

You must produce **one reconciled final report** with these sections:

1. Executive Summary
2. Repo State & Collision Map
3. Historical Claim Ledger
4. Extraction Method Matrix
5. Eval Integrity Ledger
6. Gold Integrity Review
7. Measurement Truth Statement
8. Failure Taxonomy
9. Why Improvement Stalled
10. Recommended Repair Plan
11. Explicitly Blocked Workstreams
12. Appendix: commands run, artifacts checked, key files inspected

If implementation work is performed after the audit phases, also include:

13. Bounded Change Sets Applied
14. Tests / Eval Reruns Performed
15. New Baseline After Fixes
16. Remaining Gaps

---

## Standard of Proof

Do not say:
- “accuracy improved” unless re-measured on a trustworthy dataset
- “gold is wrong” unless you can show why
- “this run succeeded” unless the exact run/artifact is identified
- “this method is better” unless compared on the same or clearly comparable basis
- “fix it all” unless the changes are actually staged, measured, and reconciled

---

## Suggested Starting Commands

Adapt as needed.

```bash
pwd
git rev-parse --show-toplevel
git branch --show-current
git status --short
git worktree list
git branch -vv
git log --oneline --decorate -n 50
rg -n "extraction_eval|extraction_gold_eval|multipass_extraction|pipeline|docling|operating_cash_flow|expected_trust|fixture_manifest|scorecard|gold|abstain|quarantine|parser_error|provenance" .
find financial-engine_v2 -maxdepth 5 -type f | sed -n '1,500p'
```

Also inspect:
- `financial-engine_v2/data/`
- `financial-engine_v2/backend/tests/`
- `scripts/`
- `docs/architecture/`
- `docs/ops/`
- recent extraction/eval related commits

---

## Practical Objective

The true objective is **not** to produce a pretty summary.

The true objective is to answer, with evidence:

- What extraction system is actually running?
- What methods have been tried?
- Which reported accuracy numbers are real?
- Which ones should not be trusted?
- Why have improvements stalled?
- What is the smallest evidence-backed plan that can materially improve real extraction accuracy?

Then execute that plan in bounded, measured steps.

