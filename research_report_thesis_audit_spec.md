# Research Report Thesis Audit

**Status:** Planning draft  
**Primary lane:** Memory  
**Execution posture:** Audit-first, safe-extension only

## 1. Purpose

Allow Tenn to accept a user-authored company research report as a **non-canonical thesis source**, convert it into structured claims and assumptions, independently verify and challenge those claims, and produce a structured thesis-audit output. Tenn may propose selected insights for storage in **confirmation-gated user thesis memory**, but must never treat the uploaded report as canonical financial truth.

## 2. Why this exists

Users already have research reports, notes, and thesis writeups. Today, Tenn can add much more value than simple summarization by:

- reconstructing the actual thesis faithfully
- extracting the few load-bearing claims that matter most
- checking those claims against Tenn’s existing evidence layers
- surfacing contradictions, staleness, and weak assumptions
- generating explicit “change-my-mind” and monitoring triggers
- preserving only user-approved thesis insights in a separate memory class

## 3. Core product definition

**One-sentence definition**

> Tenn accepts a user-authored company research report as a non-canonical thesis source, extracts atomic claims and assumptions, independently verifies and challenges them, produces a structured thesis-audit report, and proposes selected insights for confirmation-gated thesis memory.

## 4. Design principles

1. **Hypothesis source, not truth source**
   - Uploaded reports are inputs for audit and reasoning.
   - They must not define canonical numeric truth.

2. **Claim-level provenance**
   - Every extracted claim must point back to the report span that produced it.
   - Every verification or contradiction must point to independent evidence spans.

3. **Single orchestrator-led flow**
   - Reuse Tenn’s orchestrator-led `EvidenceBundle` pattern.
   - Do not create a second analysis control plane.

4. **Bounded skepticism**
   - Contrarian analysis must try to break the thesis, but only with evidence.
   - No generic “risks exist” filler.

5. **Confirmation-gated memory**
   - User thesis memory is separate from company memory and market memory.
   - Nothing is saved automatically.

6. **Preserve uncertainty**
   - `DATA_MISSING`, `unverified`, and `plausible but weakly evidenced` are valid outcomes.
   - Lack of confirmation is not the same as contradiction.

## 5. Non-goals

- Do not auto-write report content into canonical financial truth.
- Do not silently blend report-derived claims into company memory or market memory.
- Do not create an autonomous background monitoring system in v1.
- Do not merge multiple reports or prior user notes in v1.
- Do not add a multi-agent debate swarm as the default reasoning path.
- Do not let LLM output define numeric truth.

## 6. Primary user flow

1. User uploads a company research report.
2. Tenn resolves company/ticker and report scope.
3. Tenn produces a **faithful thesis reconstruction**.
4. Tenn extracts atomic claims, assumptions, catalysts, and valuation statements.
5. Tenn ranks the load-bearing claims.
6. Tenn gathers an independent `EvidenceBundle`.
7. Tenn verifies claims and labels support status.
8. Tenn runs a bounded skeptical/contrarian pass.
9. Tenn returns a structured thesis-audit report.
10. Tenn offers selected items for **confirmation-gated** save into user thesis memory.

## 7. Inputs

### Required
- Uploaded report file or text
- User query / intent

### Optional
- Company ticker / issuer name
- Thesis horizon
- User confidence level or stance
- Prior saved thesis notes for the same company (read-only context only; no merge in v1)

## 8. Output

The thesis-audit result should include:

1. **Faithful thesis summary**
2. **Load-bearing claims**
3. **Hidden assumptions**
4. **Claim verification matrix**
5. **Strongest disconfirming evidence**
6. **Report-to-reality delta**
7. **Change-my-mind triggers**
8. **Top next-diligence questions**
9. **Save candidates for user thesis memory**

## 9. Claim types

Every extracted claim should be typed as one of:

- `numeric_fact`
- `company_narrative`
- `causal_claim`
- `catalyst_timing`
- `valuation_assumption`
- `market_sector_claim`

## 10. Claim statuses

Each verified claim should end in exactly one status:

