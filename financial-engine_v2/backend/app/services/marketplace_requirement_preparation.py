from __future__ import annotations

from typing import Any

from app.services.marketplace_mission_service import (
    MarketplaceMissionNotFound,
    MarketplaceMissionService,
)
from app.services.marketplace_price_intelligence import MarketplacePriceIntelligenceService
from app.services.marketplace_requirement_resolver import (
    build_requirement_profile,
    candidate_search_terms,
    generate_requirement_candidate_specs,
)


class RequirementMissionPreparationError(RuntimeError):
    """Requirement-driven mission preparation failed before scan execution."""

    def __init__(self, mission_id: str, reason: str) -> None:
        self.mission_id = mission_id
        self.reason = reason
        super().__init__(
            f"Requirement-driven Marketplace mission {mission_id} is not scan-ready: {reason}"
        )


def marketplace_requirement_profile(mission: dict[str, Any]) -> dict[str, Any] | None:
    profile = mission.get("requirement_profile")
    if isinstance(profile, dict):
        return profile
    deployment_args = mission.get("deployment_args")
    if isinstance(deployment_args, dict) and isinstance(
        deployment_args.get("requirement_profile"),
        dict,
    ):
        return deployment_args["requirement_profile"]
    return None


def _build_profile_from_mission(mission: dict[str, Any]) -> dict[str, Any]:
    return build_requirement_profile(
        {
            "name": mission.get("name"),
            "brief": mission.get("brief"),
            "user_goal": mission.get("user_goal") or mission.get("brief"),
            "category_hint": mission.get("category_hint"),
            "hard_filters": mission.get("hard_filters") or {},
            "soft_preferences": mission.get("soft_preferences") or {},
        }
    )


def _deployment_args(mission: dict[str, Any]) -> dict[str, Any]:
    args = mission.get("deployment_args")
    return dict(args) if isinstance(args, dict) else {}


def _with_requirement_profile(
    mission: dict[str, Any],
    profile: dict[str, Any],
) -> dict[str, Any]:
    return {**mission, "requirement_profile": profile}


def _candidate_products_present(
    price_service: MarketplacePriceIntelligenceService,
    candidates: list[dict[str, Any]],
) -> bool:
    if not candidates:
        return False
    for candidate in candidates:
        tracked_product_id = str(candidate.get("tracked_product_id") or "")
        if not tracked_product_id:
            return False
        if price_service.get_tracked_product(tracked_product_id) is None:
            return False
    return True


def marketplace_candidate_contexts(
    mission_service: MarketplaceMissionService,
    price_service: MarketplacePriceIntelligenceService,
    mission_id: str,
) -> list[dict[str, Any]]:
    contexts: list[dict[str, Any]] = []
    for candidate in mission_service.list_mission_candidate_products(mission_id):
        product = price_service.get_tracked_product(
            str(candidate.get("tracked_product_id") or "")
        )
        snapshot = (
            price_service.latest_benchmark_snapshot(product["tracked_product_id"])
            if product is not None
            else None
        )
        contexts.append(
            {
                "candidate": candidate,
                "tracked_product": product,
                "benchmark_snapshot": snapshot,
                "benchmark_state": price_service.build_benchmark_state(
                    product,
                    snapshot,
                ),
            }
        )
    return contexts


def marketplace_candidate_products_payload(
    mission_service: MarketplaceMissionService,
    price_service: MarketplacePriceIntelligenceService,
    mission_id: str,
) -> list[dict[str, Any]]:
    payload: list[dict[str, Any]] = []
    for context in marketplace_candidate_contexts(
        mission_service,
        price_service,
        mission_id,
    ):
        candidate = (
            context.get("candidate") if isinstance(context.get("candidate"), dict) else {}
        )
        product = context.get("tracked_product")
        payload.append(
            {
                **candidate,
                "tracked_product": product,
                "benchmark_state": context.get("benchmark_state"),
                "warning": None
                if product is not None
                else "Candidate tracked product was not found.",
            }
        )
    return payload


def prepare_requirement_driven_mission(
    mission_service: MarketplaceMissionService,
    price_service: MarketplacePriceIntelligenceService,
    mission_or_id: dict[str, Any] | str,
) -> dict[str, Any]:
    """Prepare candidate state for requirement-driven marketplace missions.

    Exact-product missions bypass cleanly. Requirement-driven missions either
    persist candidate products/search terms or raise a fail-closed error.
    """

    if isinstance(mission_or_id, str):
        mission = mission_service.get_mission(mission_or_id)
        if mission is None:
            raise MarketplaceMissionNotFound(mission_or_id)
    else:
        mission = mission_or_id

    mission_id = str(mission.get("mission_id") or "").strip()
    if not mission_id:
        return mission

    deployment_args = _deployment_args(mission)
    profile = marketplace_requirement_profile(mission) or _build_profile_from_mission(
        mission
    )
    if not isinstance(profile, dict):
        raise RequirementMissionPreparationError(
            mission_id,
            "missing requirement profile",
        )

    existing_candidates = mission_service.list_mission_candidate_products(mission_id)
    if profile.get("mode") != "requirement_driven":
        if existing_candidates:
            mission_service.replace_mission_candidate_products(mission_id, [])
        cleaned_args = {
            key: value
            for key, value in deployment_args.items()
            if key not in {"candidate_search_terms", "candidate_count"}
        }
        if cleaned_args.get("requirement_profile") != profile:
            cleaned_args["requirement_profile"] = profile
        if cleaned_args != deployment_args:
            return _with_requirement_profile(
                mission_service.update_mission(
                    mission_id,
                    {"deployment_args": cleaned_args},
                ),
                profile,
            )
        return _with_requirement_profile(mission, profile)

    if not profile.get("category"):
        raise RequirementMissionPreparationError(
            mission_id,
            "missing requirement category",
        )
    if profile.get("unsupported_reason"):
        raise RequirementMissionPreparationError(
            mission_id,
            str(profile["unsupported_reason"]),
        )

    candidate_specs = generate_requirement_candidate_specs(profile)
    if not candidate_specs:
        raise RequirementMissionPreparationError(
            mission_id,
            "no candidate products generated",
        )
    search_terms = candidate_search_terms(candidate_specs)
    if not search_terms:
        raise RequirementMissionPreparationError(
            mission_id,
            "no candidate search terms generated",
        )

    expected_keys = [str(spec.get("canonical_key") or "") for spec in candidate_specs]
    existing_keys = [str(item.get("candidate_key") or "") for item in existing_candidates]
    if (
        existing_keys == expected_keys
        and list(deployment_args.get("candidate_search_terms") or []) == search_terms
        and int(deployment_args.get("candidate_count") or 0) == len(expected_keys)
        and deployment_args.get("requirement_profile") == profile
        and _candidate_products_present(price_service, existing_candidates)
    ):
        return _with_requirement_profile(mission, profile)

    candidate_rows: list[dict[str, Any]] = []
    for index, spec in enumerate(candidate_specs, start=1):
        product = price_service.get_or_create_tracked_product(spec)
        candidate_rows.append(
            {
                **spec,
                "tracked_product_id": product["tracked_product_id"],
                "candidate_key": spec["canonical_key"],
                "candidate_rank": index,
            }
        )

    mission_service.replace_mission_candidate_products(mission_id, candidate_rows)
    return _with_requirement_profile(
        mission_service.update_mission(
            mission_id,
            {
                "deployment_args": {
                    **deployment_args,
                    "requirement_profile": profile,
                    "candidate_search_terms": search_terms,
                    "candidate_count": len(candidate_rows),
                }
            },
        ),
        profile,
    )
