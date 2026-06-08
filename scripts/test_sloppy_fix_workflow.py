import os
import subprocess
import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "sloppy-fix.yml"


class GitHubActionsYamlLoader(yaml.SafeLoader):
    pass


GitHubActionsYamlLoader.yaml_implicit_resolvers = {
    key: list(resolvers)
    for key, resolvers in yaml.SafeLoader.yaml_implicit_resolvers.items()
}

for key, resolvers in list(GitHubActionsYamlLoader.yaml_implicit_resolvers.items()):
    GitHubActionsYamlLoader.yaml_implicit_resolvers[key] = [
        (tag, regexp)
        for tag, regexp in resolvers
        if tag != "tag:yaml.org,2002:bool"
    ]


def load_workflow() -> dict:
    return yaml.load(WORKFLOW.read_text(encoding="utf-8"), Loader=GitHubActionsYamlLoader)


class SloppyFixWorkflowTests(unittest.TestCase):
    def _workflow(self) -> dict:
        return load_workflow()

    def _fix_job(self) -> dict:
        return self._workflow()["jobs"]["fix"]

    def _comment_job(self) -> dict:
        return self._workflow()["jobs"]["comment"]

    def _fix_steps(self) -> list[dict]:
        return self._fix_job()["steps"]

    def _step_named(self, name: str) -> dict:
        for step in self._fix_steps():
            if step.get("name") == name:
                return step
        self.fail(f"Missing workflow step: {name}")

    def test_automatic_seeded_issue_run_fails_when_fix_reports_zero(self):
        step = self._step_named("Fail Sloppy fix when seeded issues remain unfixed")
        condition = step.get("if", "")
        self.assertIn("github.event_name == 'workflow_run'", condition)
        self.assertIn("steps.auth.outputs.enabled == 'true'", condition)
        self.assertIn("steps.sloppy_issues.outputs.found_count != '0'", condition)
        self.assertIn("steps.sloppy_issues.outputs.found_count != 'missing_artifact'", condition)

        env = os.environ.copy()
        env.update({"SEEDED_ISSUE_COUNT": "3", "FIXED_ISSUE_COUNT": "0"})
        zero_fixed = subprocess.run(
            ["bash", "-c", step["run"]],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            check=False,
        )
        self.assertNotEqual(zero_fixed.returncode, 0)
        self.assertIn("failing closed", (zero_fixed.stdout + zero_fixed.stderr).lower())

        env.update({"FIXED_ISSUE_COUNT": "1"})
        one_fixed = subprocess.run(
            ["bash", "-c", step["run"]],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            check=False,
        )
        self.assertEqual(one_fixed.returncode, 0, one_fixed.stdout + one_fixed.stderr)

    def test_sloppy_fix_preserves_claude_provider_auth_and_model(self):
        step = self._step_named("Sloppy fix (Claude)")
        self.assertEqual(step.get("id"), "sloppy_fix")
        self.assertEqual(step.get("uses"), "braedonsaunders/sloppy@main")
        self.assertEqual(step.get("with", {}).get("mode"), "fix")
        self.assertEqual(step.get("with", {}).get("agent"), "claude")
        self.assertEqual(step.get("with", {}).get("model"), "claude-sonnet-4-5-20250929")
        self.assertEqual(step.get("with", {}).get("output-file"), "${{ steps.sloppy_issues.outputs.path }}")
        self.assertIn("ANTHROPIC_API_KEY", step.get("env", {}))
        self.assertIn("CLAUDE_CODE_OAUTH_TOKEN", step.get("env", {}))

    def test_seeded_and_fixed_counts_propagate_to_comment_job(self):
        outputs = self._fix_job()["outputs"]
        self.assertEqual(outputs["seeded_issue_count"], "${{ steps.sloppy_issues.outputs.found_count }}")
        self.assertEqual(outputs["fixed_issue_count"], "${{ steps.sloppy_fix.outputs['issues-fixed'] }}")

        comment_step = self._comment_job()["steps"][0]
        env = comment_step["env"]
        self.assertEqual(env["SEEDED_ISSUE_COUNT"], "${{ needs.fix.outputs.seeded_issue_count }}")
        self.assertEqual(env["FIXED_ISSUE_COUNT"], "${{ needs.fix.outputs.fixed_issue_count }}")
        self.assertIn("failed closed", comment_step["with"]["script"])

    def test_workflow_dispatch_and_workflow_run_are_unscheduled(self):
        triggers = self._workflow()["on"]
        self.assertIn("workflow_dispatch", triggers)
        self.assertIn("workflow_run", triggers)
        self.assertNotIn("schedule", triggers)
        self.assertNotIn("cron:", WORKFLOW.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
