from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from types import SimpleNamespace


class FakeQuery:
    def __init__(self, existing=None, rows=None):
        self.existing = existing
        self.rows = rows or []

    def filter(self, *_criteria):
        return self

    def first(self):
        return self.existing

    def all(self):
        return self.rows


class FakeSession:
    def __init__(self, existing=None, rows=None):
        self.added = []
        self.commits = 0
        self.existing = existing
        self.rows = rows or []
        self.executed = []

    def query(self, _model):
        return FakeQuery(self.existing, self.rows)

    def add(self, value):
        self.added.append(value)

    def execute(self, statement):
        self.executed.append(statement)
        return SimpleNamespace(rowcount=1)

    def commit(self):
        self.commits += 1


def accepted_context(document_id: uuid.UUID) -> dict:
    return {
        "_observation_extraction_status": "ok",
        "period_type": "A",
        "period_end": "2025-06-30",
        "currency": "AUD",
        "source_period_type": "A",
        "source_period_evidence": {
            "period_type": "A",
            "reason": "year_ended_source_phrase",
            "hits": [
                {
                    "period_type": "A",
                    "reason": "year_ended_source_phrase",
                    "source": "source_text",
                }
            ],
        },
        "source_period_end_evidence": {
            "period_type": "A",
            "period_end": "2025-06-30",
            "reason": "year_ended_explicit_date",
            "hits": [
                {
                    "period_type": "A",
                    "period_end": "2025-06-30",
                    "reason": "year_ended_explicit_date",
                    "source": "source_text",
                }
            ],
        },
        "metrics": {"revenue": 55_658_000_000},
        "field_provenance": {
            "revenue": {
                "metric": "revenue",
                "source": "income_statement",
                "page_number": 42,
                "row_ref": "Statutory revenue",
                "period_type": "A",
                "period_end": "2025-06-30",
                "currency": "AUD",
                "scale": "millions",
                "scale_source": "table_header",
                "source_cell": {
                    "raw_value": "55,658",
                    "row_label": "Statutory revenue",
                    "header_cell": "2025 AUD millions",
                },
            }
        },
    }


def test_accepted_revenue_is_staged_without_committing():
    from app.services.financial_observations import stage_revenue_observation

    document_id = uuid.uuid4()
    run_id = uuid.uuid4()
    session = FakeSession()

    observation = stage_revenue_observation(
        session,
        document=SimpleNamespace(document_id=document_id, ticker="BHP"),
        extraction_run=SimpleNamespace(
            run_id=run_id,
            extractor_version="multipass-v5",
        ),
        structured=accepted_context(document_id),
    )

    assert len(session.executed) == 1
    compiled = session.executed[0].compile()
    assert "ON CONFLICT" in str(compiled)
    assert "DO NOTHING" in str(compiled)
    assert observation.source_document_id == document_id
    assert observation.extraction_run_id == run_id
    assert observation.extractor_version == "multipass-v5"
    assert observation.ticker == "BHP"
    assert observation.metric == "revenue"
    assert observation.value == 55_658_000_000
    assert observation.period_end == date(2025, 6, 30)
    assert observation.period_basis == "A"
    assert observation.accounting_basis == "statutory"
    assert observation.currency == "AUD"
    assert observation.scale == "units"
    assert observation.trust_state == "accepted"
    assert observation.provenance["row_ref"] == "Statutory revenue"
    assert observation.provenance["source_scale"] == "millions"
    assert observation.provenance["source_cell"]["raw_value"] == "55,658"
    assert session.added == []
    assert session.commits == 0


def test_insert_is_conflict_safe_without_querying_or_owning_the_transaction():
    from app.services.financial_observations import stage_revenue_observation

    document_id = uuid.uuid4()
    session = FakeSession()
    session.execute = lambda statement: (
        session.executed.append(statement) or SimpleNamespace(rowcount=0)
    )
    context = accepted_context(document_id)
    context["metrics"]["revenue"] = 200

    result = stage_revenue_observation(
        session,
        document=SimpleNamespace(document_id=document_id, ticker="BHP"),
        extraction_run=SimpleNamespace(
            run_id=uuid.uuid4(), extractor_version="multipass-v5"
        ),
        structured=context,
    )

    assert result is None
    assert len(session.executed) == 1
    assert session.added == []
    assert session.commits == 0


