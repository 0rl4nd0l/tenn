import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))


from app.services.multipass_extraction import _validate_gate  # noqa: E402


def _base_wrapper_payload() -> dict[str, object]:
    return {
        "document_subtype": "4D",
        "document_title": "Appendix 4D half-year report",
        "period_end": "2024-06-30",
        "period_type": "H",
        "scale": "thousands",
        "currency": "AUD",
        "confidence_metrics": 0.91,
        "source_bound": {
            "period_end": "2024-06-30",
            "period_type": "H",
            "scale": "thousands",
            "currency": "AUD",
        },
        "wrapper_disclosures": [
            "Net tangible assets per security",
            "Dividends / distributions",
            "Record date for determining entitlement to the dividend",
            "Details of associates and joint ventures entities",
        ],
        "row_refs": {
            "revenue": "Revenue",
            "np_attributable": "Net profit after income tax expense from ordinary activities",
        },
        "provenance": {
            "revenue": "income_statement:page_1:Revenue",
            "np_attributable": "income_statement:page_1:Net profit after income tax expense from ordinary activities",
        },
        "metrics": {
            "revenue": 150_804_000,
            "ebit": None,
            "np_attributable": 15_463_000,
            "operating_cf": None,
            "investing_cf": None,
            "financing_cf": None,
            "capex": None,
            "cash_end": None,
            "net_debt": None,
            "shares_outstanding": None,
        },
    }


def test_appendix_4d_wrapper_passes_with_two_canonical_metrics_and_wrapper_disclosures():
    status, error = _validate_gate(_base_wrapper_payload())

    assert status == "ok"
    assert error is None


def test_appendix_4d_wrapper_fails_without_wrapper_disclosure_evidence():
    payload = _base_wrapper_payload()
    payload.pop("wrapper_disclosures")

    status, error = _validate_gate(payload)

    assert status == "failed"
    assert error == "validation_gate:wrapper_missing_disclosure_evidence"


def test_appendix_4d_wrapper_fails_without_source_bound_context():
    payload = _base_wrapper_payload()
    payload.pop("source_bound")

    status, error = _validate_gate(payload)

    assert status == "failed"
    assert error == "validation_gate:wrapper_missing_source_bound_context"


def test_appendix_4d_wrapper_fails_without_period_end():
    payload = _base_wrapper_payload()
    payload.pop("period_end")

    status, error = _validate_gate(payload)

    assert status == "failed"
    assert error == "validation_gate:missing_period_end"


def test_appendix_4d_wrapper_fails_with_unknown_scale():
    payload = _base_wrapper_payload()
    payload["scale"] = "unknown"

    status, error = _validate_gate(payload)

    assert status == "failed"
    assert error == "validation_gate:scale_unknown"


def test_appendix_4d_wrapper_fails_when_required_canonical_metric_is_missing():
    payload = _base_wrapper_payload()
    payload["metrics"] = {key: None for key in payload["metrics"]}  # type: ignore[index]
    payload["metrics"]["revenue"] = 150_804_000  # type: ignore[index]

    status, error = _validate_gate(payload)

    assert status == "failed"
    assert error == "validation_gate:wrapper_missing_required_canonical_metrics"
