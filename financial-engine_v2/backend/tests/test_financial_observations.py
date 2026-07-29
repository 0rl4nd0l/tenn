from __future__ import annotations

import uuid
from copy import deepcopy
from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest


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
    def __init__(self, existing=None, rows=None, model_rows=None):
        self.added = []
        self.commits = 0
        self.existing = existing
        self.rows = rows or []
        self.model_rows = model_rows or {}
        self.executed = []

    def query(self, model):
        return FakeQuery(
            self.existing,
            self.model_rows.get(model, self.rows),
        )

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
                    "matched_text": "year ended 30 June 2025",
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
                    "matched_text": "year ended 30 June 2025",
                }
            ],
        },
        "metrics": {"revenue": 55_658_000_000},
        "field_provenance": {
            "revenue": {
                "metric": "revenue",
                "source": "income_statement",
                "page_number": 42,
                "row_ref": "Consolidated statutory revenue",
                "accounting_basis": "statutory",
                "consolidation_scope": "consolidated",
                "period_type": "A",
                "period_end": "2025-06-30",
                "currency": "AUD",
                "scale": "millions",
                "scale_source": "table_header",
                "source_cell": {
                    "raw_value": "55,658",
                    "row_label": "Consolidated statutory revenue",
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
    assert checks["ck_financial_observation_period_basis"] == (
        "period_basis IN ('Q', 'H', 'A', 'period_only', 'year_to_date')"
    )


def test_period_basis_migration_is_stacked_forward_only_and_matches_orm():
    import ast
    from pathlib import Path

    path = Path(
        "financial-engine_v2/backend/app/alembic/versions/"
        "0012_expand_observation_period_basis.py"
    )
    source = path.read_text()
    tree = ast.parse(source)

    assert 'down_revision = "0011_statutory_metrics"' in source
    assert (
        "_PERIOD_BASES = "
        '("Q", "H", "A", "period_only", "year_to_date")'
    ) in source
    downgrade = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "downgrade"
    )
    assert any(
        isinstance(node, ast.Raise)
        and isinstance(node.exc, ast.Call)
        and getattr(node.exc.func, "id", None) == "RuntimeError"
        for node in ast.walk(downgrade)
    )


def test_supersession_migration_and_orm_are_forward_only_and_evidence_backed():
    import ast
    from pathlib import Path

    from sqlalchemy import CheckConstraint

    from app.models.financial_observations import FinancialObservationSupersession

    table = FinancialObservationSupersession.__table__
    checks = {
        constraint.name: str(constraint.sqltext)
        for constraint in table.constraints
        if isinstance(constraint, CheckConstraint)
    }
    assert checks["ck_financial_observation_supersession_type"] == (
        "relationship_type IN ('amendment', 'restatement')"
    )
    assert table.c.evidence.nullable is False
    assert any(
        constraint.name == "uq_financial_observation_superseded_once"
        for constraint in table.constraints
    )

    path = Path(
        "financial-engine_v2/backend/app/alembic/versions/"
        "0014_observation_supersessions.py"
    )
    source = path.read_text()
    tree = ast.parse(source)
    assert 'down_revision = "0013_result_disclosures"' in source
    downgrade = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "downgrade"
    )
    assert any(isinstance(node, ast.Raise) for node in ast.walk(downgrade))


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
        row_ref=f"Consolidated statutory {metric}",
    )
    provenance["source_cell"]["row_label"] = (
        f"Consolidated statutory {metric}"
    )
    if metric == "shares_outstanding":
        provenance["currency"] = "shares"
        provenance["source_cell"]["header_cell"] = "2025 shares millions"
    context["metrics"] = {metric: 123_000_000}
    context["field_provenance"] = {metric: provenance}
    return context


def accepted_quarter_member(
    document_id: uuid.UUID, *, basis: str, value: int
) -> dict:
    role = {
        "period_only": "current_quarter",
        "year_to_date": "year_to_date",
    }[basis]
    context = accepted_metric_context(document_id, "revenue")
    context["period_basis"] = basis
    context.pop("period_type")
    context["source_period_type"] = basis
    context["metrics"]["revenue"] = value
    context["source_period_evidence"] = {
        "period_basis": basis,
        "hits": [
            {
                "period_basis": basis,
                "reason": f"{basis}_source_phrase",
                "source": "source_text",
                "matched_text": (
                    "current quarter"
                    if basis == "period_only"
                    else "year to date"
                ),
            }
        ],
    }
    context["source_period_end_evidence"] = {
        "period_basis": basis,
        "period_end": "2025-03-31",
        "hits": [
            {
                "period_basis": basis,
                "period_end": "2025-03-31",
                "reason": "reporting_period_end_explicit_date",
                "source": "source_text",
                "matched_text": (
                    "three months ended 31 March 2025"
                    if basis == "period_only"
                    else "year to date ended 31 March 2025"
                ),
            }
        ],
    }
    context["period_end"] = "2025-03-31"
    provenance = context["field_provenance"]["revenue"]
    provenance["period_basis"] = basis
    provenance.pop("period_type")
    provenance["period_end"] = "2025-03-31"
    provenance["source_cell"].update(
        column_index=2 if basis == "period_only" else 3,
        column_role=role,
        header_cell="Current quarter AUD millions"
        if basis == "period_only"
        else "Year to date AUD millions",
    )
    return context


def test_one_document_stages_distinct_quarter_and_ytd_observations():
    from app.services.financial_observations import stage_financial_observations

    document_id = uuid.UUID("11111111-1111-1111-1111-111111111111")
    session = FakeSession()
    observations = stage_financial_observations(
        session,
        document=SimpleNamespace(document_id=document_id, ticker="BHP"),
        extraction_run=SimpleNamespace(
            run_id=uuid.uuid4(), extractor_version="multipass-v5"
        ),
        structured={
            "period_observations": [
                accepted_quarter_member(
                    document_id, basis="period_only", value=25
                ),
                accepted_quarter_member(
                    document_id, basis="year_to_date", value=70
                ),
            ]
        },
    )

    assert [(item.period_basis, item.value) for item in observations] == [
        ("period_only", 25),
        ("year_to_date", 70),
    ]
    assert observations[0].observation_id != observations[1].observation_id
    assert len(session.executed) == 2


