import json
import re
import unittest
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SCHEMA_VERSION = "strategy_lab_artifact_v1"
HELPER_SCHEMA_VERSION = "strategy_lab_sidecar_artifact_v1"
PHASE3C_FIXTURE_VERSION = "strategy_lab_mock_transport_phase3c_v1"
PHASE3C_JOB_ID = "strategy_lab_offline_mock_transport_phase3c_v1_20260521"


def load_json(relative_path: str) -> Any:
    with (ROOT / relative_path).open(encoding="utf-8") as handle:
        return json.load(handle)


def rel_json_paths(pattern: str) -> list[str]:
    return sorted(path.relative_to(ROOT).as_posix() for path in ROOT.glob(pattern))


def walk_json(value: Any) -> Any:
    if isinstance(value, dict):
        for key, item in value.items():
            yield key, item
            yield from walk_json(item)
    elif isinstance(value, list):
        for item in value:
            yield from walk_json(item)


class LifecycleState(Enum):
    CREATED = "CREATED"
    POLICY_CHECKED = "POLICY_CHECKED"
    DISPATCHED_TO_MOCK = "DISPATCHED_TO_MOCK"
    MOCK_RESULT_READY = "MOCK_RESULT_READY"
    NORMALIZED_TO_PENDING_ARTIFACT = "NORMALIZED_TO_PENDING_ARTIFACT"
    QUARANTINED = "QUARANTINED"
    DATA_MISSING = "DATA_MISSING"
    POLICY_DENIED = "POLICY_DENIED"
    TIMEOUT_SIMULATED = "TIMEOUT_SIMULATED"
    SIDE_CAR_UNAVAILABLE_SIMULATED = "SIDE_CAR_UNAVAILABLE_SIMULATED"


@dataclass(frozen=True)
class StrategyLabTransportRequest:
    operation: str
    payload: dict[str, Any]
    fixture_name: str = "inline_request"


@dataclass(frozen=True)
class StrategyLabTransportPolicyDecision:
    decision: str
    policy_checked: bool
    reason_codes: tuple[str, ...]


@dataclass(frozen=True)
class StrategyLabTransportResponse:
    decision: StrategyLabTransportPolicyDecision
    lifecycle: tuple[LifecycleState, ...]
    artifact_emitted: bool
    quarantined: bool


class StrategyLabTransportPolicy:
    allow_mock_only = frozenset(
        {
            "list_capabilities",
            "read_market_snapshot",
            "submit_backtest",
            "get_backtest_result",
            "get_job",
            "regime_detect",
        }
    )
    default_hold = frozenset({"parameter_sweep", "structured_tune"})
    local_mock_conversion_only = frozenset({"export_artifact"})
    blocked_operations = frozenset(
        {
            "broker_credential_setup",
            "exchange_key_setup",
            "paper_order_placement",
            "live_order_placement",
            "bot_activation",
            "admin_token_changes",
            "strategy_live_workspace_run",
            "quick_trade_orders",
            "kill_switch_interactions",
            "direct_tenn_db_write",
            "direct_qdrant_write",
            "direct_news_write",
            "direct_memory_write",
            "direct_financial_truth_write",
            "parser_gold_label_write",
            "source_registry_write",
        }
    )
    forbidden_field_names = frozenset(
        {
            "broker_credentials",
            "exchange_credentials",
            "api_key",
            "secret",
            "paper_order",
            "live_order",
            "order_payload",
            "execution_order",
            "broker_account",
            "exchange_account",
            "quick_trade_order",
            "kill_switch_command",
            "bot_activation",
            "store_write",
            "store_write_intent",
            "direct_db_write",
            "qdrant_write",
            "news_write",
            "memory_write",
            "financial_truth_write",
            "parser_gold_label_write",
            "source_registry_write",
            "token_admin_change",
            "runtime_route",
            "service_startup",
        }
    )

    def evaluate(self, request: StrategyLabTransportRequest) -> StrategyLabTransportPolicyDecision:
        payload = request.payload
        reasons: list[str] = []

        if request.operation in self.blocked_operations:
            reasons.append("FORBIDDEN_OPERATION")
        if payload.get("production_data_access") is not False:
            reasons.append("PRODUCTION_DATA_ACCESS_DENIED")
        if payload.get("execution_allowed") is not False:
            reasons.append("EXECUTION_DENIED")
        if payload.get("paper_live_scope") != "none":
            reasons.append("PAPER_LIVE_SCOPE_DENIED")
        if self._contains_forbidden_field(payload):
            reasons.append("FORBIDDEN_FIELD_DENIED")

        if reasons:
            return StrategyLabTransportPolicyDecision("deny", True, tuple(reasons))
        if request.operation in self.allow_mock_only:
            return StrategyLabTransportPolicyDecision("allow_mock_only", True, ("OFFLINE_MOCK_OPERATION",))
        if request.operation in self.default_hold:
            return StrategyLabTransportPolicyDecision("default_hold", True, ("DATA_MISSING_SHAPE_NOT_PROVEN",))
        if request.operation in self.local_mock_conversion_only:
            if payload.get("input", {}).get("local_mock_conversion") is True:
                return StrategyLabTransportPolicyDecision(
                    "allow_local_mock_conversion_only",
                    True,
                    ("LOCAL_MOCK_CONVERSION_ONLY",),
                )
            return StrategyLabTransportPolicyDecision("deny", True, ("EXPORT_REQUIRES_LOCAL_MOCK_CONVERSION",))
        return StrategyLabTransportPolicyDecision("deny", True, ("UNRECOGNIZED_OPERATION",))

    def _contains_forbidden_field(self, value: Any) -> bool:
        if isinstance(value, dict):
            for key, item in value.items():
                if key == "store_write" and item is False:
                    continue
                if key in self.forbidden_field_names:
                    return True
                if self._contains_forbidden_field(item):
                    return True
        elif isinstance(value, list):
            return any(self._contains_forbidden_field(item) for item in value)
        return False


