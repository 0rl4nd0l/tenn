#!/usr/bin/env python3
"""Focused tests for the Codex automation runner contract."""

from __future__ import annotations

import re
import json
import sys
import tempfile
import unittest
from datetime import datetime
from unittest import mock
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import codex_automation_runner as runner
import codex_automation_observability as observability

REPO_ROOT = Path(__file__).resolve().parents[1]
AUTOMATION_INDEX = REPO_ROOT / "docs/dev/automation_index.md"
SYSTEMD_USER_DIR = REPO_ROOT / "systemd/user"


class CodexAutomationRunnerTest(unittest.TestCase):
    def _runner_command(self, job_name: str, env: dict[str, str] | None = None) -> list[str]:
        with tempfile.TemporaryDirectory() as temp_dir:
            codex_path = Path(temp_dir) / "codex"
            codex_path.write_text("#!/bin/sh\n", encoding="utf-8")
            with (
                mock.patch.object(runner, "CODEX_CANDIDATES", (codex_path,)),
                mock.patch.dict(runner.os.environ, env or {}, clear=True),
            ):
                return runner._command(runner.JOBS[job_name], Path("prompt.md"), "20260710T120000+1000")

    def _automation_index_rows(self) -> dict[str, dict[str, str]]:
        text = AUTOMATION_INDEX.read_text(encoding="utf-8")
        rows: dict[str, dict[str, str]] = {}
        pattern = re.compile(
            r"^\|\s*`tenn-codex-(?P<job>[^`]+)\.timer`\s*"
            r"\|\s*(?P<cadence>[^|]+?)\s*"
            r"\|\s*(?P<title>[^|]+?)\s*"
            r"\|\s*`(?P<output>[^`]+)`\s*\|$",
            re.MULTILINE,
        )
        for match in pattern.finditer(text):
            job_name = match.group("job")
            self.assertNotIn(
                job_name,
                rows,
                f"duplicate automation index timer row for {job_name}",
            )
            rows[job_name] = {
                "cadence": match.group("cadence").strip(),
                "title": match.group("title").strip(),
                "output": match.group("output").strip(),
            }
        return rows

    def test_expected_jobs_are_registered(self) -> None:
        expected_jobs = {
            "automation-health",
            "bug-regression",
            "daily-closeout",
            "doc-drift",
            "extraction-regression",
            "future-opportunities",
            "memory-drift",
            "repo-hygiene",
        }

        self.assertEqual(expected_jobs, set(runner.JOBS))

    def test_model_policies_are_explicit_for_registered_jobs(self) -> None:
        expected_policies = {
            "automation-health": runner.MODEL_POLICY_NATIVE,
            "bug-regression": runner.MODEL_POLICY_DEFAULT,
            "daily-closeout": runner.MODEL_POLICY_SMALL,
            "doc-drift": runner.MODEL_POLICY_SMALL,
            "extraction-regression": runner.MODEL_POLICY_DEFAULT,
            "future-opportunities": runner.MODEL_POLICY_SMALL,
            "memory-drift": runner.MODEL_POLICY_SMALL,
            "repo-hygiene": runner.MODEL_POLICY_SMALL,
        }

        self.assertEqual(expected_policies, {name: job.model_policy for name, job in runner.JOBS.items()})

    def test_small_model_viable_jobs_use_small_model_by_default(self) -> None:
        for job_name in ("daily-closeout", "doc-drift", "future-opportunities", "memory-drift", "repo-hygiene"):
            with self.subTest(job=job_name):
                command = self._runner_command(job_name)
                self.assertIn("--model", command)
                self.assertEqual(runner.DEFAULT_SMALL_MODEL, command[command.index("--model") + 1])
                self.assertIn("-c", command)
                self.assertIn(
                    f'model_reasoning_effort="{runner.DEFAULT_SMALL_REASONING_EFFORT}"',
                    command,
                )

    def test_high_risk_regression_jobs_keep_default_model_by_default(self) -> None:
        for job_name in ("bug-regression", "extraction-regression"):
            with self.subTest(job=job_name):
                command = self._runner_command(job_name)
                self.assertNotIn("--model", command)
                self.assertNotIn("-c", command)

    def test_daily_closeout_command_is_structured_isolated_and_ephemeral(self) -> None:
        command = self._runner_command("daily-closeout")

        self.assertIn("--ephemeral", command)
        self.assertIn("--ignore-user-config", command)
        self.assertIn("--output-schema", command)
        schema_path = Path(command[command.index("--output-schema") + 1])
        self.assertEqual("codex_daily_closeout_output_v1.schema.json", schema_path.name)
        output_path = Path(command[command.index("--output-last-message") + 1])
        self.assertEqual(".json", output_path.suffix)
        self.assertIn("model_outputs", output_path.parts)

        ordinary = self._runner_command("repo-hygiene")
        self.assertNotIn("--ephemeral", ordinary)
        self.assertNotIn("--ignore-user-config", ordinary)
        self.assertNotIn("--output-schema", ordinary)

    def test_per_job_model_override_wins(self) -> None:
        command = self._runner_command(
            "bug-regression",
            {
                "TENN_CODEX_AUTOMATION_BUG_REGRESSION_MODEL": "gpt-5.6-luna",
                "TENN_CODEX_AUTOMATION_BUG_REGRESSION_REASONING_EFFORT": "low",
            },
        )

        self.assertEqual("gpt-5.6-luna", command[command.index("--model") + 1])
        self.assertIn('model_reasoning_effort="low"', command)

    def test_model_override_precedence_and_blank_fallback(self) -> None:
        cases = (
            (
                "per-job beats global and small policy",
                {
                    "TENN_CODEX_AUTOMATION_REPO_HYGIENE_MODEL": "job-model",
                    "TENN_CODEX_AUTOMATION_REPO_HYGIENE_REASONING_EFFORT": "low",
                    "TENN_CODEX_AUTOMATION_MODEL": "global-model",
                    "TENN_CODEX_AUTOMATION_REASONING_EFFORT": "high",
                    "TENN_CODEX_AUTOMATION_SMALL_MODEL": "small-model",
                    "TENN_CODEX_AUTOMATION_SMALL_REASONING_EFFORT": "xhigh",
                },
                "job-model",
                "low",
            ),
            (
                "global beats small policy",
                {
                    "TENN_CODEX_AUTOMATION_MODEL": "global-model",
                    "TENN_CODEX_AUTOMATION_REASONING_EFFORT": "high",
                    "TENN_CODEX_AUTOMATION_SMALL_MODEL": "small-model",
                    "TENN_CODEX_AUTOMATION_SMALL_REASONING_EFFORT": "xhigh",
                },
                "global-model",
                "high",
            ),
            (
                "small policy overrides defaults",
                {
                    "TENN_CODEX_AUTOMATION_SMALL_MODEL": "small-model",
                    "TENN_CODEX_AUTOMATION_SMALL_REASONING_EFFORT": "low",
                },
                "small-model",
                "low",
            ),
            (
                "blank higher-priority values fall through",
                {
                    "TENN_CODEX_AUTOMATION_REPO_HYGIENE_MODEL": "  ",
                    "TENN_CODEX_AUTOMATION_REPO_HYGIENE_REASONING_EFFORT": " ",
                    "TENN_CODEX_AUTOMATION_MODEL": "",
                    "TENN_CODEX_AUTOMATION_REASONING_EFFORT": "  ",
                    "TENN_CODEX_AUTOMATION_SMALL_MODEL": "small-model",
                    "TENN_CODEX_AUTOMATION_SMALL_REASONING_EFFORT": "low",
                },
                "small-model",
                "low",
            ),
        )

        for label, env, expected_model, expected_effort in cases:
            with self.subTest(case=label):
                command = self._runner_command("repo-hygiene", env)
                self.assertEqual(expected_model, command[command.index("--model") + 1])
                self.assertIn(f'model_reasoning_effort="{expected_effort}"', command)

    def test_native_job_ignores_model_overrides(self) -> None:
        with mock.patch.dict(
            runner.os.environ,
            {
                "TENN_CODEX_AUTOMATION_MODEL": "global-model",
                "TENN_CODEX_AUTOMATION_REASONING_EFFORT": "high",
                "TENN_CODEX_AUTOMATION_AUTOMATION_HEALTH_MODEL": "job-model",
                "TENN_CODEX_AUTOMATION_AUTOMATION_HEALTH_REASONING_EFFORT": "low",
            },
            clear=True,
        ):
            selection = runner._model_selection(runner.JOBS["automation-health"])

        self.assertIsNone(selection.model)
        self.assertIsNone(selection.reasoning_effort)
        self.assertEqual(runner.MODEL_POLICY_NATIVE, selection.source)

    def test_invalid_reasoning_effort_names_the_environment_variable(self) -> None:
        with (
            mock.patch.dict(
                runner.os.environ,
                {"TENN_CODEX_AUTOMATION_REASONING_EFFORT": "medum"},
                clear=True,
            ),
            self.assertRaisesRegex(ValueError, "TENN_CODEX_AUTOMATION_REASONING_EFFORT"),
        ):
            runner._model_selection(runner.JOBS["repo-hygiene"])

    def test_automation_index_timer_table_matches_registered_jobs(self) -> None:
        index_rows = self._automation_index_rows()

        self.assertEqual(set(runner.JOBS), set(index_rows))
        for job_name, job in runner.JOBS.items():
            with self.subTest(job=job_name):
                self.assertEqual(job.title, index_rows[job_name]["title"])
                self.assertIn(f"*-{job_name}.md", index_rows[job_name]["output"])

    def test_systemd_templates_match_registered_jobs(self) -> None:
        service_jobs = {
            path.name.removeprefix("tenn-codex-").removesuffix(".service")
            for path in SYSTEMD_USER_DIR.glob("tenn-codex-*.service")
        }
        timer_jobs = {
            path.name.removeprefix("tenn-codex-").removesuffix(".timer")
            for path in SYSTEMD_USER_DIR.glob("tenn-codex-*.timer")
        }

        self.assertEqual(set(runner.JOBS), service_jobs)
        self.assertEqual(set(runner.JOBS), timer_jobs)

        for job_name in runner.JOBS:
            with self.subTest(job=job_name):
                service_text = (SYSTEMD_USER_DIR / f"tenn-codex-{job_name}.service").read_text(
                    encoding="utf-8"
                )
                timer_text = (SYSTEMD_USER_DIR / f"tenn-codex-{job_name}.timer").read_text(
                    encoding="utf-8"
                )
                self.assertRegex(
                    service_text,
                    rf"(?m)^ExecStart=.*scripts/codex_automation_runner\.py {re.escape(job_name)}$",
                )
                self.assertIn(f"Unit=tenn-codex-{job_name}.service", timer_text)

    def test_timer_persistence_policy_matches_automation_index(self) -> None:
        index_text = AUTOMATION_INDEX.read_text(encoding="utf-8")
        self.assertIn("Only the native `automation-health` timer is persistent", index_text)

        for job_name in runner.JOBS:
            with self.subTest(job=job_name):
                timer_text = (SYSTEMD_USER_DIR / f"tenn-codex-{job_name}.timer").read_text(encoding="utf-8")
                expected = "Persistent=true" if job_name == "automation-health" else "Persistent=false"
                self.assertIn(expected, timer_text)

    def test_daily_closeout_prompt_is_audit_only(self) -> None:
        prompt = runner.JOBS["daily-closeout"].prompt_builder()

        required_fragments = (
            "Daily Closeout / Lock-Up Audit",
            "Closeout status:",
            "Open P0/P1 blockers:",
            "Dirty or collision risks:",
            "Automation health:",
            "PR / issue queue:",
            "Next recommended prompt:",
            "Do not:",
            "edit files",
            "create, update, comment on, close, or reopen GitHub issues or PRs",
            "install, enable, start, stop, restart, reload, or edit live systemd units",
            "write DBs, Qdrant, Redis, news stores",
            "run broad extraction, backfill, ingestion, migration, or dependency-install commands",
        )
        for fragment in required_fragments:
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, prompt)

    def test_health_expectations_cover_registered_jobs(self) -> None:
        expected = {expectation.name for expectation in runner.HEALTH_EXPECTATIONS}

        self.assertEqual(set(runner.JOBS), expected)

    def test_list_jobs_returns_success(self) -> None:
        self.assertEqual(0, runner.list_jobs())

    def test_failed_child_process_writes_failure_report(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_root = Path(temp_dir)
            timestamp = "20260629T120000+1000"
            command = [
                sys.executable,
                "-c",
                "import sys; sys.stderr.write('transport down\\n'); sys.exit(7)",
            ]

            with (
                mock.patch.object(runner, "OUTPUT_ROOT", output_root),
                mock.patch.object(runner, "_timestamp", return_value=timestamp),
                mock.patch.object(runner, "_command", return_value=command),
            ):
                self.assertEqual(7, runner.run_job("memory-drift"))

            report_path = output_root / "reports" / f"{timestamp}-memory-drift.md"
            log_path = output_root / "logs" / f"{timestamp}-memory-drift.jsonl"

            self.assertTrue(report_path.exists())
            self.assertTrue(log_path.exists())
            report = report_path.read_text(encoding="utf-8")
            self.assertIn("Status: BROKEN", report)
            self.assertIn("transport down", report)
            self.assertIn("result: WORKING / PARTIAL / BROKEN / DATA_MISSING | BROKEN", report)

    def test_daily_closeout_native_fast_path_does_not_launch_codex(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_root = Path(temp_dir)
            run_id = "20260711T203000+1000-a1b2c3d4-daily-closeout"
            evidence = observability.build_evidence_record(
                run_id=run_id,
                observed_at="2026-07-11T10:30:00Z",
                probes=[],
                facts={"git.primary.head": "abc"},
                previous_facts={"git.primary.head": "abc"},
            )

            def collect(**kwargs):
                path = observability.ObservabilityPaths(output_root).evidence / f"{run_id}.json"
                observability.atomic_write_json(path, evidence, immutable=True)
                return evidence, path

            with (
                mock.patch.object(runner, "OUTPUT_ROOT", output_root),
                mock.patch.object(runner, "AUTOMATION_WORKTREE", REPO_ROOT),
                mock.patch.object(runner, "TARGET_WORKTREE", REPO_ROOT),
                mock.patch.object(runner.observability, "new_run_id", return_value=run_id),
                mock.patch.object(runner.observability, "collect_daily_evidence", side_effect=collect),
                mock.patch.object(runner, "_command", side_effect=AssertionError("Codex must not launch")),
            ):
                self.assertEqual(0, runner.run_job("daily-closeout"))

            run = json.loads((output_root / "runs" / f"{run_id}.json").read_text())
            self.assertEqual("SUCCEEDED", run["lifecycle_status"])
            self.assertEqual("CONFIRMING", run["usefulness"])
            self.assertIsNone(run["model"]["name"])
            self.assertEqual(0, run["usage"]["input_tokens"])
            self.assertTrue((output_root / "reports" / f"{run_id}.md").exists())

    def test_daily_closeout_model_path_uses_fake_child_and_finalizes_usage(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_root = Path(temp_dir)
            run_id = "20260711T203000+1000-a1b2c3d4-daily-closeout"
            evidence = observability.build_evidence_record(
                run_id=run_id,
                observed_at="2026-07-11T10:30:00Z",
                probes=[],
                facts={"git.primary.head": "abc"},
                previous_facts=None,
            )
            model_payload = {
                "summary": "Bootstrap state captured.",
                "findings": [
                    {
                        "fact_ids": ["git.primary.head"],
                        "classification": "Confirmed",
                        "severity": "INFO",
                        "statement": "Primary HEAD captured.",
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

            def collect(**kwargs):
                path = observability.ObservabilityPaths(output_root).evidence / f"{run_id}.json"
                observability.atomic_write_json(path, evidence, immutable=True)
                return evidence, path

            def fake_command(job, prompt_path, timestamp, **kwargs):
                output_path = kwargs["output_path"]
                script = (
                    "import json, pathlib, sys; "
                    "pathlib.Path(sys.argv[1]).write_text(sys.argv[2]); "
                    "print(json.dumps({'type':'turn.completed','usage':"
                    "{'input_tokens':1000,'cached_input_tokens':750,'output_tokens':120,'reasoning_output_tokens':40}}))"
                )
                return [sys.executable, "-c", script, str(output_path), json.dumps(model_payload)]

            with (
                mock.patch.object(runner, "OUTPUT_ROOT", output_root),
                mock.patch.object(runner, "AUTOMATION_WORKTREE", REPO_ROOT),
                mock.patch.object(runner, "TARGET_WORKTREE", REPO_ROOT),
                mock.patch.object(runner.observability, "new_run_id", return_value=run_id),
                mock.patch.object(runner.observability, "collect_daily_evidence", side_effect=collect),
                mock.patch.object(runner, "_command", side_effect=fake_command),
            ):
                self.assertEqual(0, runner.run_job("daily-closeout"))

            run = json.loads((output_root / "runs" / f"{run_id}.json").read_text())
            self.assertEqual("SUCCEEDED", run["lifecycle_status"])
            self.assertEqual(1000, run["usage"]["input_tokens"])
            self.assertEqual(250, run["usage"]["uncached_input_tokens"])
            self.assertEqual("gpt-5.4-mini", run["model"]["name"])
            self.assertTrue((output_root / "model_outputs" / f"{run_id}.json").exists())

    def test_daily_closeout_invalid_fake_child_output_fails_closed_without_retry(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_root = Path(temp_dir)
            run_id = "20260711T204000+1000-invalid1-daily-closeout"
            evidence = observability.build_evidence_record(
                run_id=run_id,
                observed_at="2026-07-11T10:40:00Z",
                probes=[],
                facts={"git.primary.head": "abc"},
                previous_facts=None,
            )
            calls = 0

            def collect(**kwargs):
                path = observability.ObservabilityPaths(output_root).evidence / f"{run_id}.json"
                observability.atomic_write_json(path, evidence, immutable=True)
                return evidence, path

            def fake_command(job, prompt_path, timestamp, **kwargs):
                nonlocal calls
                calls += 1
                output_path = kwargs["output_path"]
                script = "import pathlib, sys; pathlib.Path(sys.argv[1]).write_text('{\"summary\":\"incomplete\"}')"
                return [sys.executable, "-c", script, str(output_path)]

            with (
                mock.patch.object(runner, "OUTPUT_ROOT", output_root),
                mock.patch.object(runner, "AUTOMATION_WORKTREE", REPO_ROOT),
                mock.patch.object(runner, "TARGET_WORKTREE", REPO_ROOT),
                mock.patch.object(runner.observability, "new_run_id", return_value=run_id),
                mock.patch.object(runner.observability, "collect_daily_evidence", side_effect=collect),
                mock.patch.object(runner, "_command", side_effect=fake_command),
            ):
                self.assertEqual(2, runner.run_job("daily-closeout"))

            run = json.loads((output_root / "runs" / f"{run_id}.json").read_text())
            report = (output_root / "reports" / f"{run_id}.md").read_text()
            self.assertEqual(1, calls)
            self.assertEqual("PARTIAL", run["lifecycle_status"])
            self.assertEqual("PARTIAL", run["functionality_result"])
            self.assertEqual("invalid_structured_model_output", run["scoring_reason"])
            self.assertTrue(run["model_gate"]["actual_model_invoked"])
            self.assertIn("structured model output invalid", report)

    def test_health_rows_classify_broken_reports(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_root = Path(temp_dir)
            report_dir = output_root / "reports"
            log_dir = output_root / "logs"
            report_dir.mkdir()
            log_dir.mkdir()
            (report_dir / "20260629T120000+1000-memory-drift.md").write_text(
                "# Failure\n\nStatus: BROKEN\n",
                encoding="utf-8",
            )
            (log_dir / "20260629T120000+1000-memory-drift.jsonl").write_text(
                "transport down\n",
                encoding="utf-8",
            )

            with mock.patch.object(runner, "OUTPUT_ROOT", output_root):
                _rows, issues, records = runner._health_rows(datetime.now().astimezone())

            memory_record = next(record for record in records if record["name"] == "memory-drift")
            self.assertEqual("BROKEN_REPORT", memory_record["status"])
            self.assertIn("memory-drift: BROKEN_REPORT", issues)

    def test_health_rows_recognize_new_functionality_broken_report_shape(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_root = Path(temp_dir)
            report_dir = output_root / "reports"
            log_dir = output_root / "logs"
            report_dir.mkdir()
            log_dir.mkdir()
            (report_dir / "20260711T203000+1000-a1b2c3d4-daily-closeout.md").write_text(
                "Functionality result:\n- BROKEN\n",
                encoding="utf-8",
            )
            (log_dir / "20260711T203000+1000-a1b2c3d4-daily-closeout.jsonl").write_text(
                "failure\n",
                encoding="utf-8",
            )

            with mock.patch.object(runner, "OUTPUT_ROOT", output_root):
                _rows, issues, records = runner._health_rows(datetime.now().astimezone())

            record = next(value for value in records if value["name"] == "daily-closeout")
            self.assertEqual("BROKEN_REPORT", record["status"])
            self.assertIn("daily-closeout: BROKEN_REPORT", issues)


if __name__ == "__main__":
    unittest.main()