def test_invalid_quarter_member_and_metric_do_not_suppress_valid_siblings():
    from app.services.financial_observations import stage_financial_observations

    document_id = uuid.uuid4()
    valid = accepted_quarter_member(
        document_id, basis="period_only", value=25
    )
    invalid_metric = accepted_quarter_member(
        document_id, basis="year_to_date", value=70
    )
    invalid_metric["field_provenance"]["revenue"]["source_cell"][
        "column_role"
    ] = "current_quarter"

    observations = stage_financial_observations(
        FakeSession(),
        document=SimpleNamespace(document_id=document_id, ticker="BHP"),
        extraction_run=SimpleNamespace(
            run_id=uuid.uuid4(), extractor_version="multipass-v5"
        ),
        structured={"period_observations": [valid, invalid_metric, "invalid"]},
    )

    assert [(item.period_basis, item.value) for item in observations] == [
        ("period_only", 25)
    ]


def test_quarter_basis_rejects_comparative_prior_and_date_column_roles():
    from app.services.financial_observations import stage_financial_observations

    document_id = uuid.uuid4()
    for role in (
        "comparative",
        "prior_period",
        "date",
        "announcement_date",
        "unknown",
    ):
        member = accepted_quarter_member(
            document_id, basis="period_only", value=25
        )
        member["field_provenance"]["revenue"]["source_cell"][
            "column_role"
        ] = role
        assert stage_financial_observations(
            FakeSession(),
            document=SimpleNamespace(document_id=document_id, ticker="BHP"),
            extraction_run=SimpleNamespace(
                run_id=uuid.uuid4(), extractor_version="multipass-v5"
            ),
            structured={"period_observations": [member]},
        ) == ()


def test_quarter_basis_requires_nonnegative_column_and_source_text_evidence():
    from app.services.financial_observations import stage_financial_observations

    document_id = uuid.uuid4()
    cases = []
    for index in (-1, None, True):
        member = accepted_quarter_member(
            document_id, basis="period_only", value=25
        )
        member["field_provenance"]["revenue"]["source_cell"][
            "column_index"
        ] = index
        cases.append(member)
    metadata_only = accepted_quarter_member(
        document_id, basis="period_only", value=25
    )
    metadata_only["source_period_evidence"]["hits"][0]["source"] = "metadata"
    cases.append(metadata_only)
    announcement_date = accepted_quarter_member(
        document_id, basis="period_only", value=25
    )
    announcement_date["source_period_end_evidence"]["hits"][0][
        "reason"
    ] = "announcement_date"
    cases.append(announcement_date)

    for member in cases:
        assert stage_financial_observations(
            FakeSession(),
            document=SimpleNamespace(document_id=document_id, ticker="BHP"),
            extraction_run=SimpleNamespace(
                run_id=uuid.uuid4(), extractor_version="multipass-v5"
            ),
            structured={"period_observations": [member]},
        ) == ()


def test_quarter_basis_rejects_cross_basis_source_phrases_both_ways():
    from app.services.financial_observations import stage_financial_observations

    document_id = uuid.uuid4()
    for basis, wrong_basis in (
        ("period_only", "year_to_date"),
        ("year_to_date", "period_only"),
    ):
        member = accepted_quarter_member(document_id, basis=basis, value=25)
        member["source_period_evidence"]["hits"][0][
            "reason"
        ] = f"{wrong_basis}_source_phrase"

        assert stage_financial_observations(
            FakeSession(),
            document=SimpleNamespace(document_id=document_id, ticker="BHP"),
            extraction_run=SimpleNamespace(
                run_id=uuid.uuid4(), extractor_version="multipass-v5"
            ),
            structured={"period_observations": [member]},
        ) == ()


def test_period_observation_requires_explicit_first_class_period_basis():
    from app.services.financial_observations import stage_financial_observations

    document_id = uuid.uuid4()
    for location in (
        "member",
        "source_period_evidence",
        "source_period_evidence_hit",
        "source_period_end_evidence",
        "source_period_end_evidence_hit",
        "field_provenance",
    ):
        member = accepted_quarter_member(
            document_id, basis="period_only", value=25
        )
        if location == "member":
            member["period_type"] = member.pop("period_basis")
        elif location == "source_period_evidence":
            evidence = member["source_period_evidence"]
            evidence["period_type"] = evidence.pop("period_basis")
        elif location == "source_period_evidence_hit":
            hit = member["source_period_evidence"]["hits"][0]
            hit["period_type"] = hit.pop("period_basis")
        elif location == "source_period_end_evidence":
            evidence = member["source_period_end_evidence"]
            evidence["period_type"] = evidence.pop("period_basis")
        elif location == "source_period_end_evidence_hit":
            hit = member["source_period_end_evidence"]["hits"][0]
            hit["period_type"] = hit.pop("period_basis")
        else:
            provenance = member["field_provenance"]["revenue"]
            provenance["period_type"] = provenance.pop("period_basis")

        assert stage_financial_observations(
            FakeSession(),
            document=SimpleNamespace(document_id=document_id, ticker="BHP"),
            extraction_run=SimpleNamespace(
                run_id=uuid.uuid4(), extractor_version="multipass-v5"
            ),
            structured={"period_observations": [member]},
        ) == ()


def test_period_observation_accepts_period_basis_only_field_provenance():
    from app.services.financial_observations import stage_financial_observations

    document_id = uuid.uuid4()
    member = accepted_quarter_member(
        document_id, basis="period_only", value=25
    )
    provenance = member["field_provenance"]["revenue"]

    assert provenance["period_basis"] == "period_only"
    assert "period_type" not in provenance
    observations = stage_financial_observations(
        FakeSession(),
        document=SimpleNamespace(document_id=document_id, ticker="BHP"),
        extraction_run=SimpleNamespace(
            run_id=uuid.uuid4(), extractor_version="multipass-v5"
        ),
        structured={"period_observations": [member]},
    )
    assert [(item.period_basis, item.value) for item in observations] == [
        ("period_only", 25)
    ]


