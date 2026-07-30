from __future__ import annotations

import json
import sys
import threading
import uuid
from types import SimpleNamespace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.services.cockpit_service import (
    CockpitService,
    _normalize_cockpit_artifact_dirs,
)


def test_normalize_cockpit_artifact_dirs_maps_relative_reports_to_data_root() -> None:
    cfg = {
        "reports": {"dir": "reports"},
        "exports": {"dir": "reports/analysis"},
    }

    _normalize_cockpit_artifact_dirs(cfg, data_root="/data")

    data_root = Path("/data").resolve()
    assert cfg["reports"]["dir"] == str(data_root / "reports")
    assert cfg["exports"]["dir"] == str(data_root / "reports" / "analysis")


def test_normalize_cockpit_artifact_dirs_preserves_absolute_paths() -> None:
    cfg = {
        "reports": {"dir": "/mnt/runtime/reports"},
        "exports": {"dir": "/mnt/runtime/reports/analysis"},
    }

    _normalize_cockpit_artifact_dirs(cfg, data_root="/data")

    assert cfg["reports"]["dir"] == "/mnt/runtime/reports"
    assert cfg["exports"]["dir"] == "/mnt/runtime/reports/analysis"


def test_normalize_cockpit_artifact_dirs_falls_back_when_data_root_is_unusable(
    tmp_path,
) -> None:
    cfg = {
        "reports": {"dir": "reports"},
        "exports": {"dir": "reports/analysis"},
    }

    _normalize_cockpit_artifact_dirs(
        cfg,
        data_root="/mnt/nvme/tenn/runtime-data",
        writable_fallback_root=tmp_path,
        path_is_usable=lambda path: str(path).startswith(str(tmp_path)),
    )

    assert cfg["reports"]["dir"] == str(tmp_path / "reports")
    assert cfg["exports"]["dir"] == str(tmp_path / "reports" / "analysis")


def _prime_service(service: CockpitService) -> None:
    service._feedback_lock = threading.Lock()  # type: ignore[attr-defined]
    service._recent_turn_diagnostics = {}  # type: ignore[attr-defined]


class _FakeStateStore:
    def __init__(self, preferences: dict[str, str] | None = None) -> None:
        self.calls: list[tuple[str, str, str]] = []
        self.preferences = dict(preferences or {})

    def add_chat_message(
        self, thread_id: str, role: str, content: str, created_at: str
    ) -> None:
        self.calls.append((thread_id, role, content))

    def get_preference(self, key: str, default: str = "") -> str:
        return self.preferences.get(key, default)


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


def test_analyze_flagged_bundle_falls_back_to_deterministic_analysis_on_llm_error() -> None:
    service = CockpitService.__new__(CockpitService)
    service.llm_timeout_seconds = 30.0

    class _FailingLlmClient:
        def chat(self, *_args, **_kwargs):
            raise TimeoutError("simulated timeout")

    service.llm_client = _FailingLlmClient()

    analysis = CockpitService._analyze_flagged_bundle(
        service,
        {
            "feedback_type": "poor",
            "note": "answer looked stale",
            "flagged_message": {"content": "Top movers today were ..."},
            "backend_turn": {
                "request": {"message": "what are the market movers today"},
                "status_events": [{"stage": "Timed out while waiting for tool response"}],
                "tool_traces": [{"tool_name": "search_news", "ok": False, "error": "timeout"}],
                "tool_calls": [{"tool": "search_news"}],
                "routing_metadata": {"source": "local"},
            },
            "frontend_snapshot": {"transcript": []},
        },
    )

    assert analysis is not None
    assert analysis["status"] == "fallback"
    assert isinstance(analysis.get("summary"), str) and analysis["summary"]
    assert isinstance(analysis.get("likely_failure_modes"), list)
    assert analysis["likely_failure_modes"]
    assert isinstance(analysis.get("evidence"), list)
    assert any("Fallback trigger" in str(item) for item in analysis["evidence"])


