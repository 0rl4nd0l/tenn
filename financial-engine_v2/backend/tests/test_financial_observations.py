from __future__ import annotations

import uuid
from copy import deepcopy
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


CANONICAL_METRICS = (
    "revenue",
    "ebit",
    "np_attributable",
    "operating_cf",
    "investing_cf",
    "financing_cf",
    "capex",
    "cash_end",
    "net_debt",
    "shares_outstanding",
)


def test_orm_metadata_matches_ten_metric_and_share_unit_migration_contract():
    from sqlalchemy import CheckConstraint

    from app.models.financial_observations import FinancialObservation

    table = FinancialObservation.__table__
    checks = {
        constraint.name: str(constraint.sqltext)
        for constraint in table.constraints
        if isinstance(constraint, CheckConstraint)
    }

    assert table.c.currency.type.length == 16
    assert checks["ck_financial_observation_metric"] == (
        "metric IN ('revenue', 'ebit', 'np_attributable', 'operating_cf', "
        "'investing_cf', 'financing_cf', 'capex', 'cash_end', 'net_debt', "
        "'shares_outstanding')"
    )
    assert checks["ck_financial_observation_currency"] == (
        "(metric = 'shares_outstanding' AND currency = 'shares') OR "
        "(metric <> 'shares_outstanding' AND currency IN ('AUD', 'CAD', "
        "'CNY', 'EUR', 'GBP', 'HKD', 'IDR', 'JPY', 'NZD', 'SGD', 'USD'))"
    )


def accepted_metric_context(document_id: uuid.UUID, metric: str) -> dict:
    context = accepted_context(document_id)
    provenance = deepcopy(context["field_provenance"]["revenue"])
    source_by_metric = {
        "revenue": "income_statement",
        "ebit": "income_statement",
        "np_attributable": "income_statement",
        "operating_cf": "cashflow_statement",
        "investing_cf": "cashflow_statement",
        "financing_cf": "cashflow_statement",
        "capex": "cashflow_statement",
        "cash_end": "cashflow_statement",
        "net_debt": "net_debt_note",
        "shares_outstanding": "share_capital",
    }
    provenance.update(
        metric=metric,
        source=source_by_metric[metric],
        row_ref=f"Statutory {metric}",
    )
    provenance["source_cell"]["row_label"] = f"Statutory {metric}"
    if metric == "shares_outstanding":
        provenance["currency"] = "shares"
        provenance["source_cell"]["header_cell"] = "2025 shares millions"
    context["metrics"] = {metric: 123_000_000}
    context["field_provenance"] = {metric: provenance}
    return context


def test_all_ten_canonical_metrics_stage_independently_with_native_unit_kind():
    from app.services.financial_observations import stage_financial_observations

    document_id = uuid.uuid4()
    context = accepted_context(document_id)
    context["metrics"] = {}
    context["field_provenance"] = {}
    for metric in CANONICAL_METRICS:
        metric_context = accepted_metric_context(document_id, metric)
        context["metrics"].update(metric_context["metrics"])
        context["field_provenance"].update(metric_context["field_provenance"])

    session = FakeSession()
    observations = stage_financial_observations(
        session,
        document=SimpleNamespace(document_id=document_id, ticker="BHP"),
        extraction_run=SimpleNamespace(
            run_id=uuid.uuid4(), extractor_version="multipass-v5"
        ),
        structured=context,
    )

    assert tuple(observation.metric for observation in observations) == CANONICAL_METRICS
    assert len(session.executed) == 10
    assert all(
        observation.currency == "AUD"
        for observation in observations
        if observation.metric != "shares_outstanding"
    )
    shares = observations[-1]
    assert shares.currency == "shares"
    assert shares.scale == "units"
    assert shares.provenance["unit_kind"] == "share_count_absolute"
    assert session.added == []
    assert session.commits == 0


def test_invalid_metric_abstains_without_suppressing_valid_sibling():
    from app.services.financial_observations import stage_financial_observations

    document_id = uuid.uuid4()
    context = accepted_metric_context(document_id, "revenue")
    shares = accepted_metric_context(document_id, "shares_outstanding")
    shares["field_provenance"]["shares_outstanding"]["currency"] = "AUD"
    context["metrics"].update(shares["metrics"])
    context["field_provenance"].update(shares["field_provenance"])

    observations = stage_financial_observations(
        FakeSession(),
        document=SimpleNamespace(document_id=document_id, ticker="BHP"),
        extraction_run=SimpleNamespace(
            run_id=uuid.uuid4(), extractor_version="multipass-v5"
        ),
        structured=context,
    )

    assert [observation.metric for observation in observations] == ["revenue"]