def test_period_observation_rejects_missing_field_provenance_period_basis():
    from app.services.financial_observations import stage_financial_observations

    document_id = uuid.uuid4()
    member = accepted_quarter_member(
        document_id, basis="period_only", value=25
    )
    member["field_provenance"]["revenue"].pop("period_basis")

    assert stage_financial_observations(
        FakeSession(),
        document=SimpleNamespace(document_id=document_id, ticker="BHP"),
        extraction_run=SimpleNamespace(
            run_id=uuid.uuid4(), extractor_version="multipass-v5"
        ),
        structured={"period_observations": [member]},
    ) == ()


def test_legacy_single_period_input_retains_period_type_fallback():
    from app.services.financial_observations import stage_financial_observations

    document_id = uuid.uuid4()
    observations = stage_financial_observations(
        FakeSession(),
        document=SimpleNamespace(document_id=document_id, ticker="BHP"),
        extraction_run=SimpleNamespace(
            run_id=uuid.uuid4(), extractor_version="multipass-v5"
        ),
        structured=accepted_context(document_id),
    )

    assert [(item.period_basis, item.value) for item in observations] == [
        ("A", 55_658_000_000)
    ]


def test_quarter_basis_requires_explicit_period_observations_collection():
    from app.services.financial_observations import stage_financial_observations

    document_id = uuid.uuid4()
    member = accepted_quarter_member(document_id, basis="period_only", value=25)
    observations = stage_financial_observations(
        FakeSession(),
        document=SimpleNamespace(document_id=document_id, ticker="BHP"),
        extraction_run=SimpleNamespace(
            run_id=uuid.uuid4(), extractor_version="multipass-v5"
        ),
        structured=member,
    )

    assert observations == ()


def test_new_source_text_evidence_rejects_mixed_missing_text():
    from app.services.financial_observations import stage_financial_observations

    document_id = uuid.uuid4()
    for legacy in (False,):
        for evidence_field in (
            "source_period_evidence",
            "source_period_end_evidence",
        ):
            payload = (
                accepted_context(document_id)
                if legacy
                else accepted_quarter_member(
                    document_id, basis="period_only", value=25
                )
            )
            invalid_hit = deepcopy(payload[evidence_field]["hits"][0])
            invalid_hit.pop("matched_text")
            payload[evidence_field]["hits"].append(invalid_hit)
            structured = (
                payload
                if legacy
                else {"period_observations": [payload]}
            )

            assert stage_financial_observations(
                FakeSession(),
                document=SimpleNamespace(
                    document_id=document_id, ticker="BHP"
                ),
                extraction_run=SimpleNamespace(
                    run_id=uuid.uuid4(),
                    extractor_version="multipass-v5",
                ),
                structured=structured,
            ) == ()


def test_new_source_text_evidence_rejects_mixed_whitespace_text():
    from app.services.financial_observations import stage_financial_observations

    document_id = uuid.uuid4()
    for legacy in (False,):
        for evidence_field in (
            "source_period_evidence",
            "source_period_end_evidence",
        ):
            payload = (
                accepted_context(document_id)
                if legacy
                else accepted_quarter_member(
                    document_id, basis="period_only", value=25
                )
            )
            invalid_hit = deepcopy(payload[evidence_field]["hits"][0])
            invalid_hit["matched_text"] = " \t "
            payload[evidence_field]["hits"].append(invalid_hit)
            structured = (
                payload
                if legacy
                else {"period_observations": [payload]}
            )

            assert stage_financial_observations(
                FakeSession(),
                document=SimpleNamespace(
                    document_id=document_id, ticker="BHP"
                ),
                extraction_run=SimpleNamespace(
                    run_id=uuid.uuid4(),
                    extractor_version="multipass-v5",
                ),
                structured=structured,
            ) == ()


def test_source_text_evidence_collections_require_unanimous_valid_hits():
    from app.services.financial_observations import stage_financial_observations

    document_id = uuid.uuid4()
    mutations = (
        ("wrong_basis", lambda hit: hit.update(period_basis="year_to_date")),
        ("missing_basis", lambda hit: hit.pop("period_basis", None)),
        ("reason", lambda hit: hit.update(reason="announcement_date")),
        ("blank_quote", lambda hit: hit.update(matched_text=" \t ")),
    )
    for legacy in (False,):
        for evidence_field in (
            "source_period_evidence",
            "source_period_end_evidence",
        ):
            for dimension, mutate in mutations:
                payload = (
                    accepted_context(document_id)
                    if legacy
                    else accepted_quarter_member(
                        document_id, basis="period_only", value=25
                    )
                )
                malformed = deepcopy(payload[evidence_field]["hits"][0])
                if legacy and dimension == "wrong_basis":
                    malformed.pop("period_type")
                    malformed["period_basis"] = "H"
                elif legacy and dimension == "missing_basis":
                    malformed.pop("period_type")
                else:
                    mutate(malformed)
                payload[evidence_field]["hits"].append(malformed)
                structured = (
                    payload
                    if legacy
                    else {"period_observations": [payload]}
                )

                assert stage_financial_observations(
                    FakeSession(),
                    document=SimpleNamespace(
                        document_id=document_id, ticker="BHP"
                    ),
                    extraction_run=SimpleNamespace(
                        run_id=uuid.uuid4(),
                        extractor_version="multipass-v5",
                    ),
                    structured=structured,
                ) == (), (legacy, evidence_field, dimension)


