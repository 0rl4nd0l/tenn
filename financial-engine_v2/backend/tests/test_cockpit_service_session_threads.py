from __future__ import annotations

import sys
import threading
import uuid
from types import SimpleNamespace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.services.cockpit_service import CockpitService


def _prime_service(service: CockpitService) -> None:
    service._feedback_lock = threading.Lock()  # type: ignore[attr-defined]
    service._recent_turn_diagnostics = {}  # type: ignore[attr-defined]


class _FakeStateStore:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, str]] = []

    def add_chat_message(
        self, thread_id: str, role: str, content: str, created_at: str
    ) -> None:
        self.calls.append((thread_id, role, content))


class _FakeController:
    def __init__(self, text: str) -> None:
        self.text = text
        self.calls: list[dict[str, object]] = []
        self._hybrid_router = None

    def build_chat_response(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(
            text=self.text,
            routing_metadata=None,
            action_preview=None,
            tool_traces=[],
            evidence=[],
        )


class _FakeControllerWithMode:
    def __init__(self, text: str, mode: str, prompt: str) -> None:
        self.text = text
        self.mode = mode
        self.prompt = prompt

    def build_chat_response(self, **kwargs):
        return SimpleNamespace(
            text=self.text,
            routing_metadata=None,
            action_preview=None,
            tool_traces=[],
            evidence=[],
            mode=self.mode,
            prompt=self.prompt,
        )


class _FakeLlmClient:
    def __init__(self, model: str) -> None:
        self.model = model
        self.switch_calls: list[str] = []

    def switch_model(self, new_model: str) -> None:
        self.switch_calls.append(new_model)
        self.model = new_model


def test_chat_stream_uses_session_thread_and_persists_turns() -> None:
    service = CockpitService.__new__(CockpitService)
    _prime_service(service)
    service.state_store = _FakeStateStore()
    service.chat_controller = _FakeController("ignored")

    captured: dict[str, object] = {}
    controller = _FakeController("Here is the summary.")

    def _build_chat_controller(thread_id: str):
        captured["thread_id"] = thread_id
        return controller

    service._build_chat_controller = _build_chat_controller  # type: ignore[method-assign]

    response = CockpitService.chat_stream(
        service,
        message="ok",
        ticker="BHP",
        session_id="session-123",
        enable_web=False,
        rag=True,
        db_diagnostics=False,
    )

    assert captured["thread_id"] == "session-123"
    assert controller.calls[0]["prior_ticker"] == "BHP"
    assert response.text == "Here is the summary."
    assert service.state_store.calls == [
        ("session-123", "user", "ok"),
        ("session-123", "assistant", "Here is the summary."),
    ]


def test_chat_stream_defaults_blank_session_to_global_thread() -> None:
    service = CockpitService.__new__(CockpitService)
    _prime_service(service)
    service.state_store = _FakeStateStore()
    controller = _FakeController("Hello")
    service.chat_controller = controller
    service._build_chat_controller = lambda thread_id: controller  # type: ignore[method-assign]

    response = CockpitService.chat_stream(
        service,
        message="hello",
        session_id="  ",
    )

    assert response.text == "Hello"
    assert service.state_store.calls == [
        ("global-main", "user", "hello"),
        ("global-main", "assistant", "Hello"),
    ]


def test_chat_stream_populates_model_metadata_even_when_controller_omits_it() -> None:
    service = CockpitService.__new__(CockpitService)
    _prime_service(service)
    service.state_store = _FakeStateStore()
    service.llm_client = _FakeLlmClient("model:gpt-oss-20b")
    controller = _FakeController("No evidence available.")
    service._build_chat_controller = lambda thread_id: controller  # type: ignore[method-assign]

    response = CockpitService.chat_stream(
        service,
        message="tell me about BHP",
        session_id="session-model-meta",
        model="model:qwen3.5-35b-a3b",
    )

    assert service.llm_client.model == "model:qwen3.5-35b-a3b"
    assert response.routing_metadata == {
        "model": "model:qwen3.5-35b-a3b",
        "source": "local",
        "latency_ms": 0,
        "cost_usd": 0.0,
    }


def test_chat_stream_uses_last_attempt_route_when_controller_metadata_is_empty() -> None:
    service = CockpitService.__new__(CockpitService)
    _prime_service(service)
    service.state_store = _FakeStateStore()
    service.llm_client = _FakeLlmClient("model:qwen3.5-35b-a3b")
    controller = _FakeController(
        "I encountered an error communicating with the language model: Error code: 529"
    )
    controller._hybrid_router = SimpleNamespace(
        last_attempt_metadata=lambda: {
            "source": "api",
            "model": "claude-sonnet-test",
            "latency_ms": 0,
            "cost_usd": 0.0,
            "routing_reason": "force:api",
        }
    )
    service._build_chat_controller = lambda thread_id: controller  # type: ignore[method-assign]

    response = CockpitService.chat_stream(
        service,
        message="/cloud tell me about AGL",
        session_id="session-last-attempt",
    )

    assert "Error code: 529" in response.text
    assert response.routing_metadata == {
        "source": "api",
        "model": "claude-sonnet-test",
        "latency_ms": 0,
        "cost_usd": 0.0,
        "routing_reason": "force:api",
    }


def test_chat_stream_emits_model_switch_status_events() -> None:
    service = CockpitService.__new__(CockpitService)
    _prime_service(service)
    service.state_store = _FakeStateStore()
    service.llm_client = _FakeLlmClient("model:gpt-oss-20b")
    controller = _FakeController("Switch completed.")
    service._build_chat_controller = lambda thread_id: controller  # type: ignore[method-assign]

    statuses: list[str] = []
    response = CockpitService.chat_stream(
        service,
        message="switch model",
        session_id="session-switch",
        model="model:qwen3.5-35b-a3b",
        on_status=statuses.append,
    )

    assert response.text == "Switch completed."
    assert service.llm_client.model == "model:qwen3.5-35b-a3b"
    assert statuses[0] == "Switching model: model:gpt-oss-20b -> model:qwen3.5-35b-a3b"
    assert "Model ready: model:qwen3.5-35b-a3b" in statuses


def test_chat_stream_skips_local_model_switch_when_turn_will_route_to_api() -> None:
    service = CockpitService.__new__(CockpitService)
    _prime_service(service)
    service.state_store = _FakeStateStore()
    service.llm_client = _FakeLlmClient("model:gpt-oss-20b")
    controller = _FakeController("API-routed answer.")
    controller._hybrid_router = SimpleNamespace(
        preview_route=lambda force_backend=None: {
            "source": "api",
            "model": "claude-sonnet-test",
            "routing_reason": "extraction_active",
        }
    )
    service._build_chat_controller = lambda thread_id: controller  # type: ignore[method-assign]

    statuses: list[str] = []
    response = CockpitService.chat_stream(
        service,
        message="market update today?",
        session_id="session-preview-api",
        model="model:qwen3.5-35b-a3b",
        on_status=statuses.append,
    )

    assert response.text == "API-routed answer."
    assert service.llm_client.model == "model:gpt-oss-20b"
    assert service.llm_client.switch_calls == []
    assert statuses[0] == (
        "Skipping local model switch; this turn will route to api (extraction_active)"
    )
    assert statuses[1] == "Requested model: model:qwen3.5-35b-a3b"


def test_chat_stream_records_response_mode_in_turn_diagnostics() -> None:
    service = CockpitService.__new__(CockpitService)
    _prime_service(service)
    service.state_store = _FakeStateStore()
    controller = _FakeControllerWithMode(
        text="Deep answer.",
        mode="deep_analysis",
        prompt="prompt excerpt",
    )
    service._build_chat_controller = lambda thread_id: controller  # type: ignore[method-assign]

    response = CockpitService.chat_stream(
        service,
        message="deep dive",
        session_id="session-deep",
    )

    assert response.text == "Deep answer."
    saved = service._recent_turn_diagnostics["session-deep"][-1]
    assert saved["response_mode"] == "deep_analysis"
    assert saved["prompt"] == "prompt excerpt"


def test_preload_preferred_model_skips_during_active_extraction(monkeypatch) -> None:
    service = CockpitService.__new__(CockpitService)
    service.llm_client = SimpleNamespace(
        base_url="http://127.0.0.1:8001",
        model="model:gpt-oss-20b",
        switch_model=lambda new_model: None,
    )

    class _Response:
        content = b'{"data": []}'

        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return {
                "data": [
                    {
                        "id": "model:qwen2.5-14b-instruct",
                        "status": {"value": "loaded"},
                    }
                ]
            }

    monkeypatch.setattr(
        "app.services.cockpit_service.httpx.get",
        lambda *args, **kwargs: _Response(),
    )
    monkeypatch.setattr("app.services.router_state.is_extraction_active", lambda: True)

    called = {"load": False}
    monkeypatch.setattr(
        "cockpit.integrations.llamacpp_manager.load_model_api",
        lambda **kwargs: called.__setitem__("load", True),
    )

    CockpitService._preload_preferred_model(
        service,
        preferred_model="model:qwen3.5-35b-a3b",
        api_key="local-openai-key",
    )

    assert called["load"] is False


def test_get_diagnostic_matrix_uses_canonical_financial_rows(monkeypatch) -> None:
    service = CockpitService.__new__(CockpitService)

    doc_a = uuid.uuid4()
    rows = [
        SimpleNamespace(
            revenue=128_458_000,
            ebit=None,
            net_debt=None,
            np_attributable=-73_500_000,
            shares_outstanding=467_479_000,
            capex=-14_026_000,
            confidence_metrics=0.852,
            source_document_id=doc_a,
        )
    ]

    class _FinancialRowsQuery:
        def filter(self, *args, **kwargs):
            return self

        def order_by(self, *args, **kwargs):
            return self

        def limit(self, *args, **kwargs):
            return self

        def all(self):
            return rows

    class _FailedDocQuery:
        def filter(self, *args, **kwargs):
            return self

        def distinct(self):
            return self

        def all(self):
            return []

    class _FakeDb:
        def query(self, *args, **kwargs):
            target = args[0] if args else None
            if target is not None and getattr(target, "__name__", None) == "ASXPeriodicFinancial":
                return _FinancialRowsQuery()
            return _FailedDocQuery()

        def close(self) -> None:
            return None

    monkeypatch.setattr("app.services.cockpit_service.SessionLocal", lambda: _FakeDb())

    result = CockpitService.get_diagnostic_matrix(service, "extraction", "EOS")

    assert result == {
        "stage": "extraction",
        "entities": [
            {
                "entity": "EOS",
                "metrics": {
                    "REVENUE": "populated",
                    "EBIT": "sparse",
                    "NET_DEBT": "sparse",
                    "EPS": "populated",
                    "CAPEX": "populated",
                },
            }
        ],
    }


def test_get_diagnostic_matrix_marks_low_confidence_evaluation_rows_abstain(
    monkeypatch,
) -> None:
    service = CockpitService.__new__(CockpitService)

    doc_b = uuid.uuid4()
    rows = [
        SimpleNamespace(
            revenue=44_070_000,
            ebit=None,
            net_debt=None,
            np_attributable=46_786_000,
            shares_outstanding=467_309_000,
            capex=-6_165_000,
            confidence_metrics=0.7,
            source_document_id=doc_b,
        )
    ]

    class _FinancialRowsQuery:
        def filter(self, *args, **kwargs):
            return self

        def order_by(self, *args, **kwargs):
            return self

        def limit(self, *args, **kwargs):
            return self

        def all(self):
            return rows

    class _FailedDocQuery:
        def filter(self, *args, **kwargs):
            return self

        def distinct(self):
            return self

        def all(self):
            return []

    class _FakeDb:
        def query(self, *args, **kwargs):
            target = args[0] if args else None
            if target is not None and getattr(target, "__name__", None) == "ASXPeriodicFinancial":
                return _FinancialRowsQuery()
            return _FailedDocQuery()

        def close(self) -> None:
            return None

    monkeypatch.setattr("app.services.cockpit_service.SessionLocal", lambda: _FakeDb())

    result = CockpitService.get_diagnostic_matrix(service, "evaluation", "EOS")

    assert result["entities"][0]["metrics"]["REVENUE"] == "abstain"
    assert result["entities"][0]["metrics"]["CAPEX"] == "abstain"
    assert result["entities"][0]["metrics"]["EPS"] == "abstain"


def test_get_diagnostic_matrix_marks_failed_when_source_document_extraction_failed(
    monkeypatch,
) -> None:
    service = CockpitService.__new__(CockpitService)
    doc_id = uuid.uuid4()
    rows = [
        SimpleNamespace(
            revenue=None,
            ebit=None,
            net_debt=None,
            np_attributable=None,
            shares_outstanding=None,
            capex=None,
            confidence_metrics=None,
            source_document_id=doc_id,
        )
    ]

    class _FinancialRowsQuery:
        def filter(self, *args, **kwargs):
            return self

        def order_by(self, *args, **kwargs):
            return self

        def limit(self, *args, **kwargs):
            return self

        def all(self):
            return rows

    class _FailedDocQuery:
        def filter(self, *args, **kwargs):
            return self

        def distinct(self):
            return self

        def all(self):
            return [(doc_id,)]

    class _FakeDb:
        def query(self, *args, **kwargs):
            target = args[0] if args else None
            if target is not None and getattr(target, "__name__", None) == "ASXPeriodicFinancial":
                return _FinancialRowsQuery()
            return _FailedDocQuery()

        def close(self) -> None:
            return None

    monkeypatch.setattr("app.services.cockpit_service.SessionLocal", lambda: _FakeDb())

    result = CockpitService.get_diagnostic_matrix(service, "extraction", "EOS")

    assert result["entities"][0]["metrics"]["REVENUE"] == "failed"


def test_get_intel_pulse_stats_uses_canonical_financial_rows(monkeypatch) -> None:
    service = CockpitService.__new__(CockpitService)

    documents_count = 4
    failed_runs_count = 1
    financial_rows = [
        SimpleNamespace(
            revenue=128_458_000,
            ebit=None,
            np_attributable=-73_500_000,
            operating_cf=-24_185_000,
            investing_cf=131_287_000,
            financing_cf=-53_016_000,
            capex=-14_026_000,
            cash_end=106_916_000,
            net_debt=None,
            shares_outstanding=467_479_000,
            total_equity=None,
            interest_expense=None,
            confidence_metrics=0.852,
            period_end="2025-12-31",
            source_document_id=uuid.uuid4(),
        ),
        SimpleNamespace(
            revenue=44_070_000,
            ebit=None,
            np_attributable=46_786_000,
            operating_cf=-9_213_000,
            investing_cf=97_919_000,
            financing_cf=-50_793_000,
            capex=-6_165_000,
            cash_end=90_289_000,
            net_debt=None,
            shares_outstanding=467_309_000,
            total_equity=None,
            interest_expense=None,
            confidence_metrics=0.889,
            period_end="2025-06-30",
            source_document_id=uuid.uuid4(),
        ),
    ]

    class _ScalarQuery:
        def __init__(self, value):
            self.value = value

        def filter(self, *args, **kwargs):
            return self

        def join(self, *args, **kwargs):
            return self

        def scalar(self):
            return self.value

    class _RowsQuery:
        def filter(self, *args, **kwargs):
            return self

        def order_by(self, *args, **kwargs):
            return self

        def limit(self, *args, **kwargs):
            return self

        def all(self):
            return financial_rows

    class _CountQuery:
        def filter(self, *args, **kwargs):
            return self

        def join(self, *args, **kwargs):
            return self

        def count(self):
            return failed_runs_count

        def order_by(self, *args, **kwargs):
            return self

        def limit(self, *args, **kwargs):
            return self

        def all(self):
            return [
                SimpleNamespace(
                    run_id="deadbeefcafebabe",
                    confidence_overall=0.0,
                    error="classifier_low_confidence:0.0",
                    created_at=None,
                )
            ]

    class _JoinedFailureQuery:
        def join(self, *args, **kwargs):
            return self

        def filter(self, *args, **kwargs):
            return self

        def order_by(self, *args, **kwargs):
            return self

        def limit(self, *args, **kwargs):
            return self

        def all(self):
            return [
                (
                    SimpleNamespace(
                        run_id="deadbeefcafebabe",
                        confidence_overall=0.0,
                        error="classifier_low_confidence:0.0",
                        created_at=None,
                    ),
                    "EOS",
                )
            ]

    class _FakeDb:
        def __init__(self) -> None:
            # db.query order: document count, (financial rows), (failure query), runs count, periodic count
            self._scalars = iter(
                [documents_count, 42, len(financial_rows)]
            )

        def query(self, *args, **kwargs):
            if len(args) >= 2:
                return _JoinedFailureQuery()
            target = args[0] if args else None
            if getattr(target, "name", None) == "count":
                return _ScalarQuery(next(self._scalars))
            if target is not None and getattr(target, "__name__", None) == "ASXPeriodicFinancial":
                return _RowsQuery()
            return _CountQuery()

        def close(self) -> None:
            return None

    monkeypatch.setattr(
        "app.services.cockpit_service.SessionLocal",
        lambda: _FakeDb(),
    )

    result = CockpitService.get_intel_pulse_stats(service, "EOS")

    assert result["stats"]["document_count"] == documents_count
    assert result["stats"]["extraction_count"] == len(financial_rows)
    assert result["stats"]["recent_financial_rows_sampled"] == len(financial_rows)
    assert result["stats"]["periodic_financial_rows_total"] == len(financial_rows)
    assert result["stats"]["extraction_runs_total"] == 42
    assert result["stats"]["trust_score_avg"] == 0.87
    assert result["stats"]["quarantine_rate"] == 25.0
    assert result["stats"]["extraction_failure_rate_pct"] == 25.0
    assert result["stats"]["population_index"] == 66.7
    assert result["pipeline"][0]["id"] == "overview"
    assert result["pipeline"][0]["health"] == 76.9
    assert result["pipeline"][0]["status"] == "degraded"
    assert result["pipeline"][1]["id"] == "extraction"
    assert result["pipeline"][1]["health"] == 66.7
    assert result["pipeline"][3]["status"] == "unavailable"
    assert result["pipeline"][4]["status"] == "unavailable"
    assert result["pipeline"][5]["health"] == 75.0
    assert "generated_at" in result
