import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

PACKET_DIR = ROOT / "reports/agent_jobs/strategy_lab_readonly_subsystem_maturation_v1_20260525/packets"
DOC_PATHS = [
    ROOT / "docs/strategy_lab/README.md",
    ROOT / "docs/strategy_lab/review_queue_contract_v1.md",
    ROOT / "docs/strategy_lab/experiment_session_envelope_v1.md",
    ROOT / "docs/strategy_lab/readonly_subsystem_boundaries_v1.md",
    ROOT / "docs/strategy_lab/review_packets_v1.md",
]
JSON_PATHS = [
    ROOT / "docs/strategy_lab/review_queue_v1.schema.json",
    ROOT / "docs/strategy_lab/experiment_session_envelope_v1.schema.json",
    PACKET_DIR / "experiment_review_packet.json",
    PACKET_DIR / "repeatability_summary_packet.json",
    PACKET_DIR / "risk_summary_packet.json",
    PACKET_DIR / "artifact_provenance_packet.json",
    PACKET_DIR / "cleanup_revoke_audit_packet.json",
]


class StrategyLabReadonlySubsystemMaturationTests(unittest.TestCase):
    def test_json_docs_and_packets_parse(self):
        for path in JSON_PATHS:
            with self.subTest(path=path.relative_to(ROOT).as_posix()):
                self.assertTrue(path.is_file())
                with path.open(encoding="utf-8") as handle:
                    loaded = json.load(handle)
                self.assertIsInstance(loaded, dict)

    def test_review_packets_preserve_non_promoting_boundaries(self):
        required_false = [
            "current_sidecar_available",
            "execution_allowed",
            "canonical_financial_truth",
            "real_transport",
        ]

        for path in sorted(PACKET_DIR.glob("*.json")):
            with self.subTest(path=path.relative_to(ROOT).as_posix()):
                with path.open(encoding="utf-8") as handle:
                    packet = json.load(handle)
                self.assertEqual(packet["source_mode"], "repo_artifacts_only")
                self.assertEqual(packet["review_status"], "PENDING_REVIEW")
                for field in required_false:
                    self.assertIs(packet[field], False)
                self.assertTrue(packet["data_missing"])

    def test_schema_contracts_require_readonly_invariants(self):
        review_queue_schema = self.load_json("docs/strategy_lab/review_queue_v1.schema.json")
        experiment_session_schema = self.load_json("docs/strategy_lab/experiment_session_envelope_v1.schema.json")

        for schema in (review_queue_schema, experiment_session_schema):
            with self.subTest(schema=schema["title"]):
                properties = schema["properties"]
                self.assertEqual(properties["review_status"]["const"], "PENDING_REVIEW")
                self.assertIs(properties["current_sidecar_available"]["const"], False)
                self.assertIs(properties["execution_allowed"]["const"], False)
                self.assertIs(properties["canonical_financial_truth"]["const"], False)
                self.assertIs(properties["real_transport"]["const"], False)

    def test_new_docs_and_packets_do_not_contain_forbidden_promotion_values(self):
        forbidden_fragments = [
            '"current_sidecar_available": ' + "true",
            '"execution_allowed": ' + "true",
            '"canonical_financial_truth": ' + "true",
            '"real_transport": ' + "true",
            "ON" + "LINE",
            "CON" + "NECTED",
            "broker credential value",
            "token secret",
        ]
        paths = [*DOC_PATHS, *JSON_PATHS]

        for path in paths:
            text = path.read_text(encoding="utf-8")
            with self.subTest(path=path.relative_to(ROOT).as_posix()):
                for fragment in forbidden_fragments:
                    self.assertNotIn(fragment, text)

    def test_source_evidence_files_remain_available_for_review_packet_refs(self):
        packet = self.load_json(
            "reports/agent_jobs/strategy_lab_readonly_subsystem_maturation_v1_20260525/packets/experiment_review_packet.json"
        )
        session = packet["session"]
        refs = []
        refs.extend(session["runtime_proof_refs"])
        refs.extend(session["reprobe_refs"])
        refs.extend(session["degraded_state_refs"])
        refs.extend(session["cleanup_proof_refs"])
        refs.extend(session["revoke_proof_refs"])

        self.assertGreaterEqual(len(refs), 10)
        for ref in refs:
            with self.subTest(ref=ref):
                self.assertTrue((ROOT / ref).is_file(), ref)

    def load_json(self, relative_path: str):
        with (ROOT / relative_path).open(encoding="utf-8") as handle:
            return json.load(handle)


if __name__ == "__main__":
    unittest.main()