def test_new_period_end_evidence_rejects_valid_hit_mixed_with_wrong_end():
    from app.services.financial_observations import stage_financial_observations

    document_id = uuid.uuid4()
    for legacy in (False,):
        for malformed_period_end in (None, "2025-03-30"):
            payload = (
                accepted_context(document_id)
                if legacy
                else accepted_quarter_member(
                    document_id, basis="period_only", value=25
                )
            )
            malformed = deepcopy(
                payload["source_period_end_evidence"]["hits"][0]
            )
            if malformed_period_end is None:
                malformed.pop("period_end")
            else:
                malformed["period_end"] = malformed_period_end
            payload["source_period_end_evidence"]["hits"].append(malformed)

            assert stage_financial_observations(
                FakeSession(),
                document=SimpleNamespace(
                    document_id=document_id, ticker="BHP"
                ),
                extraction_run=SimpleNamespace(
                    run_id=uuid.uuid4(), extractor_version="multipass-v5"
                ),
                structured=(
                    payload
                    if legacy
                    else {"period_observations": [payload]}
                ),
            ) == ()


def test_new_evidence_unanimity_rejects_non_source_text_siblings():
    from app.services.financial_observations import stage_financial_observations

    document_id = uuid.uuid4()
    for evidence_field in (
        "source_period_evidence",
        "source_period_end_evidence",
    ):
        for sibling in (
            {"source": "metadata", "reason": "announcement_date"},
            {"source": "source_text", "reason": "comparative"},
            {"source": "source_text"},
            "malformed",
        ):
            payload = accepted_quarter_member(
                document_id, basis="period_only", value=25
            )
            payload[evidence_field]["hits"].append(sibling)

            assert stage_financial_observations(
                FakeSession(),
                document=SimpleNamespace(
                    document_id=document_id, ticker="BHP"
                ),
                extraction_run=SimpleNamespace(
                    run_id=uuid.uuid4(), extractor_version="multipass-v5"
                ),
                structured={"period_observations": [payload]},
            ) == (), (evidence_field, sibling)


def test_legacy_evidence_retains_existential_source_text_matching():
    from app.services.financial_observations import stage_financial_observations

    document_id = uuid.uuid4()
    payload = accepted_context(document_id)
    for evidence_field in (
        "source_period_evidence",
        "source_period_end_evidence",
    ):
        payload[evidence_field]["hits"].extend(
            [
                {"source": "metadata", "reason": "announcement_date"},
                {"source": "source_text", "reason": "comparative"},
                {"source": "source_text"},
                "malformed",
            ]
        )

    observations = stage_financial_observations(
        FakeSession(),
        document=SimpleNamespace(document_id=document_id, ticker="BHP"),
        extraction_run=SimpleNamespace(
            run_id=uuid.uuid4(), extractor_version="multipass-v5"
        ),
        structured=payload,
    )
    assert len(observations) == 1


def test_new_period_end_evidence_rejects_missing_or_mismatched_hit_date():
    from app.services.financial_observations import stage_financial_observations

    document_id = uuid.uuid4()
    for hit_period_end in (None, "2025-03-30"):
        payload = accepted_quarter_member(
            document_id, basis="period_only", value=25
        )
        hit = payload["source_period_end_evidence"]["hits"][0]
        if hit_period_end is None:
            hit.pop("period_end")
        else:
            hit["period_end"] = hit_period_end

        assert stage_financial_observations(
            FakeSession(),
            document=SimpleNamespace(
                document_id=document_id, ticker="BHP"
            ),
            extraction_run=SimpleNamespace(
                run_id=uuid.uuid4(),
                extractor_version="multipass-v5",
            ),
            structured={"period_observations": [payload]},
        ) == ()


def test_legacy_seed_compatibility_stages_while_new_member_abstains():
    from app.services.financial_observations import stage_financial_observations

    document_id = uuid.uuid4()
    payloads = (
        (accepted_context(document_id), True),
        (
            accepted_quarter_member(
                document_id, basis="period_only", value=25
            ),
            False,
        ),
    )
    for payload, legacy in payloads:
        period_field = "period_type" if legacy else "period_basis"
        for evidence_field in (
            "source_period_evidence",
            "source_period_end_evidence",
        ):
            valid_hit = payload[evidence_field]["hits"][0]
            valid_hit.pop("matched_text")
            if evidence_field == "source_period_end_evidence":
                valid_hit.pop("period_end")
                payload[evidence_field].pop(period_field)
            payload[evidence_field]["hits"].extend(
                [
                    {
                        "source": "source_text",
                        "reason": "unrelated_seed_hit",
                    },
                    {
                        "source": "source_text",
                        period_field: "invalid",
                        "reason": valid_hit["reason"],
                    },
                ]
            )
        source_cell = payload["field_provenance"]["revenue"]["source_cell"]
        source_cell["raw_value"] = " \t "
        source_cell["header_cell"] = " \t "
        source_cell["row_label"] = "Statutory revenue AUD millions"

        observations = stage_financial_observations(
            FakeSession(),
            document=SimpleNamespace(document_id=document_id, ticker="BHP"),
            extraction_run=SimpleNamespace(
                run_id=uuid.uuid4(), extractor_version="multipass-v5"
            ),
            structured=(
                payload
                if legacy
                else {"period_observations": [payload]}
            ),
        )

        assert len(observations) == (1 if legacy else 0)


def test_period_end_evidence_accepts_exact_hit_date_new_and_legacy():
    from app.services.financial_observations import stage_financial_observations

    document_id = uuid.uuid4()
    for legacy in (False, True):
        payload = (
            accepted_context(document_id)
            if legacy
            else accepted_quarter_member(
                document_id, basis="period_only", value=25
            )
        )
        expected_period_end = payload["period_end"]
        assert (
            payload["source_period_end_evidence"]["hits"][0]["period_end"]
            == expected_period_end
        )
        structured = (
            payload
            if legacy
            else {"period_observations": [payload]}
        )

        observations = stage_financial_observations(
            FakeSession(),
            document=SimpleNamespace(document_id=document_id, ticker="BHP"),
            extraction_run=SimpleNamespace(
                run_id=uuid.uuid4(),
                extractor_version="multipass-v5",
            ),
            structured=structured,
        )

        assert len(observations) == 1
        assert observations[0].period_end.isoformat() == expected_period_end