class StrategyLabMockTransport:
    def __init__(self) -> None:
        self.policy = StrategyLabTransportPolicy()

    def dispatch_fixture(self, fixture: dict[str, Any]) -> StrategyLabTransportResponse:
        request_payload = fixture["request"]
        request = StrategyLabTransportRequest(
            operation=request_payload["operation"],
            payload=request_payload,
            fixture_name=fixture["fixture_name"],
        )
        decision = self.policy.evaluate(request)
        lifecycle = [LifecycleState.CREATED, LifecycleState.POLICY_CHECKED]

        if decision.decision == "deny":
            return StrategyLabTransportResponse(decision, tuple([*lifecycle, LifecycleState.POLICY_DENIED]), False, False)
        if decision.decision == "default_hold":
            return StrategyLabTransportResponse(decision, tuple([*lifecycle, LifecycleState.DATA_MISSING]), False, False)

        lifecycle.append(LifecycleState.DISPATCHED_TO_MOCK)
        response = fixture["transport_response"]
        fixture_state = LifecycleState(response["lifecycle_state"])
        emission = response["artifact_emission_decision"]
        quarantine = response["quarantine_decision"]

        if fixture_state == LifecycleState.NORMALIZED_TO_PENDING_ARTIFACT:
            lifecycle.extend([LifecycleState.MOCK_RESULT_READY, LifecycleState.NORMALIZED_TO_PENDING_ARTIFACT])
        elif fixture_state == LifecycleState.MOCK_RESULT_READY:
            lifecycle.append(LifecycleState.MOCK_RESULT_READY)
        else:
            lifecycle.append(fixture_state)

        return StrategyLabTransportResponse(
            decision=decision,
            lifecycle=tuple(lifecycle),
            artifact_emitted=bool(emission["artifact_emitted"]),
            quarantined=bool(quarantine["quarantined"]),
        )


