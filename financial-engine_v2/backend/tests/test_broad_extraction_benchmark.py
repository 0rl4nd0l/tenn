from dataclasses import replace

import pytest
from app.services.broad_extraction_benchmark import (
    METRICS,
    ActualCell,
    BenchmarkContractError,
    CorpusDocument,
    ExpectedCell,
    score_benchmark,
)


def _documents() -> list[CorpusDocument]:
    return [
        CorpusDocument(
            document_id=f"doc-{index:02d}",
            issuer_id=f"issuer-{index:02d}",
            document_class="annual_report",
            period_type="A",
            period_end="2025-06-30",
            admission_status="admitted",
            source_path=f"sources/doc-{index:02d}.pdf",
            source_sha256=f"{index:064x}",
        )
        for index in range(1, 21)
    ]


def _expectations(documents: list[CorpusDocument]) -> list[ExpectedCell]:
    return [
        ExpectedCell(
            document_id=document.document_id,
            metric=metric,
            applicability="applicable",
            adjudication_status="verified",
            raw_value="100",
            raw_unit="AUD millions",
            currency="AUD",
            normalized_value="100000000",
            evidence_location="page=1;table=primary;row=metric;column=current",
        )
        for document in documents
        for metric in METRICS
    ]


def _actuals(
    documents: list[CorpusDocument], expectations: list[ExpectedCell]
) -> list[ActualCell]:
    by_id = {item.document_id: item for item in documents}
    return [
        ActualCell(
            document_id=item.document_id,
            metric=item.metric,
            status="accepted",
            raw_value=item.raw_value,
            raw_unit=item.raw_unit,
            normalized_value=item.normalized_value,
            period_type=by_id[item.document_id].period_type,
            period_end=by_id[item.document_id].period_end,
            currency=item.currency,
            source_sha256=by_id[item.document_id].source_sha256,
            evidence_location=item.evidence_location,
        )
        for item in expectations
    ]


def _mark_expectations_unresolved(
    expectations: list[ExpectedCell], document_id: str
) -> list[ExpectedCell]:
    return [
        replace(
            item,
            adjudication_status="unresolved",
            raw_value=None,
            raw_unit=None,
            currency=None,
            normalized_value=None,
            evidence_location=None,
        )
        if item.document_id == document_id
        else item
        for item in expectations
    ]


def test_complete_exact_source_bound_corpus_passes_gate() -> None:
    documents = _documents()
    expectations = _expectations(documents)

    result = score_benchmark(documents, expectations, _actuals(documents, expectations))

    assert result.document_count == 20
    assert result.applicable_cells == 200
    assert result.outcome_counts["correct"] == 200
    assert result.coverage == 1.0
    assert result.exact_accuracy == 1.0
    assert result.source_binding_rate == 1.0
    assert result.period_swap_count == 0
    assert result.gate_passed is True
    assert result.rows[0]["issuer_id"] == "issuer-01"
    assert result.rows[0]["document_class"] == "annual_report"


def test_wrong_period_and_unbound_source_are_incorrect_and_fail_gate() -> None:
    documents = _documents()
    expectations = _expectations(documents)
    actuals = _actuals(documents, expectations)
    actuals[0] = replace(actuals[0], period_end="2024-06-30")
    actuals[1] = replace(actuals[1], source_sha256="f" * 64)

    result = score_benchmark(documents, expectations, actuals)

    assert result.outcome_counts["incorrect"] == 2
    assert result.period_swap_count == 1
    assert result.source_binding_rate == 199 / 200
    assert result.gate_passed is False


def test_data_missing_and_unresolved_are_explicit_not_false_failures() -> None:
    documents = _documents()
    documents[-1] = replace(
        documents[-1],
        admission_status="data_missing",
        source_path=None,
        source_sha256=None,
    )
    expectations = _expectations(documents)
    expectations = _mark_expectations_unresolved(
        expectations, documents[-1].document_id
    )
    expectations[0] = replace(
        expectations[0],
        applicability="unresolved",
        adjudication_status="unresolved",
        normalized_value=None,
        evidence_location=None,
    )
    actuals = _actuals(documents[:-1], expectations[:190])
    actuals[0] = replace(
        actuals[0],
        status="unsupported",
        normalized_value=None,
        period_type=None,
        period_end=None,
        currency=None,
        source_sha256=None,
    )

    result = score_benchmark(documents, expectations, actuals)

    assert result.outcome_counts["data_missing"] == 10
    assert result.outcome_counts["unsupported"] == 1
    assert result.applicable_cells == 199
    assert result.gate_passed is False


