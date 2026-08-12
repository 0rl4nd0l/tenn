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
            normalized_value=item.normalized_value,
            period_type=by_id[item.document_id].period_type,
            period_end=by_id[item.document_id].period_end,
            currency=item.currency,
            source_sha256=by_id[item.document_id].source_sha256,
        )
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


def test_wrong_period_and_unbound_source_are_incorrect_and_fail_gate() -> None:
    documents = _documents()
    expectations = _expectations(documents)
    actuals = _actuals(documents, expectations)
    actuals[0] = replace(actuals[0], period_end="2024-06-30")
    actuals[1] = replace(actuals[1], source_sha256="f" * 64)

    result = score_benchmark(documents, expectations, actuals)

    assert result.outcome_counts["incorrect"] == 2
    assert result.period_swap_count == 1
    assert result.source_binding_rate == 198 / 200
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
    expectations[0] = replace(
        expectations[0],
        applicability="unresolved",
        adjudication_status="unresolved",
        normalized_value=None,
        evidence_location=None,
    )
    actuals = _actuals(documents[:-1], expectations[:190])

    result = score_benchmark(documents, expectations, actuals)

    assert result.outcome_counts["data_missing"] == 10
    assert result.outcome_counts["unsupported"] == 1
    assert result.applicable_cells == 199
    assert result.gate_passed is False


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda docs, expected: docs.pop(), "exactly 20 documents"),
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
    ],
)
def test_contract_fails_closed(mutation, message: str) -> None:
    documents = _documents()
    expectations = _expectations(documents)
    mutation(documents, expectations)

    with pytest.raises(BenchmarkContractError, match=message):
        score_benchmark(documents, expectations, [])