- `supported`
- `partially_supported`
- `contradicted`
- `stale`
- `assumption`
- `DATA_MISSING`

Confidence labels should remain separate:

- `Confirmed`
- `Inferred`
- `Speculative`

## 11. High-value reasoning layers

### 11.1 Faithful thesis reconstruction
Tenn must first state what the report actually argues before critiquing it.

### 11.2 Atomic claim extraction
The stored and evaluated unit is the **atomic claim**, not the full report.

### 11.3 Hidden assumption extraction
Tenn should infer what must be true for the thesis to work, even if the report does not state it directly.

### 11.4 Load-bearing claim ranking
Identify the 2–5 claims that carry most of the thesis weight.

### 11.5 Verification matrix
For each claim, show:

- claim text
- claim type
- report span
- independent evidence found
- status
- confidence
- short explanation

### 11.6 Adversarial break packs
Run bounded skeptical passes for:

- **Factual break** — report claim not supported by evidence
- **Causal break** — stated driver not convincingly linked to outcome
- **Timing break** — catalyst slower, later, or less likely than assumed
- **Financing break** — refinancing, dilution, or balance-sheet pressure breaks the path
- **Peer/base-rate break** — comparable cases do not support the edge
- **Valuation break** — upside requires heroic rather than reasonable assumptions

### 11.7 Change-my-mind triggers
Explicitly define the few events, metrics, or disclosures that would invalidate the thesis.

### 11.8 Next-diligence generator
Rank the few missing facts or documents most likely to change conviction.

## 12. Runtime shape

The feature should remain a bounded extension of Tenn’s existing orchestrator-led analysis path.

### Recommended flow

1. `resolve_entity_and_ticker`
2. `ingest_report_as_noncanonical_source`
3. `extract_report_spans`
4. `extract_thesis_claims`
5. `rank_load_bearing_claims`
6. `assemble_evidence_bundle`
7. `verify_claims_against_evidence`
8. `run_thesis_break_pack`
9. `synthesize_thesis_audit`
10. `build_user_thesis_memory_proposals`
11. `offer_confirmation_gated_save`

## 13. Candidate data contracts

### `ResearchReportInput`
```json
{
  "report_id": "rr_123",
  "source_type": "user_uploaded_report",
  "company_name": "Example Ltd",
  "ticker": "EXM",
  "as_of_date": "2026-04-30",
  "file_type": "pdf",
  "raw_text_artifact_id": "artifact_abc"
}
```

### `ReportSpan`
```json
{
  "span_id": "span_001",
  "report_id": "rr_123",
  "section_label": "Investment thesis",
  "char_start": 1200,
  "char_end": 1710,
  "text": "..."
}
```

### `ThesisClaim`
```json
{
  "claim_id": "claim_001",
  "report_id": "rr_123",
  "text": "Margins will expand as fixed costs are leveraged over higher volume.",
  "claim_type": "causal_claim",
  "directness": "direct",
  "materiality": "high",
  "report_span_ids": ["span_001"],
  "time_horizon": "12m"
}
```

### `ThesisAssumption`
```json
{
  "assumption_id": "assump_001",
  "report_id": "rr_123",
  "text": "Volume growth arrives before financing pressure intensifies.",
  "derived_from_claim_ids": ["claim_001"],
  "materiality": "high"
}
```

### `ClaimVerification`
```json
{
  "claim_id": "claim_001",
  "status": "partially_supported",
  "confidence": "Inferred",
  "supporting_evidence_ids": ["ev_101", "ev_102"],
  "contradicting_evidence_ids": ["ev_201"],
  "notes": "Historical margin expansion is evidenced, but forward leverage claim remains partly assumptive."
}
```

### `ContrarianFinding`
```json
{
  "finding_id": "cf_001",
  "break_type": "financing_break",
  "severity": "high",
  "text": "The thesis depends on avoiding dilution, but balance-sheet pressure suggests external funding risk.",
  "evidence_ids": ["ev_301"],
  "targets": ["claim_004", "assump_001"]
}
```

