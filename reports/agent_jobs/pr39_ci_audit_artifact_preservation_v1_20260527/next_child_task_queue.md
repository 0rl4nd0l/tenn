# Next Child Task Queue

No child task cards were created by this preservation task.

## 1. C01 - Architecture Invariant Reconciliation

Recommended title:
`[CI] Reconcile backend sqlite3/uuid4/vector invariant failures for PR #39`

Lane: Evaluation with Repo Hygiene support.

Architecture nuance: reconcile the broad sqlite invariant against documented
SQLite-backed qualitative memory and operational stores before removing sqlite
usage or relaxing the invariant. The child task must preserve architecture
truth boundaries and should use architecture-check before any remediation.

Forbidden surfaces: production DB/Qdrant/news/memory, canonical financial
truth, parser routing, extraction prompts, gold labels, runtime/model/GPU/service
config, invariant relaxation without explicit migration approval.

Validation: focused architecture invariant and cursor-rule pytest, Ruff on
changed files, and architecture-check against current architecture docs.

## 2. C02 - Cockpit Chat Controller Contract

Recommended title:
`[CI] Align Cockpit chat controller test doubles with llm_client contract`

Lane: Query Orchestration.

## 3. C03 - Cockpit Subagent Event Loop

Recommended title:
`[CI] Make Cockpit subagent event-loop contract explicit under pytest-asyncio`

Lane: Query Orchestration.

## 4. C04 - Streaming Subprocess job_id Contract

Recommended title:
`[CI] Align streaming subprocess helper tests with required job_id`

Lane: Repo Hygiene.

## 5. C05 - News Loader Ollama URL API

Recommended title:
`[CI] Verify or carry Ollama URL loader repair into PR #39 before rerun`

Lane: Query Orchestration.

## 6. C08 - Hybrid Router Policy Contract

Recommended title:
`[CI] Decide HybridRouter force-local and on_chunk wrapper contract`

Lane: Query Orchestration.

## 7. C07 - Cockpit Grounding Stress Expectations

Recommended title:
`[CI] Reconcile Cockpit stress expectations with grounded refusal and action-preview behavior`

Lane: Query Orchestration.

## 8. C09 - Memo Signal Routing

Recommended title:
`[CI] Restore or re-contract memo extractor signal routing in isolated tests`

Lane: Memory.

## 9. C13 - Query Sufficiency Guard

Recommended title:
`[CI] Restore query sufficiency guard when only announcement/news context is available`

Lane: Query Orchestration.

## 10. C11 - Real-Gold PDF Asset

Recommended title:
`[CI] Resolve missing real-gold PDF asset path or fixture contract for PR #39`

Lane: Evaluation.

## 11. C12 - Process Document Redis/Celery CI Dependency

Recommended title:
`[CI] Isolate process-document API test from live Redis or declare CI Redis service`

Lane: Repo Hygiene.

## 12. C06 - Marketplace Time-Stable Fixtures

Recommended title:
`[CI] Stabilize marketplace benchmark fixtures against wall-clock drift`

Lane: Evaluation.

## 13. C10 - Cockpit Preferences Runtime Target Contract

Recommended title:
`[CI] Settle Cockpit preferences chat_runtime_target API contract`

Lane: Query Orchestration.
