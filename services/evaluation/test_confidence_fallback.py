from services.evaluation.confidence import _defer_non_financial_unknown_fallback


def test_defer_is_disabled_on_failed_extractor() -> None:
    # When the upstream extractor failed, we should not defer fallback.
    assert (
        _defer_non_financial_unknown_fallback(
            doc_type="unknown",
            is_financial=False,
            canonical_metric_count=0,
            row_count=0,
            coverage=0.0,
            anomaly={"has_anomaly": False, "severity": "low", "flags": []},
            method_status="failed",
        )
        is False
    )