class StrategyLabOfflineMockTransportPhase3CTests(unittest.TestCase):
    def setUp(self) -> None:
        self.schema = load_json("docs/strategy_lab/artifact_schema_v1.schema.json")
        self.policy_vector = load_json("docs/strategy_lab/mock_test_vectors/reconciled_schema_policy_v1.json")
        self.mapping_vector = load_json("docs/strategy_lab/mock_test_vectors/helper_to_artifact_mapping_cases_v1.json")
        self.quarantine_vector = load_json("docs/strategy_lab/mock_test_vectors/quarantine_cases_v1.json")
        self.blocked_vector = load_json("docs/strategy_lab/mock_test_vectors/blocked_surfaces_v1.json")
        self.transport = StrategyLabMockTransport()

    def test_json_parse_coverage(self) -> None:
        phase3b_paths = []
        phase3b_paths.extend(rel_json_paths("docs/strategy_lab/mock_payloads/*.json"))
        phase3b_paths.extend(rel_json_paths("docs/strategy_lab/mock_test_vectors/*.json"))

        phase3c_fixture_paths = rel_json_paths("docs/strategy_lab/mock_transport_fixtures/*.json")
        authoritative_paths = ["docs/strategy_lab/artifact_schema_v1.schema.json"]
        authoritative_paths.extend(rel_json_paths("docs/strategy_lab/artifact_fixtures/*.json"))

        self.assertGreaterEqual(len(phase3b_paths), 1)
        self.assertEqual(len(phase3c_fixture_paths), 12)
        self.assertGreaterEqual(len(authoritative_paths), 1)

        for path in [*phase3b_paths, *phase3c_fixture_paths, *authoritative_paths]:
            with self.subTest(path=path):
                loaded = load_json(path)
                self.assertIsInstance(loaded, (dict, list))

    def test_phase3c_test_file_import_hygiene(self) -> None:
        test_text = (ROOT / "tests/strategy_lab/test_strategy_lab_offline_mock_transport_phase3c.py").read_text(
            encoding="utf-8"
        )
        allowed_import_roots = {"json", "re", "unittest", "dataclasses", "enum", "pathlib", "typing"}
        import_pattern = re.compile(r"^\s*(?:from|import)\s+([A-Za-z0-9_\.]+)", re.MULTILINE)
        forbidden_import_pattern = re.compile(
            r"^\s*(?:from|import)\s+"
            r"(?:requests|httpx|aiohttp|socket|subprocess|docker|mcp|quantdinger|"
            r"financial_engine_v2|backend|app|qdrant|news|memory)\b",
            re.MULTILINE,
        )
        helper_import_pattern = re.compile(r"^\s*(?:from|import)\s+.*strategy_lab_artifact_schema", re.MULTILINE)

        imported_roots = {match.split(".")[0] for match in import_pattern.findall(test_text)}
        self.assertTrue(imported_roots)
        self.assertTrue(imported_roots.issubset(allowed_import_roots))
        self.assertIsNone(forbidden_import_pattern.search(test_text))
        self.assertIsNone(helper_import_pattern.search(test_text))

    def test_fixture_contract_shape_and_lifecycle_states(self) -> None:
        expected_names = {
            "valid_capabilities_transport_response_v1",
            "valid_market_snapshot_transport_response_v1",
            "valid_submit_backtest_transport_response_v1",
            "valid_get_backtest_result_transport_response_v1",
            "valid_regime_detect_transport_response_v1",
            "invalid_policy_denied_transport_response_v1",
            "invalid_trading_scope_transport_response_v1",
            "invalid_missing_raw_payload_ref_transport_response_v1",
            "invalid_sidecar_unavailable_transport_response_v1",
            "invalid_timeout_transport_response_v1",
            "invalid_order_field_transport_response_v1",
            "invalid_store_write_transport_response_v1",
        }
        paths = rel_json_paths("docs/strategy_lab/mock_transport_fixtures/*.json")
        names = set()

        for path in paths:
            fixture = load_json(path)
            names.add(fixture["fixture_name"])
            response = fixture["transport_response"]
            with self.subTest(path=path):
                self.assertEqual(fixture["transport_fixture_version"], PHASE3C_FIXTURE_VERSION)
                self.assertEqual(fixture["request"]["job_id"], PHASE3C_JOB_ID)
                self.assertIs(fixture["policy_decision"]["policy_checked"], True)
                self.assertIn(LifecycleState(response["lifecycle_state"]), set(LifecycleState))
                self.assertIn("artifact_emission_decision", response)
                self.assertIn("quarantine_decision", response)
                self.assertIn("audit_record", response)
                self.assertIs(response["audit_record"]["policy_checked_before_dispatch"], True)

        self.assertEqual(names, expected_names)

    def test_transport_policy_gate_before_dispatch(self) -> None:
        for path in rel_json_paths("docs/strategy_lab/mock_transport_fixtures/*.json"):
            fixture = load_json(path)
            result = self.transport.dispatch_fixture(fixture)
            with self.subTest(path=path):
                self.assertEqual(result.lifecycle[0], LifecycleState.CREATED)
                self.assertIn(LifecycleState.POLICY_CHECKED, result.lifecycle)
                self.assertIs(result.decision.policy_checked, True)
                if result.decision.decision == "deny":
                    self.assertIn(LifecycleState.POLICY_DENIED, result.lifecycle)
                    self.assertNotIn(LifecycleState.DISPATCHED_TO_MOCK, result.lifecycle)
                    self.assertFalse(result.artifact_emitted)

        denied_paths = {
            "docs/strategy_lab/mock_transport_fixtures/invalid_policy_denied_transport_response_v1.json",
            "docs/strategy_lab/mock_transport_fixtures/invalid_trading_scope_transport_response_v1.json",
            "docs/strategy_lab/mock_transport_fixtures/invalid_order_field_transport_response_v1.json",
            "docs/strategy_lab/mock_transport_fixtures/invalid_store_write_transport_response_v1.json",
        }
        for path in denied_paths:
            fixture = load_json(path)
            result = self.transport.dispatch_fixture(fixture)
            with self.subTest(path=path):
                self.assertEqual(result.decision.decision, "deny")
                self.assertFalse(result.artifact_emitted)

    def test_allowed_mock_operation_coverage(self) -> None:
        policy = StrategyLabTransportPolicy()
        expected_allowed = {
            "list_capabilities",
            "read_market_snapshot",
            "submit_backtest",
            "get_backtest_result",
            "get_job",
            "regime_detect",
        }
        self.assertEqual(set(policy.allow_mock_only), expected_allowed)

        for operation in sorted(expected_allowed):
            request = StrategyLabTransportRequest(operation, self._base_request(operation))
            with self.subTest(operation=operation):
                self.assertEqual(policy.evaluate(request).decision, "allow_mock_only")

        for operation in ("parameter_sweep", "structured_tune"):
            request = StrategyLabTransportRequest(operation, self._base_request(operation))
            with self.subTest(operation=operation):
                decision = policy.evaluate(request)
                self.assertEqual(decision.decision, "default_hold")
                self.assertIn("DATA_MISSING_SHAPE_NOT_PROVEN", decision.reason_codes)

        export_request = self._base_request("export_artifact")
        export_request["input"] = {"local_mock_conversion": True, "store_write": False}
        decision = policy.evaluate(StrategyLabTransportRequest("export_artifact", export_request))
        self.assertEqual(decision.decision, "allow_local_mock_conversion_only")

    def test_blocked_mock_operation_coverage(self) -> None:
        expected_surfaces = {
            "broker credential setup",
            "exchange key setup",
            "paper order placement",
            "live order placement",
            "bot activation",
            "admin token changes",
            "strategy create/update/run against live workspace",
            "quick-trade orders",
            "kill-switch interactions",
            "direct Tenn DB writes",
            "direct Qdrant writes",
            "direct news writes",
            "direct memory writes",
            "direct financial-truth writes",
            "parser/extraction/gold-label writes",
            "source-registry writes",
        }
        blocked_surfaces = {entry["surface"] for entry in self.blocked_vector["blocked_surfaces"]}
        self.assertEqual(blocked_surfaces, expected_surfaces)

        policy = StrategyLabTransportPolicy()
        for operation in sorted(policy.blocked_operations):
            request = StrategyLabTransportRequest(operation, self._base_request(operation))
            with self.subTest(operation=operation):
                self.assertEqual(policy.evaluate(request).decision, "deny")

    def test_artifact_emission_boundary_preserves_authoritative_envelope(self) -> None:
        required_fields = set(self.schema["required"])
        expected_flags = self.policy_vector["required_artifact_flags"]
        artifact_fixture_paths = [
            "docs/strategy_lab/mock_transport_fixtures/valid_get_backtest_result_transport_response_v1.json",
            "docs/strategy_lab/mock_transport_fixtures/valid_regime_detect_transport_response_v1.json",
        ]

        for fixture_path in artifact_fixture_paths:
            fixture = load_json(fixture_path)
            emission = fixture["transport_response"]["artifact_emission_decision"]
            artifact = load_json(emission["artifact_ref"])
            with self.subTest(fixture_path=fixture_path):
                self.assertTrue(emission["artifact_emitted"])
                self.assertEqual(emission["schema_version"], SCHEMA_VERSION)
                self.assertEqual(artifact["schema_version"], SCHEMA_VERSION)
                self.assertTrue(required_fields.issubset(artifact))
                self.assertIn("raw_payload_ref", artifact)
                self.assertIn("provenance", artifact)
                self.assertTrue(artifact["assumptions"])
                self.assertTrue(artifact["limitations"])
                self.assertIn("benchmark", artifact)
                self.assertEqual(artifact["review_status"], "PENDING_REVIEW")
                for flag, expected in expected_flags.items():
                    self.assertEqual(artifact[flag], expected)
                    self.assertEqual(emission[flag], expected)
                for flag in ("may_write_db", "may_write_qdrant", "may_write_memory", "may_write_financial_truth"):
                    self.assertIs(artifact["storage_policy"][flag], False)
                for flag in (
                    "paper_live_execution_artifact",
                    "broker_exchange_credentials_present",
                    "hidden_order_execution_fields_present",
                    "token_issued_by_this_artifact",
                ):
                    self.assertIs(artifact["security_policy"][flag], False)

    def test_helper_boundary_stays_pre_envelope_only(self) -> None:
        helper = self.policy_vector["helper_candidate"]
        self.assertEqual(helper["schema_version"], HELPER_SCHEMA_VERSION)
        self.assertEqual(helper["status"], "pending_review_pre_envelope_only")
        self.assertFalse(helper["may_replace_authoritative_schema"])

        self.assertEqual(self.mapping_vector["helper_schema_version"], HELPER_SCHEMA_VERSION)
        self.assertEqual(self.mapping_vector["authoritative_schema_version"], SCHEMA_VERSION)
        self.assertFalse(self.mapping_vector["helper_can_replace_authoritative_envelope"])

        for case in self.mapping_vector["pre_envelope_only_cases"]:
            with self.subTest(case_id=case["case_id"]):
                self.assertEqual(case["expected_status"], "quarantine_pre_envelope_only")
                self.assertIn("payload", case["missing_fields"])
                self.assertIn("storage_policy", case["missing_fields"])
                self.assertIn("security_policy", case["missing_fields"])

    def test_quarantine_coverage(self) -> None:
        phase3b_case_ids = {case["case_id"] for case in self.quarantine_vector["cases"]}
        required_phase3b_cases = {
            "malformed_output",
            "missing_raw_payload_ref",
            "missing_assumptions_or_limitations",
            "missing_benchmark_without_data_missing",
            "broker_or_exchange_credential_fields",
            "paper_live_or_order_fields",
            "unexpected_artifact_type",
            "sidecar_unavailable",
            "timeout",
        }
        self.assertTrue(required_phase3b_cases.issubset(phase3b_case_ids))

        invalid_expectations = {
            "invalid_missing_raw_payload_ref_transport_response_v1": "QUARANTINED",
            "invalid_sidecar_unavailable_transport_response_v1": "SIDE_CAR_UNAVAILABLE_SIMULATED",
            "invalid_timeout_transport_response_v1": "TIMEOUT_SIMULATED",
            "invalid_policy_denied_transport_response_v1": "POLICY_DENIED",
            "invalid_trading_scope_transport_response_v1": "POLICY_DENIED",
            "invalid_order_field_transport_response_v1": "POLICY_DENIED",
            "invalid_store_write_transport_response_v1": "POLICY_DENIED",
        }
        for name, expected_state in invalid_expectations.items():
            fixture = load_json(f"docs/strategy_lab/mock_transport_fixtures/{name}.json")
            with self.subTest(name=name):
                self.assertEqual(fixture["transport_response"]["lifecycle_state"], expected_state)
                self.assertFalse(fixture["transport_response"]["artifact_emission_decision"]["artifact_emitted"])

        unrecognized = StrategyLabTransportRequest("create_live_order", self._base_request("create_live_order"))
        self.assertEqual(self.transport.policy.evaluate(unrecognized).decision, "deny")

    def test_data_missing_coverage(self) -> None:
        required_conditions = {
            "benchmark_unavailable",
            "data_source_incomplete",
            "equity_curve_or_trade_fields_missing",
            "regime_or_tuning_shape_not_proven",
            "sidecar_capability_cannot_be_confirmed",
            "helper_output_cannot_prove_full_artifact_field",
        }
        actual_conditions = {case["condition"] for case in self.quarantine_vector["data_missing_propagation_cases"]}
        self.assertTrue(required_conditions.issubset(actual_conditions))

        policy = StrategyLabTransportPolicy()
        held_artifact_types = {
            "parameter_sweep",
            "risk_report",
            "factor_test",
            "portfolio_experiment",
        }
        self.assertEqual(set(self.policy_vector["default_hold_or_data_missing_artifact_types"]), held_artifact_types)
        for operation in ("parameter_sweep", "structured_tune"):
            decision = policy.evaluate(StrategyLabTransportRequest(operation, self._base_request(operation)))
            self.assertEqual(decision.decision, "default_hold")

        unavailable = load_json("docs/strategy_lab/mock_transport_fixtures/invalid_sidecar_unavailable_transport_response_v1.json")
        self.assertIn(
            "sidecar_capability_cannot_be_confirmed",
            unavailable["transport_response"]["quarantine_decision"]["data_missing"],
        )

    def test_no_side_effect_fixture_or_vector_authorization(self) -> None:
        prohibited_true_keys = {
            "production_data_access",
            "execution_allowed",
            "may_write_db",
            "may_write_qdrant",
            "may_write_memory",
            "may_write_financial_truth",
            "live_trading_enabled",
            "network_transport_started",
            "service_started",
            "token_issued",
            "dependency_installed",
            "store_write_authorized",
            "paper_live_execution_authorized",
            "paper_live_execution_artifact",
            "broker_exchange_credentials_present",
            "hidden_order_execution_fields_present",
            "token_issued_by_this_artifact",
            "artifact_store_implemented",
            "runtime_validator_implemented",
            "source_registry_write_authorized",
            "parser_gold_label_write_authorized",
            "holdings_mutation_authorized",
            "watchlist_mutation_authorized",
            "thesis_mutation_authorized",
        }
        json_paths = rel_json_paths("docs/strategy_lab/**/*.json")
        self.assertGreaterEqual(len(json_paths), 1)

        for path in json_paths:
            loaded = load_json(path)
            for key, value in walk_json(loaded):
                if key in prohibited_true_keys and isinstance(value, bool):
                    with self.subTest(path=path, key=key):
                        if value is True and self._is_rejected_or_invalid_example(path, loaded):
                            continue
                        self.assertIs(value, False)

        for fixture_path in rel_json_paths("docs/strategy_lab/mock_transport_fixtures/*.json"):
            fixture = load_json(fixture_path)
            audit = fixture["transport_response"]["audit_record"]
            with self.subTest(fixture_path=fixture_path):
                self.assertFalse(audit["network_transport_started"])
                self.assertFalse(audit["service_started"])
                self.assertFalse(audit["token_issued"])
                self.assertFalse(audit["dependency_installed"])
                self.assertFalse(audit["store_write_authorized"])
                self.assertFalse(audit["paper_live_execution_authorized"])

    def _base_request(self, operation: str) -> dict[str, Any]:
        return {
            "request_id": f"inline_{operation}",
            "job_id": PHASE3C_JOB_ID,
            "operation": operation,
            "mock_scope": "phase3c_offline_mock_transport_only",
            "production_data_access": False,
            "execution_allowed": False,
            "paper_live_scope": "none",
            "input": {},
        }

    def _is_rejected_or_invalid_example(self, path: str, loaded: Any) -> bool:
        if Path(path).name.startswith("invalid_"):
            return True
        if not isinstance(loaded, dict):
            return False
        if loaded.get("status") in {"policy_denied", "quarantined"}:
            return True
        policy_decision = loaded.get("policy_decision")
        if isinstance(policy_decision, dict) and policy_decision.get("decision") == "deny":
            return True
        payload = loaded.get("payload")
        if isinstance(payload, dict) and "invalid_reason" in payload:
            return True
        quarantine = loaded.get("quarantine")
        if isinstance(quarantine, dict) and quarantine.get("quarantined") is True:
            return True
        return False


if __name__ == "__main__":
    unittest.main()