def test_missing_or_conflicting_financial_context_abstains():
    from app.services.financial_observations import stage_revenue_observation

    document_id = uuid.uuid4()
    cases = []
    for field in (
        "period_type",
        "period_end",
        "currency",
        "source_period_type",
        "source_period_evidence",
        "source_period_end_evidence",
    ):
        payload = accepted_context(document_id)
        payload.pop(field)
        cases.append(payload)
    missing_value = accepted_context(document_id)
    missing_value["metrics"]["revenue"] = None
    cases.append(missing_value)
    missing_provenance = accepted_context(document_id)
    missing_provenance["field_provenance"].pop("revenue")
    cases.append(missing_provenance)
    wrong_document = accepted_context(document_id)
    wrong_document["field_provenance"]["revenue"]["source_document_id"] = str(
        uuid.uuid4()
    )
    cases.append(wrong_document)
    conflicting_currency = accepted_context(document_id)
    conflicting_currency["field_provenance"]["revenue"]["currency"] = "USD"
    cases.append(conflicting_currency)
    low_confidence = accepted_context(document_id)
    low_confidence["_observation_extraction_status"] = "ok_low_confidence"
    cases.append(low_confidence)
    highlights = accepted_context(document_id)
    highlights["field_provenance"]["revenue"]["source"] = "highlights"
    cases.append(highlights)
    adjusted = accepted_context(document_id)
    adjusted["field_provenance"]["revenue"]["row_ref"] = "Adjusted revenue"
    cases.append(adjusted)
    inferred_period = accepted_context(document_id)
    inferred_period["source_period_evidence"] = {
        "period_type": "A",
        "reason": "document_type",
    }
    cases.append(inferred_period)

    for context in cases:
        session = FakeSession()
        assert (
            stage_revenue_observation(
                session,
                document=SimpleNamespace(document_id=document_id, ticker="BHP"),
                extraction_run=SimpleNamespace(
                    run_id=uuid.uuid4(), extractor_version="multipass-v5"
                ),
                structured=context,
            )
            is None
        )
        assert session.added == []
        assert session.commits == 0


def test_closed_context_vocabularies_reject_arbitrary_nonempty_strings():
    from app.services.financial_observations import stage_revenue_observation

    document_id = uuid.uuid4()
    cases = []
    for field, invalid in (
        ("period_type", "FY"),
        ("currency", "XYZ"),
        ("accounting_basis", "creative"),
        ("trust_state", "probably"),
    ):
        payload = accepted_context(document_id)
        payload[field] = invalid
        cases.append(payload)
    bad_scale = accepted_context(document_id)
    bad_scale["field_provenance"]["revenue"]["scale"] = "lakhs"
    cases.append(bad_scale)

    for payload in cases:
        session = FakeSession()
        assert (
            stage_revenue_observation(
                session,
                document=SimpleNamespace(document_id=document_id, ticker="BHP"),
                extraction_run=SimpleNamespace(
                    run_id=uuid.uuid4(), extractor_version="multipass-v5"
                ),
                structured=payload,
            )
            is None
        )
        assert session.executed == []


def _observation(value, *, currency="AUD", scale="units"):
    return SimpleNamespace(
        period_end=date(2025, 6, 30),
        period_basis="A",
        accounting_basis="statutory",
        currency=currency,
        scale=scale,
        value=value,
    )


def test_read_returns_only_uncontested_matching_legacy_context():
    from app.services.financial_observations import accepted_revenue_overrides

    session = FakeSession(rows=[_observation(100), _observation(100)])

    assert accepted_revenue_overrides(
        session,
        ticker="BHP",
        legacy_contexts={(date(2025, 6, 30), "A"): ("AUD", "units")},
    ) == {
        (date(2025, 6, 30), "A"): 100
    }


def test_read_abstains_when_accepted_statutory_observations_conflict():
    from app.services.financial_observations import accepted_revenue_overrides

    for rows in (
        [_observation(100), _observation(200)],
        [_observation(100), _observation(100, currency="USD")],
        [_observation(100), _observation(100, scale="thousands")],
    ):
        assert accepted_revenue_overrides(
            FakeSession(rows=rows),
            ticker="BHP",
            legacy_contexts={(date(2025, 6, 30), "A"): ("AUD", "units")},
        ) == {}


def test_read_never_overlays_mismatched_or_missing_legacy_currency_scale():
    from app.services.financial_observations import accepted_revenue_overrides

    row = _observation(Decimal("100"), currency="AUD", scale="units")
    key = (date(2025, 6, 30), "A")

    for context in (("USD", "units"), ("AUD", "thousands"), (None, "units")):
        assert (
            accepted_revenue_overrides(
                FakeSession(rows=[row]),
                ticker="BHP",
                legacy_contexts={key: context},
            )
            == {}
        )