def test_finalize_flagged_report_async_persists_fallback_analysis_on_timeout(
    tmp_path: Path,
) -> None:
    service = CockpitService.__new__(CockpitService)
    service.llm_timeout_seconds = 30.0

    class _FailingLlmClient:
        def chat(self, *_args, **_kwargs):
            raise TimeoutError("simulated timeout")

    service.llm_client = _FailingLlmClient()

    report_dir = tmp_path / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    bundle_path = report_dir / "bundle.json"
    summary_path = report_dir / "summary.md"
    analysis_path = report_dir / "analysis.json"
    bundle = {
        "report_id": "flag_timeout",
        "saved_at": "2026-04-22T00:00:00+00:00",
        "feedback_type": "poor",
        "capture_kind": "chat_feedback",
        "session_id": "session-timeout",
        "note": "timed out",
        "flagged_message": {"content": "market movers looked stale"},
        "backend_turn": {
            "request": {"message": "market movers today"},
            "status_events": [{"stage": "Timed out while waiting for tool response"}],
            "tool_traces": [{"tool_name": "search_news", "ok": False, "error": "timeout"}],
            "tool_calls": [{"tool": "search_news"}],
        },
        "frontend_snapshot": {"transcript": []},
    }

    CockpitService._finalize_flagged_report_async(
        service,
        report_id="flag_timeout",
        bundle=bundle,
        bundle_path=bundle_path,
        summary_path=summary_path,
        analysis_path=analysis_path,
    )

    assert analysis_path.exists()
    analysis = json.loads(analysis_path.read_text(encoding="utf-8"))
    assert analysis["status"] == "fallback"
    assert analysis["status"] != "llm_unavailable"
    assert isinstance(analysis.get("likely_failure_modes"), list)


def test_chat_stream_uses_session_thread_and_persists_turns() -> None:
    service = CockpitService.__new__(CockpitService)
    _prime_service(service)
    service.state_store = _FakeStateStore()
    service.chat_controller = _FakeController("ignored")

    captured: dict[str, object] = {}
    controller = _FakeController("Here is the summary.")

    def _build_chat_controller(thread_id: str, **_kwargs):
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


def test_chat_stream_passes_attached_sources_to_controller() -> None:
    service = CockpitService.__new__(CockpitService)
    _prime_service(service)
    service.state_store = _FakeStateStore()
    controller = _FakeController("Attached source answer.")
    service._build_chat_controller = lambda thread_id, **_kwargs: controller  # type: ignore[method-assign]

    response = CockpitService.chat_stream(
        service,
        message="compare this listing",
        session_id="session-attach",
        attached_sources=[{"source_id": "src-1", "source_kind": "concat"}],
    )

    assert response.text == "Attached source answer."
    assert controller.calls[0]["attached_sources"] == [
        {"source_id": "src-1", "source_kind": "concat"}
    ]


def test_chat_stream_seeds_recent_youtube_options_between_session_controllers() -> None:
    service = CockpitService.__new__(CockpitService)
    _prime_service(service)
    service.state_store = _FakeStateStore()
    service._recent_youtube_video_options_by_thread = {}

    class _RecentVideosController:
        _hybrid_router = None

        def build_chat_response(self, **_kwargs):
            return SimpleNamespace(
                text="Recent videos from Kneppy Invests (UCabc123):",
                routing_metadata=None,
                action_preview=None,
                tool_traces=[],
                evidence=[
                    {
                        "tool": "check_youtube_channel_recent_videos",
                        "result": {
                            "videos": [
                                {
                                    "position": 1,
                                    "title": "Status of My Trades",
                                    "video_id": "ULVlVUSSSkI",
                                    "webpage_url": "https://www.youtube.com/watch?v=ULVlVUSSSkI",
                                    "scores": {"overall": 0.88},
                                }
                            ]
                        },
                    }
                ],
            )

    class _SelectionController:
        _hybrid_router = None

        def __init__(self) -> None:
            self.seeded_options_at_call: list[dict[str, object]] = []

        def build_chat_response(self, **_kwargs):
            self.seeded_options_at_call = list(
                getattr(self, "_recent_youtube_video_options", [])
            )
            return SimpleNamespace(
                text="selection handled",
                routing_metadata=None,
                action_preview=None,
                tool_traces=[],
                evidence=[],
            )

    selection_controller = _SelectionController()
    controllers = iter([_RecentVideosController(), selection_controller])
    service._build_chat_controller = lambda _thread_id, **_kwargs: next(controllers)  # type: ignore[method-assign]

    CockpitService.chat_stream(
        service,
        message="kneppy invests recent videos",
        session_id="session-youtube",
    )
    CockpitService.chat_stream(
        service,
        message="ingest most recent video",
        session_id="session-youtube",
    )

    assert selection_controller.seeded_options_at_call == [
        {
            "position": 1,
            "title": "Status of My Trades",
            "webpage_url": "https://www.youtube.com/watch?v=ULVlVUSSSkI",
            "video_id": "ULVlVUSSSkI",
            "scores": {"overall": 0.88},
        }
    ]