def test_data_missing_document_cannot_supply_extraction_observations() -> None:
    documents = _documents()
    missing_document = replace(
        documents[-1],
        admission_status="data_missing",
        source_path=None,
        source_sha256=None,
    )
    documents[-1] = missing_document
    expectations = _mark_expectations_unresolved(
        _expectations(documents), missing_document.document_id
    )
    actuals = _actuals(documents[:-1], expectations[:-10])
    actuals.append(
        ActualCell(
            document_id=missing_document.document_id,
            metric="revenue",
            status="accepted",
            raw_value="100",
            raw_unit="AUD millions",
            normalized_value="100000000",
            period_type="A",
            period_end="2025-06-30",
            currency="AUD",
            source_sha256="f" * 64,
            evidence_location="page=1;table=primary;row=metric;column=current",
        )
    )

    with pytest.raises(
        BenchmarkContractError,
        match="DATA_MISSING document cannot have extraction observations",
    ):
        score_benchmark(documents, expectations, actuals)


def test_data_missing_document_cannot_claim_verified_expectations() -> None:
    documents = _documents()
    documents[-1] = replace(
        documents[-1],
        admission_status="data_missing",
        source_path=None,
        source_sha256=None,
    )

    with pytest.raises(
        BenchmarkContractError,
        match="DATA_MISSING document cannot have verified expectations",
    ):
        score_benchmark(documents, _expectations(documents), [])


def test_wrong_scale_is_incorrect_when_normalized_value_matches() -> None:
    documents = _documents()
    expectations = _expectations(documents)
    actuals = _actuals(documents, expectations)
    actuals[0] = replace(actuals[0], raw_unit="AUD thousands")

    result = score_benchmark(documents, expectations, actuals)

    assert result.outcome_counts["incorrect"] == 1
    assert result.raw_value_mismatch_count == 0
    assert result.scale_mismatch_count == 1
    assert result.normalized_value_mismatch_count == 0


def test_wrong_currency_is_reported_separately() -> None:
    documents = _documents()
    expectations = _expectations(documents)
    actuals = _actuals(documents, expectations)
    actuals[0] = replace(actuals[0], currency="USD")

    result = score_benchmark(documents, expectations, actuals)

    assert result.outcome_counts["incorrect"] == 1
    assert result.currency_mismatch_count == 1


def test_wrong_evidence_location_does_not_count_as_source_bound_truth() -> None:
    documents = _documents()
    expectations = _expectations(documents)
    actuals = _actuals(documents, expectations)
    actuals[0] = replace(actuals[0], evidence_location="page=2;row=narrative")

    result = score_benchmark(documents, expectations, actuals)

    assert result.outcome_counts["incorrect"] == 1
    assert result.source_binding_rate == 1.0
    assert result.provenance_binding_rate == 199 / 200
    assert result.provenance_mismatch_count == 1


def test_previously_correct_cell_becoming_wrong_is_a_regression() -> None:
    documents = _documents()
    expectations = _expectations(documents)
    baseline = _actuals(documents, expectations)
    candidate = _actuals(documents, expectations)
    candidate[0] = replace(candidate[0], raw_unit="AUD thousands")

    result = score_benchmark(
        documents,
        expectations,
        candidate,
        baseline_actuals=baseline,
    )

    assert result.regression_count == 1
    revenue_row = next(
        row
        for row in result.rows
        if row["document_id"] == "doc-01" and row["metric"] == "revenue"
    )
    assert revenue_row["regressed"] is True
    assert result.gate_passed is False


def test_correct_recovery_from_baseline_abstention_is_counted() -> None:
    documents = _documents()
    expectations = _expectations(documents)
    baseline = _actuals(documents, expectations)
    baseline[0] = replace(
        baseline[0],
        status="abstained",
        raw_value=None,
        raw_unit=None,
        normalized_value=None,
        period_type=None,
        period_end=None,
        currency=None,
        source_sha256=None,
        evidence_location=None,
    )

    result = score_benchmark(
        documents,
        expectations,
        _actuals(documents, expectations),
        baseline_actuals=baseline,
    )

    assert result.newly_correct_count == 1
    assert result.regression_count == 0
    assert result.repair_gate_passed is True


