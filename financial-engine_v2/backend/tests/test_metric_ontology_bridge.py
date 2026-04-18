"""Unit tests for app.services.metric_ontology_bridge.

These tests lock in the eval-only ontology projection contract:
    - extractor-target families map strong and are auto_collapse_safe
    - qualifier / period-suffix rows are medium and never auto_collapse_safe
    - supplemental families (ebitda, total_assets, ...) never auto_collapse_safe
    - percent-string raw values override incoming unit_type
    - share-count rows override incoming unit_type
    - per-share patterns become supplemental-only, never canonical
    - unit/family coherence is enforced (family is rejected when unit mismatches)

A replay test runs the entire hand-annotated validation fixture through the
bridge and asserts expected family / unit_type / confidence / collapse-safety.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.services.metric_ontology_bridge import (
    EXTRACTOR_TARGET_FAMILIES,
    SUPPLEMENTAL_FAMILIES,
    MappingConfidence,
    OntologyProjection,
    UnitType,
    project,
)


FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "metric_ontology_bridge"
VALIDATION_PATH = FIXTURE_DIR / "validation.jsonl"


def _datapoint(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "row_label": "",
        "context_text": "",
        "raw_value": "",
        "raw_scale": None,
        "currency": None,
        "unit_type": None,
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Strong canonical mappings
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_plain_revenue_strong_and_collapse_safe() -> None:
    p = project(
        _datapoint(
            row_label="Revenue",
            context_text="Revenue | FY21",
            raw_value="1,234",
            raw_scale="millions",
            currency="USD",
            unit_type="currency",
        )
    )
    assert p.canonical_family == "revenue"
    assert p.unit_type == UnitType.CURRENCY
    assert p.mapping_confidence == MappingConfidence.STRONG
    assert p.auto_collapse_safe is True
    assert "revenue" in p.normalized_label


@pytest.mark.unit
def test_plain_net_debt_strong_and_collapse_safe() -> None:
    p = project(
        _datapoint(
            row_label="Net debt",
            context_text="Balance sheet",
            raw_value="4,121",
            raw_scale="millions",
            currency="USD",
            unit_type="currency",
        )
    )
    assert p.canonical_family == "net_debt"
    assert p.mapping_confidence == MappingConfidence.STRONG
    assert p.auto_collapse_safe is True


@pytest.mark.unit
def test_operating_cf_header_strong() -> None:
    p = project(
        _datapoint(
            row_label="Net cash from operating activities",
            raw_value="8,500",
            raw_scale="millions",
            currency="USD",
            unit_type="currency",
        )
    )
    assert p.canonical_family == "operating_cf"
    assert p.mapping_confidence == MappingConfidence.STRONG
    assert p.auto_collapse_safe is True


# ---------------------------------------------------------------------------
# Quarterly 5B aliases
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_quarterly_cash_flows_from_operating_activities_is_strong() -> None:
    p = project(
        _datapoint(
            row_label="Cash flows from operating activities",
            context_text="Cash flows from operating activities",
            raw_value="21,836",
            raw_scale="thousands",
            currency="AUD",
            unit_type="currency",
        )
    )
    assert p.canonical_family == "operating_cf"
    assert p.mapping_confidence == MappingConfidence.STRONG
    assert p.auto_collapse_safe is True


@pytest.mark.unit
def test_quarterly_fragment_item_1_9_maps_operating_cf_medium() -> None:
    p = project(
        _datapoint(
            row_label="activities (item 1.9 above)",
            context_text=(
                "Consolidated statement of cash flows | "
                "Net cash from / (used in) operating | activities (item 1.9 above)"
            ),
            raw_value="1,154",
            raw_scale="thousands",
            currency="AUD",
            unit_type="currency",
        )
    )
    assert p.canonical_family == "operating_cf"
    assert p.mapping_confidence == MappingConfidence.MEDIUM
    assert p.auto_collapse_safe is False


@pytest.mark.unit
def test_quarterly_fragment_item_3_10_maps_financing_cf_medium() -> None:
    p = project(
        _datapoint(
            row_label="(item 3.10 above)",
            context_text=(
                "Consolidated statement of cash flows | "
                "Net cash from / (used in) financing activities | (item 3.10 above)"
            ),
            raw_value="42,241",
            raw_scale="thousands",
            currency="AUD",
            unit_type="currency",
        )
    )
    assert p.canonical_family == "financing_cf"
    assert p.mapping_confidence == MappingConfidence.MEDIUM
    assert p.auto_collapse_safe is False


@pytest.mark.unit
def test_quarterly_end_cash_fragment_maps_cash_end_medium() -> None:
    p = project(
        _datapoint(
            row_label="quarter (should equal item 4.6 above)",
            context_text=(
                "Consolidated statement of cash flows | "
                "Cash and cash equivalents at end of | quarter (should equal item 4.6 above)"
            ),
            raw_value="21,979",
            raw_scale="thousands",
            currency="AUD",
            unit_type="currency",
        )
    )
    assert p.canonical_family == "cash_end"
    assert p.mapping_confidence == MappingConfidence.MEDIUM
    assert p.auto_collapse_safe is False


# ---------------------------------------------------------------------------
# Qualifier / period-suffix rules
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_underlying_ebit_drops_to_medium_and_not_collapse_safe() -> None:
    p = project(
        _datapoint(
            row_label="Underlying EBIT",
            raw_value="21,500",
            raw_scale="millions",
            currency="USD",
            unit_type="currency",
        )
    )
    assert p.canonical_family == "ebit"
    assert p.mapping_confidence == MappingConfidence.MEDIUM
    assert p.auto_collapse_safe is False
    assert "collapse_blocker_qualifier" in p.notes


@pytest.mark.unit
def test_period_suffix_on_net_debt_drops_collapse_safe() -> None:
    p = project(
        _datapoint(
            row_label="Net debt at the end of the period",
            raw_value="4,121",
            raw_scale="millions",
            currency="USD",
            unit_type="currency",
        )
    )
    assert p.canonical_family == "net_debt"
    assert p.mapping_confidence == MappingConfidence.MEDIUM
    assert p.auto_collapse_safe is False
    assert "period_disambiguation_suffix" in p.notes


# ---------------------------------------------------------------------------
# Supplemental families (known but outside extractor target set)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_ebitda_is_supplemental_not_collapse_safe() -> None:
    p = project(
        _datapoint(
            row_label="EBITDA",
            raw_value="25,000",
            raw_scale="millions",
            currency="USD",
            unit_type="currency",
        )
    )
    assert p.canonical_family == "ebitda"
    assert p.mapping_confidence == MappingConfidence.SUPPLEMENTAL
    assert p.auto_collapse_safe is False
    assert p.canonical_family in SUPPLEMENTAL_FAMILIES
    assert p.canonical_family not in EXTRACTOR_TARGET_FAMILIES


@pytest.mark.unit
def test_total_assets_is_supplemental() -> None:
    p = project(
        _datapoint(
            row_label="Total assets",
            raw_value="500000",
            raw_scale="millions",
            unit_type="currency",
        )
    )
    assert p.canonical_family == "total_assets"
    assert p.mapping_confidence == MappingConfidence.SUPPLEMENTAL
    assert p.auto_collapse_safe is False


# ---------------------------------------------------------------------------
# Unit-type overrides (the main hardening rules of the bridge)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_percent_string_overrides_incoming_currency() -> None:
    p = project(
        _datapoint(
            row_label="up",
            context_text="Results for announcement | Revenue | up",
            raw_value="42%",
            raw_scale="millions",
            currency="USD",
            unit_type="currency",
        )
    )
    assert p.unit_type == UnitType.PERCENTAGE
    assert p.canonical_family is None
    assert p.mapping_confidence == MappingConfidence.UNSUPPORTED
    assert p.auto_collapse_safe is False


@pytest.mark.unit
def test_share_count_label_overrides_incoming_currency() -> None:
    p = project(
        _datapoint(
            row_label="Ordinary shares – issued and fully paid",
            context_text="Share capital",
            raw_value="197,631,816",
            unit_type="currency",
        )
    )
    assert p.unit_type == UnitType.COUNT
    assert p.canonical_family == "shares_outstanding"
    assert p.mapping_confidence == MappingConfidence.STRONG
    assert p.auto_collapse_safe is True


@pytest.mark.unit
def test_per_share_label_becomes_per_share_unit() -> None:
    p = project(
        _datapoint(
            row_label="Basic earnings per ordinary share (cents)",
            context_text="Consolidated income statement",
            raw_value="223.5",
            raw_scale="cents",
            unit_type="per_share",
        )
    )
    assert p.unit_type == UnitType.PER_SHARE
    assert p.canonical_family is None
    assert p.mapping_confidence == MappingConfidence.SUPPLEMENTAL
    assert p.auto_collapse_safe is False


@pytest.mark.unit
def test_cents_scale_with_share_context_becomes_per_share() -> None:
    p = project(
        _datapoint(
            row_label="DPS",
            context_text="Dividends per ordinary share",
            raw_value="6",
            raw_scale="cents",
            unit_type="currency",  # generator lied
        )
    )
    assert p.unit_type == UnitType.PER_SHARE
    assert p.canonical_family is None
    assert p.mapping_confidence == MappingConfidence.SUPPLEMENTAL
    assert p.auto_collapse_safe is False


# ---------------------------------------------------------------------------
# Unit / family coherence rejection
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_net_debt_in_percent_column_is_rejected() -> None:
    p = project(
        _datapoint(
            row_label="Net debt",
            context_text="Movement in net debt by category | (7%)",
            raw_value="4121",
            unit_type="percent_or_ratio",
        )
    )
    assert p.canonical_family is None
    assert p.unit_type == UnitType.PERCENTAGE
    assert p.mapping_confidence == MappingConfidence.UNSUPPORTED
    assert any("unit_type_conflict" in note for note in p.notes)


# ---------------------------------------------------------------------------
# Ambiguous / unsupported rows
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_total_without_context_is_unsupported() -> None:
    p = project(
        _datapoint(
            row_label="Total",
            context_text="BHP Results | Exceptional items by category | Total",
            raw_value="(4,470)",
            raw_scale="millions",
            currency="USD",
            unit_type="currency",
        )
    )
    assert p.canonical_family is None
    assert p.mapping_confidence == MappingConfidence.UNSUPPORTED


@pytest.mark.unit
def test_total_inside_revenue_section_is_weak_revenue() -> None:
    p = project(
        _datapoint(
            row_label="Total",
            context_text="Revenue | breakdown | Total",
            raw_value="60,817",
            raw_scale="millions",
            currency="USD",
            unit_type="currency",
        )
    )
    assert p.canonical_family == "revenue"
    assert p.mapping_confidence == MappingConfidence.WEAK
    assert p.auto_collapse_safe is False


@pytest.mark.unit
def test_geographic_or_customer_label_is_unsupported() -> None:
    p = project(
        _datapoint(
            row_label="Australia",
            context_text="Segment revenue | Australia",
            raw_value="1,500",
            raw_scale="millions",
            currency="AUD",
            unit_type="currency",
        )
    )
    # The leading section "Segment revenue" will trigger a weak revenue match.
    # We accept either weak-revenue or unsupported here; the critical invariant
    # is that auto_collapse_safe stays False.
    assert p.auto_collapse_safe is False
    assert p.mapping_confidence in (
        MappingConfidence.WEAK,
        MappingConfidence.UNSUPPORTED,
    )


# ---------------------------------------------------------------------------
# Empty / degenerate inputs
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_empty_row_label_is_unknown_and_unsupported() -> None:
    p = project(_datapoint(row_label="", raw_value="1000"))
    assert p.canonical_family is None
    assert p.mapping_confidence == MappingConfidence.UNSUPPORTED
    assert p.auto_collapse_safe is False


@pytest.mark.unit
def test_projection_is_hashable_and_frozen() -> None:
    p = project(_datapoint(row_label="Revenue", raw_value="1", unit_type="currency"))
    assert isinstance(p, OntologyProjection)
    with pytest.raises(Exception):
        p.canonical_family = "ebit"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Validation-set replay (142 hand-annotated rows)
# ---------------------------------------------------------------------------


def _load_validation_rows() -> list[dict]:
    if not VALIDATION_PATH.exists():
        pytest.skip(f"validation fixture missing: {VALIDATION_PATH}")
    with VALIDATION_PATH.open(encoding="utf-8") as fh:
        return [json.loads(ln) for ln in fh if ln.strip()]


@pytest.mark.unit
def test_validation_replay_family_and_collapse_gate() -> None:
    """Replay every labelled row through the bridge.

    We are strict on `auto_collapse_safe` and `unit_type` because those are
    the critical safety invariants. We are strict on `canonical_family` for
    strong/medium/supplemental rows, but allow a weak/unsupported divergence
    for borderline rows (e.g., the `Total under Exceptional` case where the
    human labeller and the bridge may disagree on whether any family is
    borrowable from context at all — both outcomes must still yield
    auto_collapse_safe=False).
    """
    rows = _load_validation_rows()
    assert rows, "validation set is empty"

    divergences: list[str] = []

    for rec in rows:
        dp = {
            "row_label": rec["row_label"],
            "context_text": rec["context_text"],
            "raw_value": rec["raw_value"],
            "raw_scale": rec["raw_scale_src"],
            "currency": rec["currency_src"],
            "unit_type": rec["unit_type_src"],
        }
        expected = rec["expected"]
        p = project(dp)

        # Unit type must match exactly (critical invariant)
        if p.unit_type.value != expected["unit_type"]:
            divergences.append(
                f"UNIT {rec['datapoint_id']}: bridge={p.unit_type.value} "
                f"expected={expected['unit_type']}"
            )

        # auto_collapse_safe must match exactly (the safety gate)
        if p.auto_collapse_safe != expected["auto_collapse_safe"]:
            divergences.append(
                f"COLLAPSE {rec['datapoint_id']}: bridge={p.auto_collapse_safe} "
                f"expected={expected['auto_collapse_safe']}"
            )

        # Family: strict for strong / medium / supplemental
        conf = expected["mapping_confidence"]
        if conf in {"strong", "medium", "supplemental"}:
            if p.canonical_family != expected["canonical_family"]:
                divergences.append(
                    f"FAMILY {rec['datapoint_id']}: bridge={p.canonical_family} "
                    f"expected={expected['canonical_family']} conf={conf}"
                )

    assert not divergences, "validation replay divergences:\n" + "\n".join(
        divergences[:40]
    )


@pytest.mark.unit
def test_validation_replay_no_silent_percent_to_currency() -> None:
    """No row whose raw_value ends with '%' should survive as currency."""
    rows = _load_validation_rows()
    for rec in rows:
        if str(rec["raw_value"]).strip().endswith("%"):
            dp = {
                "row_label": rec["row_label"],
                "context_text": rec["context_text"],
                "raw_value": rec["raw_value"],
                "raw_scale": rec["raw_scale_src"],
                "currency": rec["currency_src"],
                "unit_type": rec["unit_type_src"],
            }
            p = project(dp)
            assert p.unit_type == UnitType.PERCENTAGE, rec["datapoint_id"]
            assert p.canonical_family is None, rec["datapoint_id"]
            assert p.auto_collapse_safe is False, rec["datapoint_id"]