def test_source_cell_rejects_whitespace_only_raw_value_and_header():
    from app.services.financial_observations import stage_financial_observations

    document_id = uuid.uuid4()
    for field in ("raw_value", "header_cell"):
        member = accepted_quarter_member(
            document_id, basis="period_only", value=25
        )
        member["field_provenance"]["revenue"]["source_cell"][field] = " \t "

        assert stage_financial_observations(
            FakeSession(),
            document=SimpleNamespace(document_id=document_id, ticker="BHP"),
            extraction_run=SimpleNamespace(
                run_id=uuid.uuid4(), extractor_version="multipass-v5"
            ),
            structured={"period_observations": [member]},
        ) == ()


def test_quarter_header_semantics_override_falsely_matching_column_role():
    from app.services.financial_observations import stage_financial_observations

    document_id = uuid.uuid4()
    for header in (
        "Comparative AUD millions",
        "Prior quarter AUD millions",
        "Date",
        "Date AUD millions",
        "Announcement date",
        "Announcement date 29 April 2025 AUD millions",
        "Lodgement date 29 April 2025",
    ):
        member = accepted_quarter_member(
            document_id, basis="period_only", value=25
        )
        member["field_provenance"]["revenue"]["source_cell"][
            "header_cell"
        ] = header
        member["field_provenance"]["revenue"]["source_cell"][
            "row_label"
        ] = "Statutory revenue AUD"

        assert stage_financial_observations(
            FakeSession(),
            document=SimpleNamespace(document_id=document_id, ticker="BHP"),
            extraction_run=SimpleNamespace(
                run_id=uuid.uuid4(), extractor_version="multipass-v5"
            ),
            structured={"period_observations": [member]},
        ) == (), header


def test_quarter_header_semantics_reject_explicit_opposite_basis_both_ways():
    from app.services.financial_observations import stage_financial_observations

    document_id = uuid.uuid4()
    cases = (
        ("period_only", "Year to date 31 March 2025 AUD millions"),
        ("period_only", "Cumulative YTD AUD millions"),
        ("year_to_date", "Current quarter AUD millions"),
        ("year_to_date", "Quarter-only AUD millions"),
        ("year_to_date", "Three-month period AUD millions"),
    )
    for basis, header in cases:
        member = accepted_quarter_member(document_id, basis=basis, value=25)
        member["field_provenance"]["revenue"]["source_cell"][
            "header_cell"
        ] = header

        assert stage_financial_observations(
            FakeSession(),
            document=SimpleNamespace(document_id=document_id, ticker="BHP"),
            extraction_run=SimpleNamespace(
                run_id=uuid.uuid4(), extractor_version="multipass-v5"
            ),
            structured={"period_observations": [member]},
        ) == (), (basis, header)


def test_quarter_header_semantics_accept_legitimate_reporting_dates():
    from app.services.financial_observations import stage_financial_observations

    document_id = uuid.uuid4()
    for basis, header in (
        ("period_only", "3 months ended 31 March 2025 AUD millions"),
        ("year_to_date", "Year to date 31 March 2025 AUD millions"),
    ):
        member = accepted_quarter_member(document_id, basis=basis, value=25)
        member["field_provenance"]["revenue"]["source_cell"][
            "header_cell"
        ] = header

        observations = stage_financial_observations(
            FakeSession(),
            document=SimpleNamespace(document_id=document_id, ticker="BHP"),
            extraction_run=SimpleNamespace(
                run_id=uuid.uuid4(), extractor_version="multipass-v5"
            ),
            structured={"period_observations": [member]},
        )
        assert len(observations) == 1, (basis, header)


def test_quarter_header_semantics_fail_closed_for_unclaimed_bases():
    from app.services.financial_observations import stage_financial_observations

    document_id = uuid.uuid4()
    for basis, header in (
        ("period_only", "6 months ended 31 March 2025 AUD millions"),
        ("year_to_date", "Quarter ended 31 March 2025 AUD millions"),
        ("period_only", "31 March 2025 AUD millions"),
        ("year_to_date", "PCP year to date AUD millions"),
    ):
        member = accepted_quarter_member(document_id, basis=basis, value=25)
        member["field_provenance"]["revenue"]["source_cell"][
            "header_cell"
        ] = header

        assert stage_financial_observations(
            FakeSession(),
            document=SimpleNamespace(document_id=document_id, ticker="BHP"),
            extraction_run=SimpleNamespace(
                run_id=uuid.uuid4(), extractor_version="multipass-v5"
            ),
            structured={"period_observations": [member]},
        ) == (), (basis, header)


def test_new_quarter_source_quotes_must_semantically_authenticate_basis():
    from app.services.financial_observations import stage_financial_observations

    document_id = uuid.uuid4()
    for evidence_field, quote in (
        ("source_period_evidence", "arbitrary source text"),
        ("source_period_evidence", "year to date"),
        ("source_period_end_evidence", "year to date ended 31 March 2025"),
    ):
        member = accepted_quarter_member(
            document_id, basis="period_only", value=25
        )
        member[evidence_field]["hits"][0]["matched_text"] = quote

        assert stage_financial_observations(
            FakeSession(),
            document=SimpleNamespace(document_id=document_id, ticker="BHP"),
            extraction_run=SimpleNamespace(
                run_id=uuid.uuid4(), extractor_version="multipass-v5"
            ),
            structured={"period_observations": [member]},
        ) == (), (evidence_field, quote)


def test_new_quarter_quotes_reject_metadata_date_labels_in_any_position():
    from app.services.financial_observations import stage_financial_observations

    document_id = uuid.uuid4()
    cases = (
        (
            "source_period_evidence",
            "announcement date current quarter",
        ),
        (
            "source_period_evidence",
            "current quarter announcement date 31 March 2025",
        ),
        (
            "source_period_evidence",
            "current quarter ended 31 March 2025 lodgement date",
        ),
        (
            "source_period_end_evidence",
            "release date current quarter ended 31 March 2025",
        ),
        (
            "source_period_end_evidence",
            "year to date publication date 31 March 2025",
        ),
        (
            "source_period_end_evidence",
            "year to date ended 31 March 2025 report date",
        ),
    )
    for evidence_field, quote in cases:
        basis = "year_to_date" if "year to date" in quote else "period_only"
        member = accepted_quarter_member(document_id, basis=basis, value=25)
        member[evidence_field]["hits"][0]["matched_text"] = quote

        assert stage_financial_observations(
            FakeSession(),
            document=SimpleNamespace(document_id=document_id, ticker="BHP"),
            extraction_run=SimpleNamespace(
                run_id=uuid.uuid4(), extractor_version="multipass-v5"
            ),
            structured={"period_observations": [member]},
        ) == (), (evidence_field, quote)


