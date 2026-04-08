import fs from "fs";
import path from "path";

import type { WorktreeRecord } from "../../shared/types";
import { ensureDir, pathExists } from "../utils/filesystem";
import { createId } from "../utils/id";
import { runCommand } from "../utils/process";
import { nowIso } from "../utils/time";

export class WorktreeManager {
  private readonly baseDir: string;

  constructor(private readonly repoRoot: string, baseDir?: string) {
    this.baseDir = baseDir ?? path.join(repoRoot, "agent-orchestrator", ".tmp", "worktrees");
    ensureDir(this.baseDir);
  }

  async create(taskId: string, baseRef = "HEAD"): Promise<WorktreeRecord> {
    const branchName = `agent/${taskId}`;
    const worktreePath = path.join(this.baseDir, taskId);

    if (!pathExists(worktreePath)) {
      ensureDir(path.dirname(worktreePath));
      const result = await runCommand("git", ["worktree", "add", "-b", branchName, worktreePath, baseRef], {
        cwd: this.repoRoot
      });
      if (!result.ok) {
        throw new Error(`failed to create worktree: ${result.stderr || result.stdout}`);
      }
      this.linkRuntimeDependencies(worktreePath);
    }

    const now = nowIso();
    return {
      id: createId("wt"),
      taskId,
      branchName,
      path: worktreePath,
      baseRef,
      status: "active",
      createdAt: now,
      updatedAt: now
    };
  }

  async preserve(record: WorktreeRecord): Promise<WorktreeRecord> {
    return {
      ...record,
      status: "preserved",
      updatedAt: nowIso()
    };
  }

  async cleanup(record: WorktreeRecord): Promise<WorktreeRecord> {
    const failures: string[] = [];
    if (pathExists(record.path)) {
      const removeResult = await runCommand("git", ["worktree", "remove", "--force", record.path], {
        cwd: this.repoRoot
      });
      if (!removeResult.ok) {
        failures.push(removeResult.stderr || removeResult.stdout || `failed to remove worktree ${record.path}`);
      }
    }
    const branchDeleted = await this.deleteBranchIfPresent(record.branchName);
    if (!branchDeleted.ok) {
      failures.push(branchDeleted.error);
    }
    if (failures.length > 0) {
      throw new Error(`failed to cleanup worktree ${record.path}: ${failures.join("; ")}`);
    }
    return {
      ...record,
      status: "cleaned",
      updatedAt: nowIso()
    };
  }

  async detectOrphans(): Promise<string[]> {
    const result = await runCommand("git", ["worktree", "list", "--porcelain"], {
      cwd: this.repoRoot
    });
    if (!result.ok) {
      return [];
    }

    return result.stdout
      .split("\n")
      .filter((line) => line.startsWith("worktree "))
      .map((line) => line.replace("worktree ", "").trim())
      .filter((worktreePath) => worktreePath.startsWith(this.baseDir) && !pathExists(path.join(worktreePath, ".git")));
  }

  private linkRuntimeDependencies(worktreePath: string): void {
    const appRoot = path.join(this.repoRoot, "agent-orchestrator");
    const targetRoot = path.join(worktreePath, "agent-orchestrator");
    const sourceNodeModules = path.join(appRoot, "node_modules");
    const targetNodeModules = path.join(targetRoot, "node_modules");

    if (!pathExists(sourceNodeModules) || pathExists(targetNodeModules)) {
      return;
    }

    ensureDir(targetRoot);
    fs.symlinkSync(sourceNodeModules, targetNodeModules, "dir");
  }

  private async deleteBranchIfPresent(
    branchName: string
  ): Promise<{ ok: true } | { ok: false; error: string }> {
    const branchExists = await runCommand(
      "git",
      ["show-ref", "--verify", "--quiet", `refs/heads/${branchName}`],
      { cwd: this.repoRoot }
    );
    if (!branchExists.ok) {
      return { ok: true };
    }

    const deleteResult = await runCommand("git", ["branch", "-D", branchName], { cwd: this.repoRoot });
    if (!deleteResult.ok) {
      return {
        ok: false,
        error: deleteResult.stderr || deleteResult.stdout || `failed to delete branch ${branchName}`
      };
    }
    return { ok: true };
  }
}