def test_unchanged_candidate_does_not_claim_repair_progress() -> None:
    documents = _documents()
    expectations = _expectations(documents)
    actuals = _actuals(documents, expectations)

    result = score_benchmark(
        documents,
        expectations,
        actuals,
        baseline_actuals=actuals,
    )

    assert result.gate_passed is True
    assert result.baseline_outcome_counts["correct"] == 200
    assert result.newly_correct_count == 0
    assert result.repair_gate_passed is False


def test_repair_gate_rejects_a_new_identity_failure_class() -> None:
    documents = _documents()
    expectations = _expectations(documents)
    baseline = _actuals(documents, expectations)
    baseline[0] = replace(baseline[0], currency="USD")
    baseline[1] = replace(
        baseline[1],
        status="abstained",
        raw_value=None,
        raw_unit=None,
        normalized_value=None,
        period_type=None,
        period_end=None,
        currency=None,
        source_sha256=None,
        evidence_location=None,
    )
    candidate = _actuals(documents, expectations)
    candidate[1] = replace(candidate[1], raw_unit="AUD thousands")

    result = score_benchmark(
        documents,
        expectations,
        candidate,
        baseline_actuals=baseline,
    )

    assert result.newly_correct_count == 1
    assert result.regression_count == 0
    assert result.outcome_counts["incorrect"] == 1
    assert result.baseline_outcome_counts["incorrect"] == 1
    assert result.repair_gate_passed is False


def test_accepted_observation_requires_finite_numeric_identity() -> None:
    documents = _documents()
    expectations = _expectations(documents)
    actuals = _actuals(documents, expectations)
    actuals[0] = replace(actuals[0], raw_value="NaN")

    with pytest.raises(
        BenchmarkContractError,
        match="accepted result has invalid raw or normalized numeric value",
    ):
        score_benchmark(documents, expectations, actuals)


def test_accepted_observation_requires_valid_source_hash() -> None:
    documents = _documents()
    expectations = _expectations(documents)
    actuals = _actuals(documents, expectations)
    actuals[0] = replace(actuals[0], source_sha256="not-a-sha256")

    with pytest.raises(
        BenchmarkContractError,
        match="accepted result has invalid source SHA-256",
    ):
        score_benchmark(documents, expectations, actuals)


def test_accepted_observation_requires_valid_period_identity() -> None:
    documents = _documents()
    expectations = _expectations(documents)
    actuals = _actuals(documents, expectations)
    actuals[0] = replace(actuals[0], period_type="FY", period_end="2025-02-30")

    with pytest.raises(
        BenchmarkContractError,
        match="accepted result has invalid period identity",
    ):
        score_benchmark(documents, expectations, actuals)


def test_accepted_observation_requires_valid_currency_code() -> None:
    documents = _documents()
    expectations = _expectations(documents)
    actuals = _actuals(documents, expectations)
    actuals[0] = replace(actuals[0], currency="aud")

    with pytest.raises(
        BenchmarkContractError,
        match="accepted result has invalid currency",
    ):
        score_benchmark(documents, expectations, actuals)


def test_accepted_observation_requires_nonempty_unit_and_evidence() -> None:
    documents = _documents()
    expectations = _expectations(documents)
    actuals = _actuals(documents, expectations)
    actuals[0] = replace(actuals[0], raw_unit="")

    with pytest.raises(
        BenchmarkContractError,
        match="accepted result requires non-empty raw unit and evidence",
    ):
        score_benchmark(documents, expectations, actuals)


def test_verified_monetary_expectation_requires_currency() -> None:
    documents = _documents()
    expectations = _expectations(documents)
    expectations[0] = replace(expectations[0], currency=None)

    with pytest.raises(
        BenchmarkContractError,
        match="verified monetary cell requires currency",
    ):
        score_benchmark(documents, expectations, [])


def test_malformed_runtime_document_type_fails_with_contract_error() -> None:
    documents = _documents()
    documents[0] = object()  # type: ignore[assignment]

    with pytest.raises(BenchmarkContractError, match="expected CorpusDocument"):
        score_benchmark(documents, [], [])