def test_chat_stream_clears_recent_youtube_options_after_empty_lookup() -> None:
    service = CockpitService.__new__(CockpitService)
    _prime_service(service)
    service.state_store = _FakeStateStore()
    service._recent_youtube_video_options_by_thread = {
        "session-youtube": [
            {
                "position": 1,
                "title": "Old video",
                "webpage_url": "https://www.youtube.com/watch?v=old11111111",
            }
        ]
    }

    class _EmptyRecentVideosController:
        _hybrid_router = None

        def build_chat_response(self, **_kwargs):
            return SimpleNamespace(
                text="No recent videos found.",
                routing_metadata=None,
                action_preview=None,
                tool_traces=[],
                evidence=[
                    {
                        "tool": "check_youtube_channel_recent_videos",
                        "result": {"ok": True, "videos": []},
                    }
                ],
            )

    service._build_chat_controller = (
        lambda _thread_id, **_kwargs: _EmptyRecentVideosController()
    )  # type: ignore[method-assign]

    CockpitService.chat_stream(
        service,
        message="other channel recent videos",
        session_id="session-youtube",
    )

    assert service._recent_youtube_video_options_by_thread == {}


def test_chat_stream_defaults_blank_session_to_global_thread() -> None:
    service = CockpitService.__new__(CockpitService)
    _prime_service(service)
    service.state_store = _FakeStateStore()
    controller = _FakeController("Hello")
    service.chat_controller = controller
    service._build_chat_controller = lambda thread_id, **_kwargs: controller  # type: ignore[method-assign]

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
    service._build_chat_controller = lambda thread_id, **_kwargs: controller  # type: ignore[method-assign]

    response = CockpitService.chat_stream(
        service,
        message="tell me about BHP",
        session_id="session-model-meta",
        model="model:qwen3.5-35b-a3b",
    )

    assert service.llm_client.model == "model:qwen3.5-35b-a3b"
    assert response.routing_metadata["model"] == "model:qwen3.5-35b-a3b"
    assert response.routing_metadata["source"] == "local"
    assert response.routing_metadata["latency_ms"] >= 1
    assert response.routing_metadata["cost_usd"] == 0.0


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
    service._build_chat_controller = lambda thread_id, **_kwargs: controller  # type: ignore[method-assign]

    response = CockpitService.chat_stream(
        service,
        message="/cloud tell me about AGL",
        session_id="session-last-attempt",
    )

    assert "Error code: 529" in response.text
    assert response.routing_metadata["source"] == "api"
    assert response.routing_metadata["model"] == "claude-sonnet-test"
    assert response.routing_metadata["latency_ms"] >= 1
    assert response.routing_metadata["cost_usd"] == 0.0
    assert response.routing_metadata["routing_reason"] == "force:api"


def test_chat_stream_applies_api_default_backend_side_to_plain_turn() -> None:
    service = CockpitService.__new__(CockpitService)
    _prime_service(service)
    service.state_store = _FakeStateStore({"api_default_enabled": "true"})
    service.llm_client = _FakeLlmClient("model:qwen3.5-35b-a3b")
    controller = _FakeController("API default routed.")
    service._build_chat_controller = lambda thread_id, **_kwargs: controller  # type: ignore[method-assign]
    statuses: list[str] = []

    response = CockpitService.chat_stream(
        service,
        message="tell me about BHP",
        session_id="session-api-default",
        on_status=statuses.append,
    )

    assert response.text == "API default routed."
    assert controller.calls[0]["message"] == "/cloud tell me about BHP"
    assert "API default active - local LLM routing disabled" in statuses
    saved = service._recent_turn_diagnostics["session-api-default"][-1]
    assert saved["request"]["api_default_applied"] is True


