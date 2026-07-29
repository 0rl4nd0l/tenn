from datetime import date
from decimal import Decimal
from types import SimpleNamespace
import uuid

import pytest


class FakeQuery:
    def __init__(self, rows):
        self.rows = rows

    def filter(self, *_criteria):
        return self

    def all(self):
        return self.rows


class FakeSession:
    def __init__(self, *, rows=None, get_rows=None):
        self.rows = rows or {}
        self.get_rows = get_rows or {}
        self.executed = []
        self.commits = 0

    def query(self, model):
        return FakeQuery(self.rows.get(model, []))

    def get(self, model, identity):
        return self.get_rows.get((model, identity))

    def execute(self, statement):
        self.executed.append(statement)
        return SimpleNamespace(rowcount=1)

    def commit(self):
        self.commits += 1


def review_candidate(kind="conflicting", *, evidence=True, value=125):
    return {
        "metric": "revenue",
        "proposed_value": value,
        "period_end": "2025-06-30",
        "period_basis": "A",
        "currency": "AUD",
        "scale": "millions",
        "review_kind": kind,
        "reason_codes": [f"{kind}_source_values"],
        "source_evidence": (
            {
                "page_number": 42,
                "table_or_region": "Consolidated income statement",
                "row_ref": "Revenue",
                "cell_ref": "row 3, column 2025",
            }
            if evidence
            else {}
        ),
    }


@pytest.mark.parametrize(
    "kind", ("conflicting", "ambiguous", "abstained", "quarantined")
)
def test_unresolved_observations_enter_review_queue_with_reason_codes(kind):
    from app.services.financial_observations import (
        stage_financial_observation_reviews,
    )

    session = FakeSession()
    staged = stage_financial_observation_reviews(
        session,
        document=SimpleNamespace(document_id=uuid.uuid4(), ticker="BHP"),
        extraction_run=SimpleNamespace(
            run_id=uuid.uuid4(), extractor_version="fake-v1"
        ),
        structured={"observation_reviews": [review_candidate(kind)]},
    )

    assert len(staged) == 1
    assert staged[0].review_kind == kind
    assert staged[0].reason_codes == [f"{kind}_source_values"]
    assert len(session.executed) == 1


def real_outcome(kind):
    payload = {
        "metrics": {"revenue": 125},
        "period_end": "2025-06-30",
        "period_type": "A",
        "currency": "AUD",
        "field_provenance": {
            "revenue": {
                "page_number": 42,
                "table_or_region": "Consolidated income statement",
                "row_ref": "Revenue",
                "cell_ref": "row 3, column 2025",
                "scale": "millions",
            }
        },
    }
    if kind in {"conflicting", "ambiguous"}:
        code = (
            "conflicting_source_coordinates"
            if kind == "conflicting"
            else "ambiguous_source_cell"
        )
        payload["provenance_summary"] = {
            "issues": [{"code": code, "field": "revenue"}]
        }
    else:
        payload["trust_outcome"] = (
            "abstain" if kind == "abstained" else "quarantine"
        )
        payload["trust_triggers"] = [f"{kind}_metric_outcome"]
    return payload


@pytest.mark.parametrize(
    "kind", ("conflicting", "ambiguous", "abstained", "quarantined")
)
def test_real_outcome_shapes_enter_review_queue(kind):
    from app.services.financial_observations import (
        stage_financial_observation_reviews,
    )

    session = FakeSession()
    staged = stage_financial_observation_reviews(
        session,
        document=SimpleNamespace(document_id=uuid.uuid4(), ticker="BHP"),
        extraction_run=SimpleNamespace(
            run_id=uuid.uuid4(), extractor_version="fake-v1"
        ),
        structured=real_outcome(kind),
    )

    assert len(staged) == 1
    assert staged[0].review_kind == kind
    assert staged[0].reason_codes
    assert len(session.executed) == 1


def test_missing_location_evidence_is_queued_with_reason_codes():
    from app.services.financial_observations import (
        stage_financial_observation_reviews,
    )

    candidate = review_candidate(evidence=False)
    session = FakeSession()
    staged = stage_financial_observation_reviews(
        session,
        document=SimpleNamespace(document_id=uuid.uuid4(), ticker="BHP"),
        extraction_run=SimpleNamespace(
            run_id=uuid.uuid4(), extractor_version="fake-v1"
        ),
        structured={"observation_reviews": [candidate]},
    )

    assert len(staged) == 1
    assert set(staged[0].reason_codes) >= {
        "missing_evidence_page_number",
        "missing_evidence_table_or_region",
        "missing_evidence_row_ref",
        "missing_evidence_cell_ref",
    }


