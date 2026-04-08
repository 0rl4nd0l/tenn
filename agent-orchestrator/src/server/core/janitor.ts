import path from "path";

import type {
  JanitorCheckDefinition,
  JanitorResultRecord,
  TaskRecord,
  VerificationCheckType,
  WorktreeRecord
} from "../../shared/types";
import { createId } from "../utils/id";
import { pathExists, readTextSafe } from "../utils/filesystem";
import { runCommand } from "../utils/process";
import { nowIso } from "../utils/time";

export interface JanitorOptions {
  repoRoot: string;
  worktree?: WorktreeRecord | null;
  checks?: JanitorCheckDefinition[];
}

export class Janitor {
  async verifyTask(task: TaskRecord, options: JanitorOptions): Promise<JanitorResultRecord> {
    const cwd = options.worktree?.path ?? options.repoRoot;
    const checks = options.checks ?? this.defaultChecksForTask(task);
    const results: JanitorResultRecord["checks"] = [];

    for (const check of checks) {
      const outcome = await this.runCheck(check, task, cwd);
      results.push(outcome);
    }

    const diffSummary = await this.buildDiffSummary(cwd);
    const failed = results.some((check) => check.status === "failed");
    return {
      id: createId("janitor"),
      taskId: task.id,
      runId: null,
      status: failed ? "failed" : "passed",
      checks: results,
      diffSummary,
      createdAt: nowIso()
    };
  }

  private defaultChecksForTask(task: TaskRecord): JanitorCheckDefinition[] {
    const checks: JanitorCheckDefinition[] = [
      { type: "diff_sanity", label: "Diff sanity" },
      { type: "owned_file_boundary", label: "Owned file boundary" },
      { type: "merge_conflict", label: "Merge conflict check" },
      { type: "untracked_files", label: "Untracked file review" }
    ];
    for (const policy of task.verificationPolicy) {
      if (!checks.some((check) => check.type === policy)) {
        checks.push({ type: policy, label: labelForType(policy) });
      }
    }
    return checks;
  }

  private async runCheck(
    check: JanitorCheckDefinition,
    task: TaskRecord,
    cwd: string
  ): Promise<JanitorResultRecord["checks"][number]> {
    switch (check.type) {
      case "path_exists":
        return {
          ...check,
          status: check.path && pathExists(path.join(cwd, check.path)) ? "passed" : "failed",
          output: check.path ? `checked ${check.path}` : "missing check.path"
        };
      case "file_contains":
        if (!check.path || !check.contains) {
          return { ...check, status: "failed", output: "file_contains requires path and contains" };
        }
        if (!pathExists(path.join(cwd, check.path))) {
          return { ...check, status: "failed", output: `${check.path} does not exist` };
        }
        return {
          ...check,
          status: readTextSafe(path.join(cwd, check.path)).includes(check.contains) ? "passed" : "failed",
          output: `searched ${check.path} for required content`
        };
      case "diff_sanity": {
        const result = await runCommand("git", ["diff", "--stat"], { cwd });
        return {
          ...check,
          status: result.ok ? "passed" : "failed",
          output: `${result.stdout}${result.stderr}`.trim()
        };
      }
      case "owned_file_boundary": {
        const result = await runCommand("git", ["diff", "--name-only"], { cwd });
        const changedFiles = result.stdout
          .split("\n")
          .map((value) => value.trim())
          .filter(Boolean);
        const violations =
          task.ownedFiles.length === 0
            ? []
            : changedFiles.filter(
                (file) => !task.ownedFiles.some((owned) => file === owned || file.startsWith(owned.replace(/\*\*?$/, "")))
              );
        return {
          ...check,
          status: violations.length === 0 ? "passed" : "failed",
          output:
            violations.length === 0
              ? changedFiles.join("\n") || "no changed files"
              : `changed files outside owned scope:\n${violations.join("\n")}`
        };
      }
      case "merge_conflict": {
        const result = await runCommand("git", ["diff", "--check"], { cwd });
        return {
          ...check,
          status: result.ok ? "passed" : "failed",
          output: `${result.stdout}${result.stderr}`.trim() || "no merge conflict markers detected"
        };
      }
      case "untracked_files": {
        const result = await runCommand("git", ["status", "--short", "--untracked-files=all"], { cwd });
        return {
          ...check,
          status: result.ok ? "passed" : "failed",
          output: result.stdout.trim() || "clean tree"
        };
      }
      case "test":
      case "lint":
      case "typecheck":
      case "build":
      case "review":
        if (!check.command) {
          return { ...check, status: "passed", output: "no command configured" };
        }
        return this.runCommandCheck(check, cwd);
      default:
        return { ...check, status: "failed", output: "unsupported janitor check type" };
    }
  }

  private async runCommandCheck(
    check: JanitorCheckDefinition,
    cwd: string
  ): Promise<JanitorResultRecord["checks"][number]> {
    const result = await runCommand("bash", ["-lc", check.command ?? ""], { cwd });
    return {
      ...check,
      status: result.ok ? "passed" : "failed",
      output: `${result.stdout}${result.stderr}`.trim()
    };
  }

  private async buildDiffSummary(cwd: string): Promise<string> {
    const result = await runCommand("git", ["diff", "--stat"], { cwd });
    return `${result.stdout}${result.stderr}`.trim();
  }
}

function labelForType(type: VerificationCheckType): string {
  switch (type) {
    case "test":
      return "Tests";
    case "lint":
      return "Lint";
    case "typecheck":
      return "Typecheck";
    case "build":
      return "Build";
    case "path_exists":
      return "Path exists";
    case "file_contains":
      return "File contains";
    case "diff_sanity":
      return "Diff sanity";
    case "owned_file_boundary":
      return "Owned file boundary";
    case "merge_conflict":
      return "Merge conflict";
    case "untracked_files":
      return "Untracked files";
    case "review":
      return "Review";
  }
}
