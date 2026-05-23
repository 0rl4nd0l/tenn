import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCHEMA_VERSION = "strategy_lab_artifact_v1"
HELPER_SCHEMA_VERSION = "strategy_lab_sidecar_artifact_v1"


def load_json(relative_path):
    with (ROOT / relative_path).open(encoding="utf-8") as handle:
        return json.load(handle)


def rel_json_paths(pattern):
    return sorted(path.relative_to(ROOT).as_posix() for path in ROOT.glob(pattern))


def walk_json(value):
    if isinstance(value, dict):
        for key, item in value.items():
            yield key, item
            yield from walk_json(item)
    elif isinstance(value, list):
        for item in value:
            yield from walk_json(item)


class StrategyLabPhase3BReconciledMockTests(unittest.TestCase):
    def setUp(self):
        self.schema = load_json("docs/strategy_lab/artifact_schema_v1.schema.json")
        self.policy = load_json("docs/strategy_lab/mock_test_vectors/reconciled_schema_policy_v1.json")
        self.mapping = load_json("docs/strategy_lab/mock_test_vectors/helper_to_artifact_mapping_cases_v1.json")
        self.quarantine = load_json("docs/strategy_lab/mock_test_vectors/quarantine_cases_v1.json")
        self.blocked = load_json("docs/strategy_lab/mock_test_vectors/blocked_surfaces_v1.json")
        self.invariants = load_json("docs/strategy_lab/mock_test_vectors/artifact_invariant_cases_v1.json")

    def test_json_parse_coverage(self):
        paths = ["docs/strategy_lab/artifact_schema_v1.schema.json"]
        paths.extend(rel_json_paths("docs/strategy_lab/artifact_fixtures/*.json"))
        paths.extend(rel_json_paths("docs/strategy_lab/mock_payloads/*.json"))
        paths.extend(rel_json_paths("docs/strategy_lab/mock_test_vectors/*.json"))

        self.assertGreaterEqual(len(paths), 1)
        for path in paths:
            with self.subTest(path=path):
                loaded = load_json(path)
                self.assertIsInstance(loaded, (dict, list))

    def test_authoritative_schema_baseline_remains_phase2_artifact_v1(self):
        authoritative = self.policy["authoritative_schema"]

        self.assertEqual(authoritative["schema_version"], SCHEMA_VERSION)
        self.assertEqual(self.schema["properties"]["schema_version"]["const"], SCHEMA_VERSION)
        self.assertTrue((ROOT / authoritative["schema_doc"]).is_file())
        self.assertTrue((ROOT / authoritative["schema_json"]).is_file())
        self.assertTrue((ROOT / authoritative["fixture_dir"]).is_dir())

        required = set(self.schema["required"])
        invariant_required = set(self.invariants["required_fields"])
        self.assertEqual(required, invariant_required)

        for fixture_ref in self.invariants["authoritative_baseline"]["valid_fixture_refs"]:
            with self.subTest(fixture_ref=fixture_ref):
                artifact = load_json(fixture_ref)
                self.assertEqual(artifact["schema_version"], SCHEMA_VERSION)
                self.assertTrue(required.issubset(artifact))

    def test_helper_candidate_is_pre_envelope_only(self):
        helper = self.policy["helper_candidate"]

        self.assertEqual(helper["schema_version"], HELPER_SCHEMA_VERSION)
        self.assertEqual(helper["status"], "pending_review_pre_envelope_only")
        self.assertFalse(helper["may_replace_authoritative_schema"])
        self.assertIn("map_to_full_strategy_lab_artifact_v1_envelope", helper["allowed_outcomes"])
        self.assertIn("quarantine_as_pre_envelope_only", helper["allowed_outcomes"])

        self.assertEqual(self.mapping["helper_schema_version"], HELPER_SCHEMA_VERSION)
        self.assertEqual(self.mapping["authoritative_schema_version"], SCHEMA_VERSION)
        self.assertFalse(self.mapping["helper_can_replace_authoritative_envelope"])

        pre_envelope_cases = self.mapping["pre_envelope_only_cases"]
        self.assertGreaterEqual(len(pre_envelope_cases), 1)
        for case in pre_envelope_cases:
            self.assertEqual(case["source_helper_schema_version"], HELPER_SCHEMA_VERSION)
            self.assertEqual(case["expected_status"], "quarantine_pre_envelope_only")
            self.assertIn("payload", case["missing_fields"])
            self.assertIn("storage_policy", case["missing_fields"])
            self.assertIn("security_policy", case["missing_fields"])

    def test_helper_to_authoritative_mapping_contains_full_required_fields(self):
        required_target_fields = set(self.mapping["required_target_fields"])
        self.assertTrue(set(self.schema["required"]).issubset(required_target_fields))

        for case in self.mapping["mappings"]:
            with self.subTest(case_id=case["case_id"]):
                self.assertEqual(case["source_helper_schema_version"], HELPER_SCHEMA_VERSION)
                self.assertEqual(case["target_schema_version"], SCHEMA_VERSION)
                self.assertEqual(case["mapping_decision"], "map_to_full_authoritative_envelope")
                self.assertTrue(case["evidence_backed"])
                self.assertIn(case["target_artifact_type"], self.mapping["evidence_backed_types"])

                mapped = load_json(case["mapped_artifact_ref"])
                self.assertEqual(mapped["schema_version"], SCHEMA_VERSION)
                self.assertEqual(mapped["artifact_type"], case["target_artifact_type"])
                self.assertTrue(required_target_fields.issubset(mapped))
                self.assertNotIn("observations", mapped)

                for missing_field in case["required_data_missing"]:
                    self.assertIn(missing_field, mapped["data_missing"])

                self.assertIn("payload", case["source_helper_missing_authoritative_fields"])
                self.assertIn("raw_payload_ref", case["source_helper_missing_authoritative_fields"])
                self.assertIn("normalized_result", case["source_helper_missing_authoritative_fields"])
                self.assertIn("storage_policy", case["source_helper_missing_authoritative_fields"])
                self.assertIn("security_policy", case["source_helper_missing_authoritative_fields"])

    def test_required_strategy_lab_artifact_flags_are_preserved(self):
        expected_flags = self.invariants["required_flags"]
        fixture_refs = list(self.invariants["authoritative_baseline"]["valid_fixture_refs"])
        fixture_refs.extend(case["mapped_artifact_ref"] for case in self.mapping["mappings"])

        for fixture_ref in sorted(set(fixture_refs)):
            artifact = load_json(fixture_ref)
            with self.subTest(fixture_ref=fixture_ref):
                for flag, expected in expected_flags.items():
                    self.assertEqual(artifact[flag], expected)
                for flag in self.invariants["storage_policy_required_false_flags"]:
                    self.assertIs(artifact["storage_policy"][flag], False)
                for flag in self.invariants["security_policy_required_false_flags"]:
                    self.assertIs(artifact["security_policy"][flag], False)

        for payload_ref in rel_json_paths("docs/strategy_lab/mock_payloads/*.json"):
            payload = load_json(payload_ref)
            mapping = payload.get("artifact_mapping")
            if not mapping or not mapping.get("artifact_emitted"):
                continue
            flags = mapping.get("required_flags", {})
            with self.subTest(payload_ref=payload_ref):
                for flag, expected in expected_flags.items():
                    self.assertEqual(flags[flag], expected)

    def test_evidence_backed_type_limits_are_enforced(self):
        expected_backed = {"backtest_run", "regime_breakdown"}
        expected_hold = {"parameter_sweep", "risk_report", "factor_test", "portfolio_experiment"}

        self.assertEqual(set(self.policy["evidence_backed_artifact_types"]), expected_backed)
        self.assertEqual(set(self.mapping["evidence_backed_types"]), expected_backed)
        self.assertEqual(set(self.policy["default_hold_or_data_missing_artifact_types"]), expected_hold)
        self.assertEqual(set(self.mapping["held_or_data_missing_types"]), expected_hold)

        mapped_types = {case["target_artifact_type"] for case in self.mapping["mappings"]}
        self.assertEqual(mapped_types, expected_backed)
        self.assertTrue(mapped_types.isdisjoint(expected_hold))

    def test_forbidden_evidence_labels_are_rejected_or_flagged(self):
        forbidden = set(self.invariants["forbidden_labels"])
        self.assertEqual(forbidden, set(self.policy["forbidden_evidence_labels"]))

        for fixture_ref in self.invariants["authoritative_baseline"]["valid_fixture_refs"]:
            artifact = load_json(fixture_ref)
            with self.subTest(fixture_ref=fixture_ref):
                self.assertNotIn(artifact["evidence_label"], forbidden)
                self.assertTrue(set(artifact["evidence_labels"]).isdisjoint(forbidden))

        invalid_financial_truth = load_json(
            "docs/strategy_lab/artifact_fixtures/invalid_financial_truth_label_v1.json"
        )
        self.assertIn("financial_truth", invalid_financial_truth["evidence_labels"])
        flagged_cases = {case["case_id"] for case in self.quarantine["cases"]}
        self.assertIn("schema_validation_failure", flagged_cases)

    def test_tool_allowlist_entries_declare_required_policy_fields(self):
        expected_operations = {
            "list_capabilities",
            "read_market_snapshot",
            "submit_backtest",
            "get_backtest_result",
            "get_job",
            "regime_detect",
            "parameter_sweep",
            "structured_tune",
            "export_artifact"
        }
        required_entry_fields = {
            "operation",
            "decision",
            "required_mock_scope",
            "input_fields",
            "output_shape",
            "artifact_type_emitted",
            "raw_payload_ref_rule",
            "quarantine_rule",
            "data_missing_behavior",
            "audit_log_fields",
            "rate_limit_expectation",
            "human_review_required"
        }

        operations = {entry["operation"]: entry for entry in self.policy["operations"]}
        self.assertEqual(set(operations), expected_operations)

        for operation, entry in operations.items():
            with self.subTest(operation=operation):
                self.assertTrue(required_entry_fields.issubset(entry))
                self.assertIsInstance(entry["input_fields"], list)
                self.assertIsInstance(entry["audit_log_fields"], list)
                self.assertTrue(entry["input_fields"])
                self.assertTrue(entry["audit_log_fields"])
                self.assertTrue(entry["human_review_required"])

        self.assertEqual(operations["parameter_sweep"]["decision"], "default_hold")
        self.assertEqual(operations["structured_tune"]["decision"], "default_hold")
        self.assertEqual(operations["get_backtest_result"]["artifact_type_emitted"], "backtest_run")
        self.assertEqual(operations["regime_detect"]["artifact_type_emitted"], "regime_breakdown")
        self.assertEqual(
            operations["export_artifact"]["decision"],
            "conditional_tenn_owned_local_mock_conversion_only"
        )

    def test_blocked_surfaces_are_default_denied(self):
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
            "source-registry writes"
        }

        surfaces = {entry["surface"]: entry for entry in self.blocked["blocked_surfaces"]}
        self.assertEqual(set(surfaces), expected_surfaces)
        for surface, entry in surfaces.items():
            with self.subTest(surface=surface):
                self.assertEqual(entry["decision"], "deny")
                self.assertTrue(entry["reason"])

    def test_quarantine_and_data_missing_cases_cover_required_failures(self):
        expected_case_ids = {
            "helper_missing_full_envelope_fields_promoted",
            "sidecar_unavailable",
            "timeout",
            "malformed_output",
            "schema_validation_failure",
            "policy_denial",
            "forbidden_scope_requested",
            "missing_benchmark_without_data_missing",
            "missing_data_source",
            "missing_assumptions_or_limitations",
            "missing_raw_payload_ref",
            "broker_or_exchange_credential_fields",
            "paper_live_or_order_fields",
            "unexpected_artifact_type",
            "suspected_live_or_paper_execution_surface"
        }
        cases = {case["case_id"]: case for case in self.quarantine["cases"]}
        self.assertEqual(set(cases), expected_case_ids)

        expected_data_missing = {
            "benchmark_unavailable",
            "data_source_incomplete",
            "equity_curve_or_trade_fields_missing",
            "regime_or_tuning_shape_not_proven",
            "raw_payload_unavailable",
            "sidecar_capability_cannot_be_confirmed",
            "helper_output_cannot_prove_full_artifact_field"
        }
        actual_data_missing = {
            case["condition"] for case in self.quarantine["data_missing_propagation_cases"]
        }
        self.assertEqual(actual_data_missing, expected_data_missing)

    def test_no_store_write_contract_authorizes_no_store_mutation(self):
        policy_targets = {entry["target"]: entry for entry in self.policy["no_store_write_contract"]}
        blocked_targets = {entry["target"]: entry for entry in self.blocked["no_store_write_cases"]}
        expected_targets = {
            "db",
            "qdrant",
            "news_store",
            "memory",
            "financial_truth",
            "parser_gold_labels",
            "source_registry",
            "holdings_state",
            "watchlist_state",
            "thesis_state"
        }

        self.assertEqual(set(policy_targets), expected_targets)
        self.assertEqual(set(blocked_targets), expected_targets)

        for target in expected_targets:
            with self.subTest(target=target):
                self.assertIs(policy_targets[target]["allow_write"], False)
                self.assertIs(blocked_targets[target]["may_write"], False)

        for vector_ref in rel_json_paths("docs/strategy_lab/mock_test_vectors/*.json"):
            vector = load_json(vector_ref)
            for key, value in walk_json(vector):
                if key in {"allow_write", "may_write", "store_write"} and isinstance(value, bool):
                    with self.subTest(vector_ref=vector_ref, key=key):
                        self.assertIs(value, False)

    def test_static_import_hygiene_for_phase3b_tests_and_vectors(self):
        test_text = (ROOT / "tests/strategy_lab/test_strategy_lab_mocked_adapter_phase3b_reconciled.py").read_text(
            encoding="utf-8"
        )
        forbidden_import = re.compile(
            r"^\s*(?:from|import)\s+"
            r"(?:requests|httpx|aiohttp|socket|subprocess|docker|mcp|quantdinger|"
            r"financial_engine_v2|backend|app)\b",
            re.MULTILINE,
        )
        self.assertIsNone(forbidden_import.search(test_text))
        helper_import = re.compile(r"^\s*(?:from|import)\s+.*strategy_lab_artifact_schema", re.MULTILINE)
        self.assertIsNone(helper_import.search(test_text))

        for entry in self.policy["forbidden_import_authority"]:
            with self.subTest(surface=entry["surface"]):
                self.assertIs(entry["authorized"], False)

        for vector_ref in rel_json_paths("docs/strategy_lab/mock_test_vectors/*.json"):
            vector = load_json(vector_ref)
            for key, value in walk_json(vector):
                if key == "authorized" and isinstance(value, bool):
                    with self.subTest(vector_ref=vector_ref):
                        self.assertIs(value, False)


if __name__ == "__main__":
    unittest.main()
