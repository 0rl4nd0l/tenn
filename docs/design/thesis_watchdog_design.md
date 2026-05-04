# Thesis Watchdog: Active Monitoring System Design

**Goal:** Transform static thesis audits into live monitors that alert users when new evidence contradicts or supports their saved thesis claims.

## 1. Architectural Overview

The Thesis Watchdog operates as an asynchronous validation layer triggered by the backend ingestion pipeline.

### Component Diagram
```
[Ingestion Pipeline] -> [Pipeline Stage: process_document]
                                    |
                                    v
                          [Celery Task: thesis_watchdog_check]
                                    |
                                    v
                         [ThesisWatchdogService]
                         /          |          \
           [UserThesisMemory]  [ExtractionRun]  [FinancialTruth]
                         \          |          /
                          [Contradiction Analysis]
                                    |
                                    v
                             [Thesis Alerts]
```

## 2. Technical Integration

### Trigger Hook
- **File:** `financial-engine_v2/backend/app/services/pipeline.py`
- **Location:** At the end of `process_document()`, after the `persistence` stage succeeds.
- **Action:** Call `thesis_watchdog_check.delay(document_id=str(doc.document_id), ticker=doc.ticker)`.

### New Celery Task
- **File:** `financial-engine_v2/backend/app/worker_tasks.py`
- **Name:** `thesis_watchdog_check`
- **Logic:**
    1. Fetch `active` thesis entries for the given ticker from `UserThesisMemoryStore`.
    2. Fetch the newly persisted `ExtractionRun` or `ASXPeriodicFinancial` data.
    3. For each thesis claim tagged with `auto_monitor=True`:
        - Run a "Mini-Audit": Use a specialized prompt to compare the claim against the new data.
        - If a **High-Confidence Divergence** is found:
            - Create a record in `thesis_alerts`.
            - (Optional) Emit a system notification.

## 3. Data Schema Extensions

### `user_thesis_memory.sqlite`

#### Table: `thesis_entries`
- Add column: `auto_monitor` (BOOLEAN, default TRUE)
- Add column: `monitoring_config` (JSON, for future thresholds)

#### Table: `thesis_alerts` (New)
- `alert_id` (TEXT PRIMARY KEY)
- `entry_id` (INTEGER, FK to `thesis_entries`)
- `ticker` (TEXT)
- `severity` (TEXT: 'contradiction', 'divergence', 'support')
- `finding` (TEXT)
- `evidence_source_id` (TEXT, e.g., document_id)
- `status` (TEXT: 'unread', 'dismissed', 'acted')
- `created_at` (TEXT)

## 4. Mini-Audit Prompt (Draft)

```text
Claim: "{{claim_statement}}"
New Evidence (Document {{doc_title}}):
{{new_evidence_text}}

Does this new evidence significantly contradict, support, or present a divergence from the claim?
Return JSON:
{
  "outcome": "contradict" | "support" | "neutral",
  "severity": 0.0 to 1.0,
  "reasoning": "...",
  "relevant_excerpt": "..."
}
```

## 5. UI Integration

- **Thesis Screen**: Add a "Live Monitor" toggle (linked to `auto_monitor`).
- **Dashboard/Alerts**: A new "Watchdog Alerts" section showing recent thesis divergences.
- **Diligence Tab**: Show "Recent Monitoring Activity" for a specific thesis.

## 6. Implementation Phases

1.  **Phase 1: Schema & Store**: Update `UserThesisMemoryStore` with new tables and columns.
2.  **Phase 2: Watchdog Service**: Implement the comparison logic using LLM.
3.  **Phase 3: Pipeline Hook**: Add the Celery trigger.
4.  **Phase 4: UI Feedback**: Update the Cockpit UI to show alerts.
