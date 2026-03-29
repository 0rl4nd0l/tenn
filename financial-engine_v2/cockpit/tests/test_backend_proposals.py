from __future__ import annotations

from cockpit.core.backend_proposals import (
    build_backend_access_proposal_request,
    build_backend_runtime_remediation_request,
)


class _BackendClient:
    def __init__(self, payload):
        self._payload = payload

    def capabilities(self, timeout: float = 5.0):  # noqa: ARG002
        return {"ok": True, "payload": self._payload}


def test_build_backend_runtime_remediation_request_uses_backend_proposal():
    payload = {
        "proposals": [
            {
                "id": "start_extraction_runtime",
                "target": "extraction",
                "summary": "Start or repair the extraction llama.cpp runtime",
            }
        ]
    }
    request = build_backend_runtime_remediation_request(
        _BackendClient(payload),
        action_id="metric_extraction",
        args={"ticker": "BHP"},
        error_message="Extraction endpoint unreachable at http://127.0.0.1:8002",
    )

    assert request is not None
    assert request["action_id"] == "__backend_proposal__"
    assert request["args"]["proposal_id"] == "start_extraction_runtime"


def test_build_backend_runtime_remediation_request_returns_none_without_matching_proposal():
    request = build_backend_runtime_remediation_request(
        _BackendClient({"proposals": []}),
        action_id="metric_extraction",
        args={"ticker": "BHP"},
        error_message="Extraction endpoint unreachable at http://127.0.0.1:8002",
    )

    assert request is None


def test_build_backend_access_proposal_request_uses_backend_proposal_shape():
    request = build_backend_access_proposal_request(
        "web",
        enable=True,
        resume_message="fetch https://example.com",
    )

    assert request["action_id"] == "__backend_proposal__"
    assert request["args"]["proposal_id"] == "enable_web_access"
    assert request["args"]["resume_message"] == "fetch https://example.com"