def test_chat_stream_api_default_overrides_local_prefix_before_controller() -> None:
    service = CockpitService.__new__(CockpitService)
    _prime_service(service)
    service.state_store = _FakeStateStore({"api_default_enabled": "true"})
    service.llm_client = _FakeLlmClient("model:qwen3.5-35b-a3b")
    controller = _FakeController("Local prefix overridden.")
    service._build_chat_controller = lambda thread_id, **_kwargs: controller  # type: ignore[method-assign]

    CockpitService.chat_stream(
        service,
        message="/local tell me about BHP",
        session_id="session-api-default-local-prefix",
    )

    assert controller.calls[0]["message"] == "/cloud tell me about BHP"


def test_chat_stream_api_default_preserves_non_routing_slash_commands() -> None:
    service = CockpitService.__new__(CockpitService)
    _prime_service(service)
    service.state_store = _FakeStateStore({"api_default_enabled": "true"})
    service.llm_client = _FakeLlmClient("model:qwen3.5-35b-a3b")
    controller = _FakeController("Sources listed.")
    service._build_chat_controller = lambda thread_id, **_kwargs: controller  # type: ignore[method-assign]
    statuses: list[str] = []

    CockpitService.chat_stream(
        service,
        message="/sources list",
        session_id="session-api-default-slash-command",
        on_status=statuses.append,
    )

    assert controller.calls[0]["message"] == "/sources list"
    assert "API default active - local LLM routing disabled" not in statuses
    saved = service._recent_turn_diagnostics["session-api-default-slash-command"][-1]
    assert saved["request"]["api_default_applied"] is False


