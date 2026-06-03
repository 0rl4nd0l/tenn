import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))


from app.services.multipass_extraction import _validate_gate  # noqa: E402


def _base_ordinary_payload(period_type: str) -> dict[str, object]:
    return {
        "period_end": "2025-12-31",
        "period_type": period_type,
        "scale": "thousands",
        "currency": "AUD",
        "confidence_metrics": 0.9,
        "metrics": {
            "revenue": 10_000.0,
            "ebit": 2_000.0,
            "np_attributable": None,
            "operating_cf": None,
            "investing_cf": None,
            "financing_cf": None,
            "capex": None,
            "cash_end": None,
            "net_debt": None,
            "shares_outstanding": None,
        },
    }


def test_ordinary_half_year_reports_still_require_the_normal_metric_minimum():
    payload = _base_ordinary_payload("H")

    status, error = _validate_gate(payload)

    assert status == "failed"
    assert error == "validation_gate:insufficient_metrics:2"


def test_ordinary_half_year_reports_pass_with_three_canonical_metrics():
    payload = _base_ordinary_payload("H")
    payload["metrics"]["np_attributable"] = 500.0  # type: ignore[index]

    status, error = _validate_gate(payload)

    assert status == "ok"
    assert error is None


def test_ordinary_annual_reports_still_require_the_normal_metric_minimum():
    payload = _base_ordinary_payload("A")

    status, error = _validate_gate(payload)

    assert status == "failed"
    assert error == "validation_gate:insufficient_metrics:2"