def test_review_item_exposes_location_period_currency_and_scale():
    from app.models.financial_observations import FinancialObservationReview
    from app.services.financial_observations import (
        pending_financial_observation_reviews,
    )

    row = FinancialObservationReview(
        review_id=uuid.uuid4(),
        source_document_id=uuid.uuid4(),
        extraction_run_id=uuid.uuid4(),
        extractor_version="fake-v1",
        ticker="BHP",
        metric="revenue",
        proposed_value=Decimal("125"),
        period_end=date(2025, 6, 30),
        period_basis="A",
        currency="AUD",
        scale="millions",
        review_kind="ambiguous",
        reason_codes=["ambiguous_column"],
        source_evidence=review_candidate()["source_evidence"],
        status="pending",
        decision=None,
        decision_note=None,
    )

    item = pending_financial_observation_reviews(
        FakeSession(rows={FinancialObservationReview: [row]}), ticker="BHP"
    )[0]
    assert item["source_evidence"] == {
        "page_number": 42,
        "table_or_region": "Consolidated income statement",
        "row_ref": "Revenue",
        "cell_ref": "row 3, column 2025",
    }
    assert (item["period_end"], item["period_basis"]) == (
        date(2025, 6, 30),
        "A",
    )
    assert (item["currency"], item["scale"]) == ("AUD", "millions")


def _review(*, evidence=True, value=125):
    from app.models.financial_observations import FinancialObservationReview

    candidate = review_candidate(evidence=evidence, value=value)
    return FinancialObservationReview(
        review_id=uuid.uuid4(),
        source_document_id=uuid.uuid4(),
        extraction_run_id=uuid.uuid4(),
        extractor_version="fake-v1",
        ticker="BHP",
        metric=candidate["metric"],
        proposed_value=(
            Decimal(str(candidate["proposed_value"]))
            if candidate["proposed_value"] is not None
            else None
        ),
        period_end=date.fromisoformat(candidate["period_end"]),
        period_basis=candidate["period_basis"],
        currency=candidate["currency"],
        scale=candidate["scale"],
        review_kind=candidate["review_kind"],
        reason_codes=candidate["reason_codes"],
        source_evidence=candidate["source_evidence"],
        status="pending",
        decision=None,
        decision_note=None,
    )


@pytest.mark.parametrize(
    ("evidence", "value"), ((False, 125), (True, None))
)
def test_review_approval_cannot_promote_without_value_and_source_evidence(
    evidence, value
):
    from app.models.financial_observations import FinancialObservationReview
    from app.services.financial_observations import (
        decide_financial_observation_review,
    )

    review = _review(evidence=evidence, value=value)
    session = FakeSession(
        get_rows={(FinancialObservationReview, review.review_id): review}
    )
    with pytest.raises(
        ValueError,
        match="approval requires a proposed value with source evidence",
    ):
        decide_financial_observation_review(
            session, review_id=review.review_id, decision="approve"
        )
    assert session.executed == []
    assert review.status == "pending"


def test_evidence_backed_approval_promotes_an_accepted_profile_observation():
    from app.models.financial_observations import FinancialObservationReview
    from app.services.financial_observations import (
        decide_financial_observation_review,
    )

    review = _review()
    session = FakeSession(
        get_rows={(FinancialObservationReview, review.review_id): review}
    )
    observation = decide_financial_observation_review(
        session,
        review_id=review.review_id,
        decision="approve",
        note="Source cells checked",
    )

    assert observation is not None
    assert observation.trust_state == "accepted"
    assert observation.value == Decimal("125000000")
    assert observation.provenance["review_id"] == str(review.review_id)
    assert observation.provenance["page_number"] == 42
    assert review.status == "approved"
    assert len(session.executed) == 1


def test_trusted_observation_path_does_not_require_a_review():
    from app.services.financial_observations import stage_financial_observations
    from test_financial_observations import accepted_context

    document_id = uuid.uuid4()
    session = FakeSession()
    observations = stage_financial_observations(
        session,
        document=SimpleNamespace(document_id=document_id, ticker="BHP"),
        extraction_run=SimpleNamespace(
            run_id=uuid.uuid4(), extractor_version="fake-v1"
        ),
        structured=accepted_context(document_id),
    )

    assert len(observations) == 1
    assert observations[0].trust_state == "accepted"
    assert len(session.executed) == 1