def test_chat_stream_marks_anthropic_credit_error_as_provider_error() -> None:
    service = CockpitService.__new__(CockpitService)
    _prime_service(service)
    service.state_store = _FakeStateStore()
    service.llm_client = _FakeLlmClient("model:qwen3.5-35b-a3b")
    controller = _FakeController(
        "I encountered an error communicating with the language model: "
        "Your credit balance is too low to access the Anthropic API. "
        "Please go to Plans & Billing to upgrade or purchase credits."
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
    service._build_chat_controller = lambda thread_id, **_kwargs: controller  # type: ignore[method-assign]
    statuses: list[str] = []

    response = CockpitService.chat_stream(
        service,
        message="/cloud tell me about AGL",
        session_id="session-credit-error",
        on_status=statuses.append,
    )

    provider_error = response.routing_metadata["provider_error"]
    assert provider_error["provider"] == "anthropic"
    assert provider_error["code"] == "billing_insufficient_credit"
    assert provider_error["severity"] == "action_required"
    assert "Top up Anthropic credits" in provider_error["message"]
    assert statuses[-1] == "Claude API billing action required: top up Anthropic credits."


def test_chat_stream_emits_model_switch_status_events() -> None:
    service = CockpitService.__new__(CockpitService)
    _prime_service(service)
    service.state_store = _FakeStateStore()
    service.llm_client = _FakeLlmClient("model:gpt-oss-20b")
    controller = _FakeController("Switch completed.")
    service._build_chat_controller = lambda thread_id, **_kwargs: controller  # type: ignore[method-assign]

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
    service._build_chat_controller = lambda thread_id, **_kwargs: controller  # type: ignore[method-assign]

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
    assert statuses == ["Routing to API: claude-sonnet-test (extraction_active)"]
    assert response.routing_metadata["source"] == "api"
    assert response.routing_metadata["model"] == "claude-sonnet-test"
    assert response.routing_metadata["routing_reason"] == "extraction_active"


def test_chat_stream_records_response_mode_in_turn_diagnostics() -> None:
    service = CockpitService.__new__(CockpitService)
    _prime_service(service)
    service.state_store = _FakeStateStore()
    controller = _FakeControllerWithMode(
        text="Deep answer.",
        mode="deep_analysis",
        prompt="prompt excerpt",
    )
    service._build_chat_controller = lambda thread_id, **_kwargs: controller  # type: ignore[method-assign]

    response = CockpitService.chat_stream(
        service,
        message="deep dive",
        session_id="session-deep",
    )

    assert response.text == "Deep answer."
    saved = service._recent_turn_diagnostics["session-deep"][-1]
    assert saved["response_mode"] == "deep_analysis"
    assert saved["prompt"] == "prompt excerpt"


def test_refresh_global_chat_controller_reloads_when_routing_policy_changes(
    monkeypatch,
) -> None:
    service = CockpitService.__new__(CockpitService)
    _prime_service(service)
    service.repo_root = Path("/tmp")
    service._config_path = Path("/tmp/config/cockpit.yaml")
    service._runtime_profile = "default"
    service._runtime_read_only = False
    service._runtime_no_web = False
    service.llm_client = SimpleNamespace(model="model:qwen3.5-35b-a3b")
    service.tool_router = object()
    service.action_registry = object()
    service.state_store = object()
    service.query_orchestrator = None
    service.llm_timeout_seconds = 120.0
    service.config = {
        "cockpit_llm": {"hybrid_router_policy": "local_preferred"},
        "llm": {"timeout_seconds": 120},
    }
    service.chat_controller = SimpleNamespace(
        _hybrid_router=SimpleNamespace(_policy="local_preferred", _api=None)
    )

    monkeypatch.setattr("app.services.cockpit_service.load_config", lambda _path: {})
    monkeypatch.setattr(
        "app.services.cockpit_service.apply_runtime_flags",
        lambda _cfg, _flags: {
            "cockpit_llm": {"hybrid_router_policy": "api_preferred"},
            "llm": {"timeout_seconds": 300},
        },
    )
    monkeypatch.setattr(
        "app.services.cockpit_service.effective_anthropic_api_key",
        lambda _cm: "non-empty-key",
    )

    created: dict[str, object] = {}

    class _FakeChatController:
        def __init__(self, **kwargs):
            created.update(kwargs)
            self._hybrid_router = SimpleNamespace(
                _policy=kwargs["cockpit_llm"]["hybrid_router_policy"],
                _api=object(),
            )

    monkeypatch.setattr(
        "app.services.cockpit_service.ChatController", _FakeChatController
    )

    CockpitService._refresh_global_chat_controller_if_needed(service)

    assert created["thread_id"] == "global-main"
    assert created["llm_timeout_seconds"] == 300.0
    assert service.llm_timeout_seconds == 300.0
    assert service.config["cockpit_llm"]["hybrid_router_policy"] == "api_preferred"
    assert service.chat_controller._hybrid_router._policy == "api_preferred"


def test_refresh_global_chat_controller_uses_operator_routing_override(
    monkeypatch,
) -> None:
    service = CockpitService.__new__(CockpitService)
    _prime_service(service)
    service.repo_root = Path("/tmp")
    service._config_path = Path("/tmp/config/cockpit.yaml")
    service._runtime_profile = "default"
    service._runtime_read_only = False
    service._runtime_no_web = False
    service.llm_client = SimpleNamespace(model="model:qwen3.5-35b-a3b")
    service.tool_router = object()
    service.action_registry = object()
    service.query_orchestrator = None
    service.llm_timeout_seconds = 120.0
    service.config = {
        "cockpit_llm": {"hybrid_router_policy": "api_preferred"},
        "llm": {"timeout_seconds": 120},
    }
    service.chat_controller = SimpleNamespace(
        _hybrid_router=SimpleNamespace(_policy="api_preferred", _api=object())
    )

    class _StateStore:
        def get_preference(self, key: str, default: str = "") -> str:
            return "local_only" if key == "chat_routing_policy_override" else default

    service.state_store = _StateStore()

    monkeypatch.setattr("app.services.cockpit_service.load_config", lambda _path: {})
    monkeypatch.setattr(
        "app.services.cockpit_service.apply_runtime_flags",
        lambda _cfg, _flags: {
            "cockpit_llm": {"hybrid_router_policy": "api_preferred"},
            "llm": {"timeout_seconds": 300},
        },
    )
    monkeypatch.setattr(
        "app.services.cockpit_service.effective_anthropic_api_key",
        lambda _cm: "non-empty-key",
    )

    class _FakeChatController:
        def __init__(self, **kwargs):
            self._hybrid_router = SimpleNamespace(
                _policy=kwargs["cockpit_llm"]["hybrid_router_policy"],
                _api=object(),
            )

    monkeypatch.setattr(
        "app.services.cockpit_service.ChatController", _FakeChatController
    )

    CockpitService._refresh_global_chat_controller_if_needed(service)

    assert service.config["cockpit_llm"]["hybrid_router_policy"] == "local_only"
    assert service.chat_controller._hybrid_router._policy == "local_only"


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
    projected_rows = (
        {
            "revenue": "128458000",
            "ebit": None,
            "net_debt": None,
            "np_attributable": "-73500000",
            "shares_outstanding": "467479000",
            "capex": "-14026000",
            "confidence_metrics": None,
            "source_document_id": str(doc_a),
        },
    )

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
                raise AssertionError("stale legacy financials must not be queried")
            return _FailedDocQuery()

        def close(self) -> None:
            return None

    monkeypatch.setattr("app.services.cockpit_service.SessionLocal", lambda: _FakeDb())
    monkeypatch.setattr(
        "app.services.cockpit_service.stable_financial_profile",
        lambda db, *, ticker: projected_rows,
    )

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
    projected_rows = (
        {
            "revenue": "44070000",
            "ebit": None,
            "net_debt": None,
            "np_attributable": "46786000",
            "shares_outstanding": "467309000",
            "capex": "-6165000",
            "confidence_metrics": 0.7,
            "source_document_id": str(doc_b),
        },
    )

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
                raise AssertionError("stale legacy financials must not be queried")
            return _FailedDocQuery()

        def close(self) -> None:
            return None

    monkeypatch.setattr("app.services.cockpit_service.SessionLocal", lambda: _FakeDb())
    monkeypatch.setattr(
        "app.services.cockpit_service.stable_financial_profile",
        lambda db, *, ticker: projected_rows,
    )

    result = CockpitService.get_diagnostic_matrix(service, "evaluation", "EOS")

    assert result["entities"][0]["metrics"]["REVENUE"] == "abstain"
    assert result["entities"][0]["metrics"]["CAPEX"] == "abstain"
    assert result["entities"][0]["metrics"]["EPS"] == "abstain"


def test_get_diagnostic_matrix_marks_failed_when_source_document_extraction_failed(
    monkeypatch,
) -> None:
    service = CockpitService.__new__(CockpitService)
    doc_id = uuid.uuid4()
    projected_rows = (
        {
            "revenue": None,
            "ebit": None,
            "net_debt": None,
            "np_attributable": None,
            "shares_outstanding": None,
            "capex": None,
            "confidence_metrics": None,
            "source_document_id": str(doc_id),
        },
    )

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
                raise AssertionError("stale legacy financials must not be queried")
            return _FailedDocQuery()

        def close(self) -> None:
            return None

    monkeypatch.setattr("app.services.cockpit_service.SessionLocal", lambda: _FakeDb())
    monkeypatch.setattr(
        "app.services.cockpit_service.stable_financial_profile",
        lambda db, *, ticker: projected_rows,
    )

    result = CockpitService.get_diagnostic_matrix(service, "extraction", "EOS")

    assert result["entities"][0]["metrics"]["REVENUE"] == "failed"


@pytest.mark.parametrize("ticker", ["EOS", None])
def test_get_intel_pulse_stats_uses_canonical_financial_rows(
    monkeypatch, ticker
) -> None:
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
            self._scalars = iter([documents_count, 42])

        def query(self, *args, **kwargs):
            if len(args) >= 2:
                return _JoinedFailureQuery()
            target = args[0] if args else None
            if getattr(target, "name", None) == "count":
                return _ScalarQuery(next(self._scalars))
            if target is not None and getattr(target, "__name__", None) == "ASXPeriodicFinancial":
                raise AssertionError("stale legacy financials must not be queried")
            return _CountQuery()

        def close(self) -> None:
            return None

    monkeypatch.setattr(
        "app.services.cockpit_service.SessionLocal",
        lambda: _FakeDb(),
    )
    monkeypatch.setattr(
        "app.services.cockpit_service.stable_financial_profiles",
        lambda db, *, ticker: tuple(vars(row) for row in financial_rows),
    )

    result = CockpitService.get_intel_pulse_stats(service, ticker)

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
