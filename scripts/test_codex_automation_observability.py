#!/usr/bin/env python3
"""Focused tests for daily-closeout observability primitives."""

from __future__ import annotations

import json
import os
import stat
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import codex_automation_observability as obs


class CodexAutomationObservabilityTest(unittest.TestCase):
    def test_private_directories_atomic_lifecycle_and_finalized_immutability(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            paths = obs.ObservabilityPaths(Path(temp_dir))
            obs.ensure_private_dirs(paths)

            for directory in paths.private_directories:
                self.assertEqual(0o700, stat.S_IMODE(directory.stat().st_mode))

            record = obs.initial_run_record(
                run_id="20260711T203000+1000-a1b2c3d4-daily-closeout",
                job="daily-closeout",
                started_at="2026-07-11T10:30:00Z",
            )
            path = obs.write_initial_run(paths, record)
            self.assertEqual(0o600, stat.S_IMODE(path.stat().st_mode))
            self.assertEqual("RUNNING", json.loads(path.read_text())["lifecycle_status"])

            obs.update_running_record(paths, record["run_id"], {"model_gate": {"model_required": False}})
            final = obs.finalize_run(
                paths,
                record["run_id"],
                {
                    "lifecycle_status": "SUCCEEDED",
                    "execution_status": "SUCCEEDED",
                    "evidence_status": "COMPLETE",
                    "usefulness": "CONFIRMING",
                    "functionality_result": "WORKING",
                    "ended_at": "2026-07-11T10:31:00Z",
                },
            )
            self.assertEqual("SUCCEEDED", final["lifecycle_status"])
            with self.assertRaisesRegex(RuntimeError, "finalized"):
                obs.update_running_record(paths, record["run_id"], {"usefulness": "NOISE"})

    def test_atomic_writer_refuses_symlink_target(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            paths = obs.ObservabilityPaths(root)
            obs.ensure_private_dirs(paths)
            target = root / "real.json"
            target.write_text("{}", encoding="utf-8")
            link = paths.runs / "link.json"
            link.symlink_to(target)

            with self.assertRaisesRegex(RuntimeError, "symlink"):
                obs.atomic_write_json(link, {"record_type": "run"})

    def test_parse_usage_ignores_non_json_and_derives_uncached_input(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            log = Path(temp_dir) / "run.jsonl"
            log.write_text(
                "transport warning\n"
                '{"type":"turn.started"}\n'
                '{"type":"turn.completed","usage":{"input_tokens":1000,'
                '"cached_input_tokens":750,"output_tokens":120,'
                '"reasoning_output_tokens":40}}\n',
                encoding="utf-8",
            )

            self.assertEqual(
                {
                    "input_tokens": 1000,
                    "cached_input_tokens": 750,
                    "uncached_input_tokens": 250,
                    "output_tokens": 120,
                    "reasoning_output_tokens": 40,
                },
                obs.parse_usage(log),
            )

    def test_probe_output_is_redacted_and_capped(self) -> None:
        secret = "ghp_" + "a" * 48
        spec = obs.ProbeSpec(
            "test.secret",
            (sys.executable, "-c", f"print('{secret}'); print('x' * 20000)"),
            True,
        )
        result = obs.run_probe(spec, output_limit=512)

        self.assertEqual(0, result["returncode"])
        self.assertNotIn(secret, result["output"])
        self.assertIn("[REDACTED]", result["output"])
        self.assertTrue(result["output_truncated"])
        self.assertGreater(result["original_output_bytes"], 512)

    def test_evidence_pack_is_bounded(self) -> None:
        probes = [
            {
                "id": f"probe.{index}",
                "required": True,
                "returncode": 0,
                "status": "AVAILABLE",
                "output": "x" * obs.PER_PROBE_OUTPUT_LIMIT,
                "original_output_bytes": obs.PER_PROBE_OUTPUT_LIMIT,
                "output_truncated": False,
            }
            for index in range(8)
        ]
        evidence = obs.build_evidence_record(
            run_id="run-1",
            observed_at="2026-07-11T10:30:00Z",
            probes=probes,
            facts={"git.primary.head": "abc"},
            previous_facts=None,
        )

        encoded = json.dumps(evidence, sort_keys=True).encode("utf-8")
        self.assertLessEqual(len(encoded), obs.EVIDENCE_PACK_LIMIT)
        self.assertTrue(any(probe["output_truncated"] for probe in evidence["probes"]))

    def test_fact_comparison_materiality_model_gate_and_usefulness(self) -> None:
        previous = {
            "git.primary.head": "abc",
            "git.primary.dirty": False,
            "automation.failed_units": [],
        }
        current = {
            "git.primary.head": "def",
            "git.primary.dirty": False,
            "automation.failed_units": [],
        }
        comparison = obs.compare_facts(current, previous)
        self.assertEqual(["git.primary.head"], comparison["material_changed_fact_ids"])
        gate = obs.decide_model_gate(comparison, evidence_status="COMPLETE")
        self.assertFalse(gate["model_required"])
        self.assertEqual(["SINGLE_DETERMINISTIC_TRANSITION"], gate["reason_codes"])
        rating, reason = obs.score_usefulness(comparison, "COMPLETE", has_next_action=True)
        self.assertEqual("ACTIONABLE", rating)
        self.assertEqual("material_change_with_action", reason)

        no_change = obs.compare_facts(current, current)
        gate = obs.decide_model_gate(no_change, evidence_status="COMPLETE")
        self.assertFalse(gate["model_required"])
        self.assertEqual(["NATIVE_NO_CHANGE"], gate["reason_codes"])
        self.assertEqual(("CONFIRMING", "fresh_complete_confirmation"), obs.score_usefulness(no_change, "COMPLETE"))

        bootstrap = obs.compare_facts(current, None)
        gate = obs.decide_model_gate(bootstrap, evidence_status="COMPLETE")
        self.assertTrue(gate["model_required"])
        self.assertIn("BOOTSTRAP_SYNTHESIS", gate["reason_codes"])
        self.assertEqual(
            ("ACTIONABLE", "bootstrap_current_blocker"),
            obs.score_usefulness(bootstrap, "COMPLETE", has_next_action=True),
        )

        ambiguous = {
            "comparison_state": "COMPARABLE",
            "material_changed_fact_ids": ["queue.owner_decisions"],
            "facts": {"queue.owner_decisions": ["one", "two"]},
        }
        gate = obs.decide_model_gate(ambiguous, evidence_status="COMPLETE")
        self.assertTrue(gate["model_required"])
        self.assertEqual(["OWNER_PRIORITY_AMBIGUOUS"], gate["reason_codes"])

    def test_tool_activity_counts_targeted_reads_and_caps_command_details(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            log = Path(temp_dir) / "run.jsonl"
            events = [
                {
                    "type": "item.started",
                    "item": {"type": "command_execution", "command": f"sed -n '1,20p' report-{index}.md"},
                }
                for index in range(6)
            ]
            log.write_text("\n".join(json.dumps(event) for event in events) + "\n", encoding="utf-8")

            activity = obs.parse_tool_activity(log)
            self.assertEqual(6, activity["targeted_read_count"])
            self.assertFalse(activity["within_allowance"])
            self.assertEqual(4, len(activity["commands"]))
            self.assertEqual(2, activity["additional_command_count"])

    def test_required_probe_failure_degrades_evidence(self) -> None:
        evidence = obs.build_evidence_record(
            run_id="run-1",
            observed_at="2026-07-11T10:30:00Z",
            probes=[
                {
                    "id": "systemd.timers",
                    "required": True,
                    "returncode": 1,
                    "status": "UNAVAILABLE",
                    "output": "bus unavailable",
                    "original_output_bytes": 15,
                    "output_truncated": False,
                },
                {
                    "id": "github.read",
                    "required": False,
                    "returncode": 1,
                    "status": "UNAVAILABLE",
                    "output": "auth unavailable",
                    "original_output_bytes": 16,
                    "output_truncated": False,
                },
            ],
            facts={},
            previous_facts={},
        )

        self.assertEqual("DEGRADED", evidence["evidence_status"])
        self.assertEqual(0.0, evidence["required_probe_coverage"])

    def test_model_output_rejects_unknown_facts_and_unsafe_next_action(self) -> None:
        payload = {
            "summary": "summary",
            "findings": [
                {
                    "fact_ids": ["unknown.fact"],
                    "classification": "Confirmed",
                    "severity": "P1",
                    "statement": "statement",
                    "owner_action": "action",
                }
            ],
            "data_missing": [],
            "next_action": {
                "action": "git reset --hard",
                "next_prompt": "do it",
                "requires_approval": True,
            },
        }
        with self.assertRaisesRegex(ValueError, "unknown fact"):
            obs.validate_model_output(payload, {"git.primary.head"})

        payload["findings"][0]["fact_ids"] = ["git.primary.head"]
        with self.assertRaisesRegex(ValueError, "unsafe"):
            obs.validate_model_output(payload, {"git.primary.head"})

    def test_model_output_fails_closed_on_schema_drift(self) -> None:
        payload = {
            "summary": "summary",
            "findings": [
                {
                    "fact_ids": ["git.primary.head"],
                    "classification": "Confirmed",
                    "severity": "INFO",
                    "statement": "statement",
                    "owner_action": "none",
                }
            ],
            "data_missing": [],
            "next_action": {
                "action": "none",
                "next_prompt": "next scheduled closeout",
                "requires_approval": False,
            },
        }
        obs.validate_model_output(payload, {"git.primary.head"})

        payload["unexpected"] = True
        with self.assertRaisesRegex(ValueError, "keys"):
            obs.validate_model_output(payload, {"git.primary.head"})
        payload.pop("unexpected")

        payload["findings"][0]["severity"] = "warning"
        with self.assertRaisesRegex(ValueError, "severity"):
            obs.validate_model_output(payload, {"git.primary.head"})

    def test_oversized_model_output_is_preserved_and_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "model-output.json"
            payload = b" " * (obs.MODEL_OUTPUT_SIZE_LIMIT + 1)
            path.write_bytes(payload)

            with self.assertRaisesRegex(ValueError, "32 KiB"):
                obs.load_model_output(path)
            self.assertEqual(payload, path.read_bytes())

    def test_abandoned_recovery_and_job_lock(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            paths = obs.ObservabilityPaths(Path(temp_dir))
            obs.ensure_private_dirs(paths)
            record = obs.initial_run_record(
                run_id="old-daily-closeout",
                job="daily-closeout",
                started_at="2026-07-11T09:00:00Z",
            )
            obs.write_initial_run(paths, record)

            recovered = obs.recover_abandoned_runs(
                paths,
                now=datetime(2026, 7, 11, 10, 0, tzinfo=timezone.utc),
                timeout=timedelta(minutes=35),
                detected_by="new-run",
            )
            self.assertEqual(["old-daily-closeout"], recovered)
            recovered_record = json.loads((paths.runs / "old-daily-closeout.json").read_text())
            self.assertEqual("ABANDONED", recovered_record["lifecycle_status"])

            with obs.JobLock(paths, "daily-closeout") as first:
                self.assertTrue(first.acquired)
                with obs.JobLock(paths, "daily-closeout") as second:
                    self.assertFalse(second.acquired)

    def test_reviews_are_immutable_and_aggregation_applies_latest(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            paths = obs.ObservabilityPaths(Path(temp_dir))
            obs.ensure_private_dirs(paths)
            record = obs.initial_run_record("run-1", "daily-closeout", "2026-07-11T10:00:00Z")
            obs.write_initial_run(paths, record)
            obs.finalize_run(
                paths,
                "run-1",
                {
                    "lifecycle_status": "SUCCEEDED",
                    "execution_status": "SUCCEEDED",
                    "evidence_status": "COMPLETE",
                    "usefulness": "CONFIRMING",
                    "functionality_result": "WORKING",
                    "ended_at": "2026-07-11T10:01:00Z",
                    "required_probe_coverage": 1.0,
                    "usage": {"input_tokens": 100, "uncached_input_tokens": 25, "output_tokens": 10},
                    "model": {"name": "gpt-5.4-mini"},
                },
            )
            review = obs.create_review(
                paths,
                run_id="run-1",
                rating="NOISE",
                reason="Repeated a known blocker without new evidence",
                reviewer="Orlando",
                reviewed_at="2026-07-11T10:02:00Z",
            )
            self.assertTrue(review.exists())
            with self.assertRaises(FileExistsError):
                obs.atomic_write_json(review, {"changed": True}, immutable=True)

            summary = obs.summarize_runs(paths, job="daily-closeout", limit=7)
            self.assertEqual(1, summary["completed_runs"])
            self.assertEqual(0, summary["useful_runs"])
            self.assertEqual(1, summary["noise_runs"])
            self.assertEqual(1, summary["model_assisted_runs"])


if __name__ == "__main__":
    unittest.main()