### `UserThesisMemoryProposal`
```json
{
  "proposal_id": "utm_001",
  "report_id": "rr_123",
  "proposal_type": "kill_criteria",
  "text": "If gross margin fails to improve by the next half, re-evaluate thesis.",
  "supporting_ids": ["claim_001", "cf_001"],
  "requires_confirmation": true
}
```

### `ThesisAuditReport`
```json
{
  "report_id": "rr_123",
  "company_name": "Example Ltd",
  "faithful_summary": "...",
  "load_bearing_claim_ids": ["claim_001", "claim_002"],
  "verification_summary": {
    "supported": 3,
    "partially_supported": 2,
    "contradicted": 1,
    "stale": 1,
    "assumption": 2,
    "DATA_MISSING": 1
  },
  "contrarian_findings": ["cf_001"],
  "change_my_mind_triggers": ["..."],
  "next_diligence_questions": ["..."],
  "memory_proposals": ["utm_001"]
}
```

## 14. Guardrails

### Truth boundaries
- Canonical financial truth remains the only source for numeric truth.
- Narrative synthesis must be clearly labeled as derived.
- Report claims must never overwrite canonical facts.

### Memory boundaries
- User thesis memory is separate from company and market memory.
- No automatic memory writes.
- No silent carry-forward of speculative notes.

### Provenance boundaries
- All extracted claims require report-span provenance.
- All verification judgments require independent evidence provenance.
- Contrarian findings without evidence are invalid.

### Safety / quality boundaries
- Preserve `DATA_MISSING` where evidence is absent.
- Do not present polished prose as proof.
- Do not hide stale claims behind synthesis.

## 15. V1 scope

### In scope
- One report
- One company
- Faithful summary
- Atomic claim extraction
- Hidden assumption extraction
- Claim verification matrix
- One bounded skeptic pass
- Save proposals for user thesis memory

### Explicitly out of scope
- Multi-report merging
- Automatic monitoring/alerts
- Background jobs
- Portfolio/watchlist-wide thesis scoring
- Sector-specific skeptic packs
- Automatic contradiction resolution across all historical user notes

## 16. Deferred extensions

- Multi-report comparison and thesis versioning
- Thesis aging / staleness detection
- Automatic alerts when new filings or news break a saved assumption
- Cross-thesis consistency checks for the same company over time
- Sector-specific skeptic packs
- Watchlist integration
- Human review queue / approval UI

## 17. Acceptance criteria

A v1 result is acceptable only if it:

1. preserves a faithful thesis summary before critique
2. produces atomic claims with report-span provenance
3. labels claims with explicit support status
4. surfaces at least the strongest disconfirming evidence when available
5. clearly separates contradiction from uncertainty
6. proposes memory items without saving them automatically
7. keeps numeric truth separate from narrative reasoning

## 18. Recommended implementation boundary

### Safe extension surfaces
- orchestrator-led analysis flow
- evidence bundle assembly
- reporting layer for thesis-audit output
- separate user thesis memory proposal layer

### Unsafe surfaces for this feature
- canonical extraction truth path
- broad memory-ranking rewrites
- new parallel agent runtime
- silent auto-ingestion into company/market memory

## 19. Suggested implementation order

1. Finalize this feature spec
2. Run collision audit against:
   - `query_orchestrator.py`
   - `company_memory.py`
   - `market_memory.py`
   - `memory_signal_router.py`
   - `provenance.py`
   - relevant cockpit reporting surfaces
3. Define claim/assumption/report data contracts
4. Build report-span extraction and claim extraction in a bounded, testable path
5. Reuse existing evidence bundle assembly
6. Add verification matrix output
7. Add contrarian/break-pack output
8. Add confirmation-gated thesis-memory proposal output
9. Defer monitoring and multi-report features

## 20. Open questions

- Should report ingestion live behind a new request type or a distinct company-analysis mode?
- Should the v1 output appear in Cockpit only, or also in backend API/report exports?
- Should saved thesis memory proposals be stored as distinct typed notes or as a generic proposal envelope?
- What minimum evidence threshold is required before Tenn may mark a claim as `supported`?