def test_malformed_runtime_document_fields_fail_with_contract_error() -> None:
    documents = _documents()
    documents[0] = replace(documents[0], document_id=[])  # type: ignore[arg-type]

    with pytest.raises(
        BenchmarkContractError,
        match="invalid document or issuer identifier",
    ):
        score_benchmark(documents, [], [])


def test_baseline_validation_error_identifies_comparison_side() -> None:
    documents = _documents()
    expectations = _expectations(documents)
    baseline = _actuals(documents, expectations)
    baseline[0] = replace(baseline[0], source_sha256="not-a-sha256")

    with pytest.raises(
        BenchmarkContractError,
        match=r"baseline_actuals\[0\]: accepted result has invalid source SHA-256",
    ):
        score_benchmark(
            documents,
            expectations,
            _actuals(documents, expectations),
            baseline_actuals=baseline,
        )


def test_accepted_inapplicable_metric_is_incorrect_not_unsupported() -> None:
    documents = _documents()
    expectations = _expectations(documents)
    expectations[0] = replace(
        expectations[0],
        applicability="inapplicable",
        adjudication_status="verified",
        raw_value=None,
        raw_unit=None,
        currency=None,
        normalized_value=None,
        evidence_location="page=1;reason=not_disclosed",
    )
    actuals = _actuals(documents, _expectations(documents))

    result = score_benchmark(documents, expectations, actuals)

    assert result.outcome_counts["incorrect"] == 1
    assert result.outcome_counts["unsupported"] == 0
    assert result.exact_accuracy == 199 / 200


def test_data_missing_document_blocks_gate_even_when_its_cells_are_inapplicable() -> (
    None
):
    documents = _documents()
    documents[-1] = replace(
        documents[-1],
        admission_status="data_missing",
        source_path=None,
        source_sha256=None,
    )
    expectations = _expectations(documents)
    expectations[-10:] = [
        replace(
            item,
            applicability="inapplicable",
            adjudication_status="unresolved",
            raw_value=None,
            raw_unit=None,
            currency=None,
            normalized_value=None,
            evidence_location="reason=source_missing",
        )
        for item in expectations[-10:]
    ]

    result = score_benchmark(
        documents,
        expectations,
        _actuals(documents[:-1], expectations[:-10]),
    )

    assert result.coverage == 1.0
    assert result.outcome_counts["data_missing"] == 10
    assert result.gate_passed is False


def test_contract_digest_binds_expectations_without_order_drift() -> None:
    documents = _documents()
    expectations = _expectations(documents)
    original = score_benchmark(documents, expectations, [])
    reordered = score_benchmark(
        reversed(documents),
        reversed(expectations),
        [],
    )
    changed_expectations = list(expectations)
    changed_expectations[0] = replace(
        changed_expectations[0], normalized_value="100000001"
    )
    changed = score_benchmark(documents, changed_expectations, [])

    assert reordered.contract_digest == original.contract_digest
    assert changed.contract_digest != original.contract_digest


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda docs, expected: docs.pop(), "exactly 20 documents"),
        (
            lambda docs, expected: docs.__setitem__(
                0, replace(docs[0], period_end="2025-02-30")
            ),
            "invalid period end",
        ),
        (
            lambda docs, expected: docs.__setitem__(
                0, replace(docs[0], document_class="")
            ),
            "invalid document class",
        ),
        (
            lambda docs, expected: expected.pop(),
            "declare every document/metric cell exactly once",
        ),
        (
            lambda docs, expected: expected.__setitem__(
                0, replace(expected[0], metric="ebit")
            ),
            "outside ten-metric contract",
        ),
        (
            lambda docs, expected: expected.__setitem__(
                0, replace(expected[0], raw_unit=None)
            ),
            "lacks raw value, unit, normalized value, or evidence",
        ),
        (
            lambda docs, expected: expected.__setitem__(
                0, replace(expected[0], evidence_location="")
            ),
            "requires non-empty raw unit and evidence",
        ),
        (
            lambda docs, expected: expected.__setitem__(
                0, replace(expected[0], normalized_value="not-a-number")
            ),
            "invalid raw or normalized numeric value",
        ),
    ],
)
def test_contract_fails_closed(mutation, message: str) -> None:
    documents = _documents()
    expectations = _expectations(documents)
    mutation(documents, expectations)

    with pytest.raises(BenchmarkContractError, match=message):
        score_benchmark(documents, expectations, [])
