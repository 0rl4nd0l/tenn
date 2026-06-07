from broad_extraction_test import compute_summary


def test_compute_summary_preserves_source_noncandidate_reason():
    summary = compute_summary(
        [
            {
                "status": "failed",
                "error": "validation_gate:source_noncandidate:meeting_or_proxy_notice",
                "ticker": "EQR",
                "metrics": {},
                "non_null_metrics": 0,
                "elapsed_s": 0.1,
            }
        ]
    )

    assert summary["error_classification"] == {
        "source_noncandidate:meeting_or_proxy_notice": 1
    }


def test_compute_summary_preserves_director_interest_notice_reason():
    summary = compute_summary(
        [
            {
                "status": "failed",
                "error": "validation_gate:source_noncandidate:director_interest_notice",
                "ticker": "EOS",
                "metrics": {},
                "non_null_metrics": 0,
                "elapsed_s": 0.1,
            }
        ]
    )

    assert summary["error_classification"] == {
        "source_noncandidate:director_interest_notice": 1
    }


def test_compute_summary_keeps_other_validation_gates_grouped():
    summary = compute_summary(
        [
            {
                "status": "failed",
                "error": "validation_gate:scale_unknown",
                "ticker": "WHC",
                "metrics": {},
                "non_null_metrics": 0,
                "elapsed_s": 0.1,
            }
        ]
    )

    assert summary["error_classification"] == {"validation_gate:scale_unknown": 1}