def test_revenue_compatibility_alias_does_not_stage_sibling_metrics():
    from app.services.financial_observations import stage_revenue_observation

    document_id = uuid.uuid4()
    context = accepted_metric_context(document_id, "revenue")
    sibling = accepted_metric_context(document_id, "ebit")
    context["metrics"].update(sibling["metrics"])
    context["field_provenance"].update(sibling["field_provenance"])
    session = FakeSession()

    observation = stage_revenue_observation(
        session,
        document=SimpleNamespace(document_id=document_id, ticker="BHP"),
        extraction_run=SimpleNamespace(
            run_id=uuid.uuid4(), extractor_version="multipass-v5"
        ),
        structured=context,
    )

    assert observation.metric == "revenue"
    assert len(session.executed) == 1


def test_metric_statement_context_is_derived_from_authoritative_contract():
    from app.services.financial_observations import stage_financial_observations

    document_id = uuid.uuid4()
    context = accepted_metric_context(document_id, "ebit")
    context["field_provenance"]["ebit"]["source"] = "cashflow_statement"

    assert (
        stage_financial_observations(
            FakeSession(),
            document=SimpleNamespace(document_id=document_id, ticker="BHP"),
            extraction_run=SimpleNamespace(
                run_id=uuid.uuid4(), extractor_version="multipass-v5"
            ),
            structured=context,
        )
        == ()
    )


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


def test_observation_id_is_deterministic_for_complete_source_context_identity():
    from app.services.financial_observations import stage_revenue_observation

    document_id = uuid.UUID("11111111-1111-1111-1111-111111111111")
    run_id = uuid.UUID("22222222-2222-2222-2222-222222222222")

    def stage(*, context=None, **document_or_run):
        session = FakeSession()
        observation = stage_revenue_observation(
            session,
            document=SimpleNamespace(
                document_id=document_or_run.get("document_id", document_id),
                ticker=document_or_run.get("ticker", "BHP"),
            ),
            extraction_run=SimpleNamespace(
                run_id=document_or_run.get("run_id", run_id),
                extractor_version=document_or_run.get(
                    "extractor_version", "multipass-v5"
                ),
            ),
            structured=context or accepted_context(document_id),
        )
        assert observation is not None
        return observation.observation_id

    first = stage()
    retry = stage(run_id=uuid.UUID("33333333-3333-3333-3333-333333333333"))

    assert first == retry
    assert first.version == 5

    materially_different_ids = {
        stage(document_id=uuid.UUID("44444444-4444-4444-4444-444444444444")),
        stage(extractor_version="multipass-v6"),
        stage(ticker="RIO"),
    }
    for field, replacement in (
        ("period_end", "2024-06-30"),
        ("period_type", "H"),
        ("currency", "USD"),
    ):
        context = accepted_context(document_id)
        context[field] = replacement
        context["field_provenance"]["revenue"][field] = replacement
        if field == "period_type":
            context["source_period_type"] = replacement
            context["source_period_evidence"]["period_type"] = replacement
            context["source_period_evidence"]["hits"][0]["period_type"] = replacement
            context["source_period_end_evidence"]["period_type"] = replacement
            context["source_period_end_evidence"]["hits"][0]["period_type"] = replacement
        elif field == "period_end":
            context["source_period_end_evidence"]["period_end"] = replacement
            context["source_period_end_evidence"]["hits"][0]["period_end"] = replacement
        elif field == "currency":
            context["field_provenance"]["revenue"]["source_cell"][
                "header_cell"
            ] = "2025 USD millions"
        materially_different_ids.add(stage(context=context))

    assert len(materially_different_ids) == 6
    assert first not in materially_different_ids


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


def _observation(
    value, *, metric="revenue", currency="AUD", scale="units"
):
    return SimpleNamespace(
        metric=metric,
        period_end=date(2025, 6, 30),
        period_basis="A",
        accounting_basis="statutory",
        currency=currency,
        scale=scale,
        value=value,
    )


def test_read_projects_each_metric_independently_and_preserves_sparse_legacy():
    from app.services.financial_observations import accepted_statutory_overrides

    rows = [
        _observation(100, metric="revenue"),
        _observation(100, metric="revenue"),
        _observation(20, metric="ebit"),
        _observation(30, metric="ebit"),
        _observation(
            500,
            metric="shares_outstanding",
            currency="shares",
        ),
    ]
    key = (date(2025, 6, 30), "A")

    assert accepted_statutory_overrides(
        FakeSession(rows=rows),
        ticker="BHP",
        legacy_contexts={
            key: {
                **{metric: ("AUD", "units") for metric in CANONICAL_METRICS},
                "shares_outstanding": ("shares", "units"),
            }
        },
    ) == {
        key: {
            "revenue": Decimal("100"),
            "shares_outstanding": Decimal("500"),
        }
    }


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
