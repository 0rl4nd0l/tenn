# Phase 2 Plan

## Proposed Schemas

```python
@dataclass(frozen=True)
class InferenceRequest:
    operation: Literal["generate_json", "embed_texts", "chat"]
    prompt: str | None = None
    texts: tuple[str, ...] = ()
    task_type: str | None = None
    component: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)
    requested_base_url: str | None = None
    requested_model: str | None = None
    timeout_seconds: float | None = None
    client: Any | None = None
```

```python
@dataclass(frozen=True)
class InferenceResult:
    payload: Any
    operation: str
    routing_decision: RoutingDecision | None
    effective_base_url: str | None
    effective_model: str | None
    provider: str | None
    queue_name: str | None
    latency_seconds: float | None
    token_usage: Mapping[str, int] = field(default_factory=dict)
    fallback_used: bool = False
    degraded: bool = False
```

## Stage 1: Typed Adapters Only

- Add typed request/result containers beside `llm.py`.
- Add conversion helpers from current `metadata` dictionaries.
- Keep public `generate_json()` and `embed_texts()` signatures unchanged.
- Add tests proving existing metadata keys map without behavior changes.

## Stage 2: Internal Facade Result Metadata

- Have `generate_json()` and `embed_texts()` internally construct `InferenceRequest`.
- Keep return payloads unchanged.
- Expose optional debug metadata only to internal callers that explicitly request it.
- Preserve router metrics and current fallback rules.

## Stage 3: Migrate Low-Risk Callers

- Migrate one low-risk backend module D2 path from direct `generate_json_llamacpp()` to the facade.
- Preserve optional/no-LLM behavior and timeout semantics.
- Add focused tests for routed execution, no-LLM fallback, and failure handling.

## Stage 4: Celery Route Consistency

- Decide whether Celery should persist dispatch-time `RoutingDecision` or intentionally re-route at worker execution.
- Add tests for queue selection and worker behavior under changed router state.
- Do not silently change queues for existing tasks.

## Stage 5: Cockpit Runtime Contract

- Treat Cockpit `LlamaCppClient` / Anthropic paths as a separate contract.
- Do not merge them into backend inference until Cockpit provider selection, streaming, tool use, and UI metadata are explicitly covered.

## Follow-ups

- Follow-up tracker status: `DATA_MISSING` until this closeout PR is reviewed or a maintainer selects the Phase 2 implementation scope.
- Create or link a safe-extension issue for typed request/result scaffolding before any implementation.
- Create or link a separate issue for direct module D2 bypass migration before changing module D2 runtime behavior.
- Create or link a separate issue for Celery dispatch/execution routing consistency before changing task queues.
- Create or link a separate Cockpit runtime-contract issue before touching Cockpit clients.