def test_new_quarter_quotes_accept_legitimate_reporting_period_wording():
    from app.services.financial_observations import stage_financial_observations

    document_id = uuid.uuid4()
    for basis, quote in (
        ("period_only", "current quarter ended 31 March 2025"),
        ("year_to_date", "year to date ended 31 March 2025"),
    ):
        member = accepted_quarter_member(document_id, basis=basis, value=25)
        member["source_period_evidence"]["hits"][0]["matched_text"] = quote
        member["source_period_end_evidence"]["hits"][0]["matched_text"] = quote

        observations = stage_financial_observations(
            FakeSession(),
            document=SimpleNamespace(document_id=document_id, ticker="BHP"),
            extraction_run=SimpleNamespace(
                run_id=uuid.uuid4(), extractor_version="multipass-v5"
            ),
            structured={"period_observations": [member]},
        )
        assert len(observations) == 1, (basis, quote)


def test_new_quarter_period_end_quote_must_express_exact_member_date():
    from app.services.financial_observations import stage_financial_observations

    document_id = uuid.uuid4()
    for quote in (
        "three months ended 30 March 2025",
        "three months ended 2025-03-30",
        "three months ended 30/03/2025",
    ):
        member = accepted_quarter_member(
            document_id, basis="period_only", value=25
        )
        member["source_period_end_evidence"]["hits"][0][
            "matched_text"
        ] = quote

        assert stage_financial_observations(
            FakeSession(),
            document=SimpleNamespace(document_id=document_id, ticker="BHP"),
            extraction_run=SimpleNamespace(
                run_id=uuid.uuid4(), extractor_version="multipass-v5"
            ),
            structured={"period_observations": [member]},
        ) == (), quote


def test_new_quarter_period_end_quote_accepts_common_exact_date_forms():
    from app.services.financial_observations import stage_financial_observations

    document_id = uuid.uuid4()
    for date_text in (
        "2025-03-31",
        "31/03/2025",
        "03/31/2025",
        "31 March 2025",
        "March 31, 2025",
    ):
        member = accepted_quarter_member(
            document_id, basis="period_only", value=25
        )
        member["source_period_end_evidence"]["hits"][0][
            "matched_text"
        ] = f"quarter ended {date_text}"

        observations = stage_financial_observations(
            FakeSession(),
            document=SimpleNamespace(document_id=document_id, ticker="BHP"),
            extraction_run=SimpleNamespace(
                run_id=uuid.uuid4(), extractor_version="multipass-v5"
            ),
            structured={"period_observations": [member]},
        )
        assert len(observations) == 1, date_text


def test_new_quarter_period_end_quote_rejects_ambiguous_slash_date():
    from app.services.financial_observations import stage_financial_observations

    document_id = uuid.uuid4()
    for period_end, date_text in (
        ("2025-04-03", "03/04/2025"),
        ("2025-03-04", "03/04/2025"),
    ):
        member = accepted_quarter_member(
            document_id, basis="period_only", value=25
        )
        member["period_end"] = period_end
        member["source_period_end_evidence"]["period_end"] = period_end
        hit = member["source_period_end_evidence"]["hits"][0]
        hit["period_end"] = period_end
        hit["matched_text"] = f"quarter ended {date_text}"
        member["field_provenance"]["revenue"]["period_end"] = period_end

        assert stage_financial_observations(
            FakeSession(),
            document=SimpleNamespace(
                document_id=document_id, ticker="BHP"
            ),
            extraction_run=SimpleNamespace(
                run_id=uuid.uuid4(), extractor_version="multipass-v5"
            ),
            structured={"period_observations": [member]},
        ) == (), (period_end, date_text)


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


def test_revenue_compatibility_alias_does_not_stage_result_disclosures():
    from app.services.financial_observations import stage_revenue_observation

    document_id = uuid.uuid4()
    context = accepted_metric_context(document_id, "revenue")
    context["result_disclosures"] = [adjusted_disclosure(document_id)]
    session = FakeSession()

    observation = stage_revenue_observation(
        session,
        document=SimpleNamespace(document_id=document_id, ticker="BHP"),
        extraction_run=SimpleNamespace(
            run_id=uuid.uuid4(), extractor_version="multipass-v5"
        ),
        structured=context,
    )

    assert observation is not None
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
    assert observation.provenance["row_ref"] == "Consolidated statutory revenue"
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
        observation_id=uuid.uuid4(),
        source_document_id=uuid.uuid4(),
        extraction_run_id=uuid.uuid4(),
        extractor_version="multipass-v9",
        ticker="BHP",
        metric=metric,
        period_end=date(2025, 6, 30),
        period_basis="A",
        accounting_basis="statutory",
        currency=currency,
        scale=scale,
        value=value,
        provenance={"row_ref": "Consolidated statutory revenue"},
        trust_state="accepted",
    )


def _supersession(superseding, superseded, relationship_type="restatement"):
    return SimpleNamespace(
        superseding_observation_id=superseding.observation_id,
        superseded_observation_id=superseded.observation_id,
        relationship_type=relationship_type,
        evidence={
            "source": "income_statement",
            "page_number": 3,
            "row_ref": "Restated comparative",
            "matched_text": "Comparative revenue has been restated",
            "superseded_source_document_id": str(
                superseded.source_document_id
            ),
        },
    )


def test_explicit_restatement_selects_new_truth_and_later_arrival_cannot_win():
    from app.models.financial_observations import (
        FinancialObservation,
        FinancialObservationSupersession,
    )
    from app.services.financial_observations import accepted_revenue_overrides

    original = _observation(100)
    restated = _observation(90)
    relationship = _supersession(restated, original)
    key = (date(2025, 6, 30), "A")
    session = FakeSession(
        model_rows={
            FinancialObservation: [original, restated],
            FinancialObservationSupersession: [relationship],
        }
    )
    assert accepted_revenue_overrides(
        session,
        ticker="BHP",
        legacy_contexts={key: ("AUD", "units")},
    ) == {key: Decimal("90")}

    ordinary_later_arrival = _observation(110)
    session.model_rows[FinancialObservation].append(ordinary_later_arrival)
    assert accepted_revenue_overrides(
        session,
        ticker="BHP",
        legacy_contexts={key: ("AUD", "units")},
    ) == {}


def test_stage_supersession_requires_explicit_matching_evidence_and_identity():
    from app.models.financial_observations import FinancialObservation
    from app.services.financial_observations import stage_observation_supersessions

    original = _observation(100)
    restated = _observation(90)
    candidate = {
        "relationship_type": "restatement",
        "superseded_source_document_id": str(original.source_document_id),
        "metric": "revenue",
        "period_end": "2025-06-30",
        "period_basis": "A",
        "evidence": _supersession(restated, original).evidence,
    }
    session = FakeSession(model_rows={FinancialObservation: [original]})
    relationships = stage_observation_supersessions(
        session,
        superseding_observations=(restated,),
        structured={"observation_supersessions": [candidate]},
    )
    assert len(relationships) == 1
    assert relationships[0].superseded_observation_id == original.observation_id
    assert session.commits == 0

    for mutation in ("ordinary", "wrong_target", "different_metric"):
        rejected = deepcopy(candidate)
        superseding = restated
        if mutation == "ordinary":
            rejected["evidence"]["matched_text"] = "Revenue for the year"
        elif mutation == "wrong_target":
            rejected["evidence"]["superseded_source_document_id"] = str(
                uuid.uuid4()
            )
        else:
            superseding = _observation(90, metric="ebit")
        rejected_session = FakeSession(
            model_rows={FinancialObservation: [original]}
        )
        assert stage_observation_supersessions(
            rejected_session,
            superseding_observations=(superseding,),
            structured={"observation_supersessions": [rejected]},
        ) == ()
        assert rejected_session.executed == []


def test_history_retains_superseded_observation_and_both_provenance_records():
    from app.models.financial_observations import (
        FinancialObservation,
        FinancialObservationSupersession,
    )
    from app.services.financial_observations import accepted_observation_history

    original = _observation(100)
    restated = _observation(90)
    relationship = _supersession(restated, original)
    history = accepted_observation_history(
        FakeSession(
            model_rows={
                FinancialObservation: [original, restated],
                FinancialObservationSupersession: [relationship],
            }
        ),
        ticker="BHP",
    )
    by_id = {item["observation_id"]: item for item in history}
    superseded = by_id[str(original.observation_id)]
    assert superseded["active"] is False
    assert superseded["provenance"] == original.provenance
    assert superseded["superseded_by"] == str(restated.observation_id)
    assert superseded["supersession_evidence"] == relationship.evidence
    assert by_id[str(restated.observation_id)]["active"] is True


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


def test_additive_read_returns_sparse_deterministic_bases_without_conflicts():
    from app.services.financial_observations import accepted_observation_periods

    period_only = _observation(25)
    period_only.period_basis = "period_only"
    ytd_revenue = _observation(70)
    ytd_revenue.period_basis = "year_to_date"
    ytd_ebit_a = _observation(10, metric="ebit")
    ytd_ebit_a.period_basis = "year_to_date"
    ytd_ebit_b = _observation(11, metric="ebit")
    ytd_ebit_b.period_basis = "year_to_date"

    assert accepted_observation_periods(
        FakeSession(
            rows=[ytd_ebit_b, period_only, ytd_revenue, ytd_ebit_a]
        ),
        ticker="BHP",
    ) == (
        {
            "ticker": "BHP",
            "period_end": date(2025, 6, 30),
            "period_type": "year_to_date",
            "period_basis": "year_to_date",
            "observation_only": True,
            "revenue": "70",
            "metric_units": {"revenue": "AUD"},
        },
        {
            "ticker": "BHP",
            "period_end": date(2025, 6, 30),
            "period_type": "period_only",
            "period_basis": "period_only",
            "observation_only": True,
            "revenue": "25",
            "metric_units": {"revenue": "AUD"},
        },
    )


def adjusted_disclosure(document_id: uuid.UUID) -> dict:
    source_label = "Underlying EBITDA (management measure)"
    return {
        "metric": "ebit",
        "value": 125_000_000,
        "period_end": "2025-06-30",
        "period_basis": "A",
        "accounting_basis": "underlying",
        "consolidation_scope": "consolidated",
        "source_label": source_label,
        "currency": "AUD",
        "scale": "units",
        "provenance": {
            "source_document_id": str(document_id),
            "metric": "ebit",
            "source_label": source_label,
            "accounting_basis": "underlying",
            "consolidation_scope": "consolidated",
            "page_number": 7,
            "row_ref": source_label,
        },
        "reconciliation_evidence": {
            "source_label": source_label,
            "items": [
                {
                    "label": "Restructuring costs",
                    "value": 5_000_000,
                    "source_ref": "page 7 reconciliation row 3",
                }
            ],
        },
    }


def test_end_to_end_staging_keeps_adjusted_result_out_of_canonical_lane():
    from app.services.financial_observations import stage_financial_observations

    document_id = uuid.uuid4()
    payload = accepted_metric_context(document_id, "ebit")
    payload["metrics"]["ebit"] = 120_000_000
    payload["result_disclosures"] = [adjusted_disclosure(document_id)]
    session = FakeSession()

    observations = stage_financial_observations(
        session,
        document=SimpleNamespace(document_id=document_id, ticker="BHP"),
        extraction_run=SimpleNamespace(
            run_id=uuid.uuid4(), extractor_version="multipass-v9"
        ),
        structured=payload,
    )

    assert [item.value for item in observations] == [Decimal("120000000")]
    assert len(session.executed) == 2
    canonical_values = session.executed[0].compile().params
    disclosure_values = session.executed[1].compile().params
    assert canonical_values["value"] == Decimal("120000000")
    assert canonical_values["accounting_basis"] == "statutory"
    assert disclosure_values["value"] == Decimal("125000000")
    assert disclosure_values["source_label"] == (
        "Underlying EBITDA (management measure)"
    )
    assert disclosure_values["reconciliation_evidence"]["items"][0][
        "source_ref"
    ] == "page 7 reconciliation row 3"


def test_adjusted_canonical_candidate_abstains_but_disclosure_is_retained():
    from app.services.financial_observations import stage_financial_observations

    document_id = uuid.uuid4()
    payload = accepted_metric_context(document_id, "ebit")
    provenance = payload["field_provenance"]["ebit"]
    provenance["row_ref"] = "Consolidated underlying EBIT"
    provenance["source_cell"]["row_label"] = "Consolidated underlying EBIT"
    payload["accounting_basis"] = "underlying"
    payload["result_disclosures"] = [adjusted_disclosure(document_id)]
    session = FakeSession()

    assert stage_financial_observations(
        session,
        document=SimpleNamespace(document_id=document_id, ticker="BHP"),
        extraction_run=SimpleNamespace(
            run_id=uuid.uuid4(), extractor_version="multipass-v9"
        ),
        structured=payload,
    ) == ()
    assert len(session.executed) == 1
    assert (
        session.executed[0].compile().params["source_label"]
        == "Underlying EBITDA (management measure)"
    )


@pytest.mark.parametrize(
    "marker",
    (
        "adjusted",
        "underlying",
        "normalized",
        "normalised",
        "pro forma",
        "pro-forma",
    ),
)
def test_every_non_statutory_spelling_abstains_from_canonical_lane(marker):
    from app.services.financial_observations import stage_financial_observations

    document_id = uuid.uuid4()
    payload = accepted_metric_context(document_id, "ebit")
    provenance = payload["field_provenance"]["ebit"]
    source_label = f"Consolidated statutory {marker} EBIT"
    provenance["row_ref"] = source_label
    provenance["source_cell"]["row_label"] = source_label
    session = FakeSession()

    assert stage_financial_observations(
        session,
        document=SimpleNamespace(document_id=document_id, ticker="BHP"),
        extraction_run=SimpleNamespace(
            run_id=uuid.uuid4(), extractor_version="multipass-v9"
        ),
        structured=payload,
    ) == ()
    assert session.executed == []


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("accounting_basis", None),
        ("accounting_basis", "underlying"),
        ("consolidation_scope", None),
        ("consolidation_scope", "parent"),
    ),
)
def test_canonical_provenance_requires_explicit_statutory_consolidated(
    field, value
):
    from app.services.financial_observations import stage_financial_observations

    document_id = uuid.uuid4()
    payload = accepted_metric_context(document_id, "ebit")
    provenance = payload["field_provenance"]["ebit"]
    if value is None:
        provenance.pop(field)
    else:
        provenance[field] = value
    session = FakeSession()

    assert stage_financial_observations(
        session,
        document=SimpleNamespace(document_id=document_id, ticker="BHP"),
        extraction_run=SimpleNamespace(
            run_id=uuid.uuid4(), extractor_version="multipass-v9"
        ),
        structured=payload,
    ) == ()
    assert session.executed == []


def test_ambiguous_disclosure_basis_or_scope_abstains_from_both_lanes():
    from app.services.financial_observations import stage_financial_observations

    document_id = uuid.uuid4()
    for field, value in (
        ("accounting_basis", None),
        ("accounting_basis", "statutory"),
        ("consolidation_scope", None),
        ("consolidation_scope", "parent"),
    ):
        payload = {
            "result_disclosures": [adjusted_disclosure(document_id)]
        }
        payload["result_disclosures"][0][field] = value
        session = FakeSession()
        assert stage_financial_observations(
            session,
            document=SimpleNamespace(document_id=document_id, ticker="BHP"),
            extraction_run=SimpleNamespace(
                run_id=uuid.uuid4(), extractor_version="multipass-v9"
            ),
            structured=payload,
        ) == ()
        assert session.executed == []


def test_disclosure_requires_exact_label_and_reconciliation_evidence():
    from app.services.financial_observations import (
        stage_financial_result_disclosures,
    )

    document_id = uuid.uuid4()
    for mutation in ("label_mismatch", "missing_reconciliation"):
        candidate = adjusted_disclosure(document_id)
        if mutation == "label_mismatch":
            candidate["provenance"]["source_label"] = "Adjusted EBIT"
        else:
            candidate["reconciliation_evidence"]["items"] = []
        session = FakeSession()
        assert stage_financial_result_disclosures(
            session,
            document=SimpleNamespace(document_id=document_id, ticker="BHP"),
            extraction_run=SimpleNamespace(
                run_id=uuid.uuid4(), extractor_version="multipass-v9"
            ),
            structured={"result_disclosures": [candidate]},
        ) == ()
        assert session.executed == []


@pytest.mark.parametrize("source_label", ("Unadjusted EBIT", "Underlyingness EBIT"))
def test_disclosure_basis_requires_boundary_aware_label_term(source_label):
    from app.services.financial_observations import (
        stage_financial_result_disclosures,
    )

    document_id = uuid.uuid4()
    candidate = adjusted_disclosure(document_id)
    candidate["accounting_basis"] = "adjusted"
    candidate["source_label"] = source_label
    candidate["provenance"]["accounting_basis"] = "adjusted"
    candidate["provenance"]["source_label"] = source_label
    candidate["reconciliation_evidence"]["source_label"] = source_label
    session = FakeSession()

    assert stage_financial_result_disclosures(
        session,
        document=SimpleNamespace(document_id=document_id, ticker="BHP"),
        extraction_run=SimpleNamespace(
            run_id=uuid.uuid4(), extractor_version="multipass-v9"
        ),
        structured={"result_disclosures": [candidate]},
    ) == ()
    assert session.executed == []
