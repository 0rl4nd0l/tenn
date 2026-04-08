import assert from "assert";
import { execFileSync } from "child_process";
import fs from "fs";
import path from "path";

import type { AdapterSpawnInput, AgentAdapter } from "../src/server/adapters/base";
import { AdapterRegistry } from "../src/server/adapters";
import { OwnershipLockManager } from "../src/server/core/locks";
import { TaskSpawner } from "../src/server/core/spawner";
import { DEFAULT_TOKEN_BUDGET } from "../src/shared/types";
import type { ProjectSnapshot, ProviderCapabilitySnapshot, TaskRecord } from "../src/shared/types";
import { buildBoardState } from "../src/server/api/state";
import { TaskRouter } from "../src/server/core/router";
import { TaskScheduler } from "../src/server/core/scheduler";
import { StrategistRuntimeRunner } from "../src/server/core/strategist-runtime";
import { StrategistService, materializeTaskGraph } from "../src/server/core/strategist";
import { TokenBudgetManager } from "../src/server/core/token-budget";
import { WorktreeManager } from "../src/server/core/worktrees";
import { OpenCodeAdapter } from "../src/server/adapters/opencode";
import { OrchestratorService } from "../src/server/services/orchestrator";
import type { StoreCollections } from "../src/server/db/database";
import { findFirstInstalledCommand } from "../src/server/utils/process";

function makeCapability(
  runtime: ProviderCapabilitySnapshot["runtime"],
  partial: Partial<ProviderCapabilitySnapshot> = {}
): ProviderCapabilitySnapshot {
  const provider =
    runtime === "claude"
      ? "anthropic"
      : runtime === "gemini"
        ? "google"
        : runtime === "cursor"
          ? "cursor"
          : runtime === "opencode"
            ? "opencode"
            : runtime.startsWith("codex")
              ? "openai"
              : "generic";

  return {
    runtime,
    provider,
    title: runtime,
    command: runtime,
    version: "1.0.0",
    installStatus: "installed",
    authStatus: "authenticated",
    detectedAt: new Date().toISOString(),
    models: ["default-model", "fallback-model"],
    supportsNativeSubagents: runtime === "opencode" || runtime.startsWith("codex"),
    supportsCloud: runtime === "codex-cloud",
    supportsContextStats: runtime === "claude" || runtime === "gemini",
    supportsCompaction: runtime === "claude" || runtime === "opencode",
    supportsModelSelection: true,
    supportsModeSelection: runtime === "claude" || runtime === "opencode",
    supportsBestOfN: runtime === "codex-cloud",
    supportsInternetControl: runtime !== "cursor",
    supportsReadOnlyPlanMode: runtime !== "cursor",
    supportsWorktreeExecution: runtime !== "codex-cloud",
    exactUsageSupported: runtime.startsWith("codex"),
    nativeStatsSupported: runtime === "claude" || runtime.startsWith("codex") || runtime === "gemini",
    maxContextWindow: runtime === "gemini" ? 1_000_000 : runtime === "claude" ? 200_000 : 128_000,
    maxOutputTokens: 32_000,
    costTier: runtime === "gemini" ? "low" : "medium",
    quotaState: "healthy",
    telemetryConfidence: 0.8,
    notes: [],
    ...partial
  };
}

function makeTask(partial: Partial<TaskRecord> = {}): TaskRecord {
  return {
    id: "task_test",
    goalId: "goal_test",
    parentId: null,
    title: "Implement orchestrator backend",
    description: "Build deterministic routing and write-task isolation for the orchestrator.",
    status: "ready",
    role: "worker",
    taskType: "implement",
    agentMode: "single",
    delegationPolicy: "hybrid",
    locality: "local",
    runtimeCandidates: ["codex-local", "claude", "gemini", "opencode", "generic", "codex-cloud", "cursor"],
    providerCandidates: ["openai", "anthropic", "google", "opencode", "generic", "cursor"],
    preferredRuntime: null,
    preferredProvider: null,
    chosenRuntime: null,
    chosenProvider: null,
    chosenModel: null,
    ownedFiles: ["agent-orchestrator/src/server/router.ts"],
    readOnlyPaths: [],
    verificationPolicy: ["diff_sanity", "owned_file_boundary", "merge_conflict"],
    tokenBudget: DEFAULT_TOKEN_BUDGET,
    dependencies: [],
    attempts: 0,
    maxAttempts: 3,
    routingRationale: null,
    constraints: {
      ambiguity: 0.4,
      reasoningDepth: 0.55,
      repoSliceSize: 4
    },
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
    ...partial
  };
}

function makeSpawnHandle(runtime: ProviderCapabilitySnapshot["runtime"], externalId: string | null = null) {
  return {
    runtime,
    capability: makeCapability(runtime),
    externalId,
    mode: "remote" as const,
    wait: async () => ({
      ok: true,
      command: runtime,
      args: [],
      stdout: "",
      stderr: "",
      exitCode: 0,
      durationMs: 0
    }),
    cancel: async () => undefined,
    isAlive: async () => false
  };
}

function createTempGitRepo(): { repoRoot: string; cleanup: () => void } {
  const tempBase = path.join(process.cwd(), ".tmp", "tests");
  fs.mkdirSync(tempBase, { recursive: true });
  const repoRoot = fs.mkdtempSync(path.join(tempBase, "worktree-"));
  execFileSync("git", ["init"], { cwd: repoRoot });
  execFileSync("git", ["config", "user.email", "codex@example.com"], { cwd: repoRoot });
  execFileSync("git", ["config", "user.name", "Codex"], { cwd: repoRoot });
  fs.writeFileSync(path.join(repoRoot, "README.md"), "seed\n", "utf8");
  execFileSync("git", ["add", "README.md"], { cwd: repoRoot });
  execFileSync("git", ["commit", "-m", "seed"], { cwd: repoRoot });
  return {
    repoRoot,
    cleanup: () => fs.rmSync(repoRoot, { recursive: true, force: true })
  };
}

class TestableOpenCodeAdapter extends OpenCodeAdapter {
  buildArgs(input: AdapterSpawnInput): string[] {
    return this.buildSpawnArgs(input);
  }
}

function git(cwd: string, args: string[]): string {
  return execFileSync("git", args, { cwd, encoding: "utf8" }).trim();
}

function makeProjectSnapshot(partial: Partial<ProjectSnapshot> = {}): ProjectSnapshot {
  return {
    generatedAt: new Date().toISOString(),
    repoRoot: process.cwd(),
    projects: [
      {
        path: ".",
        kind: "workspace",
        name: "TENN",
        summary: "Workspace root",
        keyFiles: ["README.md"]
      },
      {
        path: "agent-orchestrator",
        kind: "node",
        name: "agent-orchestrator",
        summary: "Node app",
        keyFiles: ["agent-orchestrator/README.md"]
      }
    ],
    dirtyFiles: ["agent-orchestrator/src/server/core/strategist.ts"],
    evidenceMatches: [],
    queryTerms: [],
    operationalHealth: {
      totalTasks: 8,
      runningTasks: 1,
      failedTasks: 0,
      blockedTasks: 0,
      reviewTasks: 1,
      liveSessions: 1,
      authenticatedRuntimes: ["codex-local", "codex-cloud"],
      degradedRuntimes: ["claude"],
      latestFailures: []
    },
    ...partial
  };
}

function makeCollections(partial: Partial<StoreCollections> = {}): StoreCollections {
  return {
    tasks: [],
    sessions: [],
    runs: [],
    events: [],
    logs: [],
    janitorResults: [],
    reviews: [],
    locks: [],
    worktrees: [],
    capabilities: [],
    conversation: {
      latestPlanTaskId: null,
      messages: []
    },
    ...partial
  };
}

function testTokenBudget(): void {
  const manager = new TokenBudgetManager();
  const budget = manager.estimateBudget(makeTask(), makeCapability("codex-local"));
  assert.ok(budget.headroomRatio > 0.2, "expected usable token headroom");
  assert.ok(["healthy", "caution", "compact_or_fork", "migrate"].includes(budget.headroomBand));
}

function testRouter(): void {
  const router = new TaskRouter(new TokenBudgetManager());
  const implementPlan = router.routeTask(makeTask(), [
    makeCapability("claude"),
    makeCapability("codex-local"),
    makeCapability("gemini")
  ]);
  assert.equal(implementPlan.runtime, "codex-local");
  assert.equal(implementPlan.useWorktree, true);

  const explorePlan = router.routeTask(
    makeTask({
      taskType: "explore",
      ownedFiles: [],
      readOnlyPaths: ["."],
      constraints: {
        ambiguity: 0.8,
        reasoningDepth: 0.7,
        needsLargeContext: true,
        repoSliceSize: 30
      }
    }),
    [makeCapability("gemini"), makeCapability("claude"), makeCapability("codex-local")]
  );
  assert.equal(explorePlan.runtime, "gemini");

  const authenticatedFallback = router.routeTask(
    makeTask({
      taskType: "explore",
      ownedFiles: [],
      readOnlyPaths: ["."]
    }),
    [
      makeCapability("claude", { authStatus: "logged_out" }),
      makeCapability("codex-local", { authStatus: "authenticated" })
    ]
  );
  assert.equal(
    authenticatedFallback.runtime,
    "codex-local",
    "router should prefer authenticated runtimes over logged-out ones when viable"
  );

  const preferredImplement = router.routeTask(
    makeTask({
      taskType: "implement",
      preferredRuntime: "codex-local",
      preferredProvider: "openai"
    }),
    [makeCapability("opencode"), makeCapability("codex-local")]
  );
  assert.equal(preferredImplement.runtime, "codex-local", "suitable preferred runtime should win for implementation");

  const unsuitablePreferredExplore = router.routeTask(
    makeTask({
      taskType: "explore",
      preferredRuntime: "codex-local",
      preferredProvider: "openai",
      ownedFiles: [],
      readOnlyPaths: ["."]
    }),
    [makeCapability("gemini"), makeCapability("codex-local")]
  );
  assert.equal(
    unsuitablePreferredExplore.runtime,
    "gemini",
    "unsuitable preferred runtime should not override a materially better explore candidate"
  );
}

function testScheduler(): void {
  const scheduler = new TaskScheduler({ maxParallelTasks: 2, maxParallelReadTasks: 2 });
  const discover = makeTask({ id: "discover", taskType: "explore", status: "done", ownedFiles: [] });
  const implement = makeTask({ id: "implement", dependencies: ["discover"], status: "ready" });
  const verify = makeTask({
    id: "verify",
    taskType: "verify",
    dependencies: ["implement"],
    status: "ready",
    ownedFiles: []
  });

  const runnable = scheduler.selectRunnableTasks([discover, implement, verify], [], []);
  assert.deepEqual(
    runnable.map((task) => task.id),
    ["implement"],
    "scheduler should only release tasks with satisfied dependencies"
  );
}

async function testStrategistRuntimeRunner(): Promise<void> {
  process.env.STRATEGIST_CHAT_RUNTIME = "codex-local";
  try {
    const observedArgs: string[][] = [];
    const runner = new StrategistRuntimeRunner((command, args, options) => {
      observedArgs.push(args);
      options.onStdout?.('{"type":"item.completed","item":{"type":"agent_message","text":"hello from codex"}}\n');
      return {
        id: "proc_test",
        pid: 123,
        startedAt: new Date().toISOString(),
        child: {} as never,
        wait: async () => ({
          ok: true,
          command,
          args,
          stdout: "",
          stderr: "",
          exitCode: 0,
          durationMs: 5
        }),
        cancel: async () => undefined,
        isAlive: () => false
      };
    });

    const reply = await new Promise<string>((resolve, reject) => {
      runner.run(
        {
          message: "how r u",
          fallbackReply: "fallback",
          cwd: process.cwd(),
          capabilities: [makeCapability("codex-local")],
          conversation: {
            latestPlanTaskId: null,
            messages: [{ id: "m1", role: "user", content: "hi", createdAt: new Date().toISOString() }]
          },
          projectSummary: "Active project: agent-orchestrator."
        },
        {
          onDelta: () => undefined,
          onComplete: resolve,
          onError: reject
        }
      );
    });

    assert.ok(observedArgs[0]?.includes("--json"));
    assert.ok(observedArgs[0]?.includes("--cd"));
    assert.equal(reply, "hello from codex");

    const resumedReply = await new Promise<string>((resolve, reject) => {
      runner.run(
        {
          message: "how r u",
          fallbackReply: "fallback",
          cwd: process.cwd(),
          capabilities: [makeCapability("codex-local")],
          conversation: {
            latestPlanTaskId: null,
            messages: [{ id: "m1", role: "user", content: "hi", createdAt: new Date().toISOString() }]
          },
          sessionId: "session-123"
        },
        {
          onDelta: () => undefined,
          onComplete: resolve,
          onError: reject
        }
      );
    });

    assert.equal(resumedReply, "hello from codex");
    assert.equal(observedArgs[1]?.[0], "exec");
    assert.equal(observedArgs[1]?.[1], "resume");
    assert.equal(observedArgs[1]?.[2], "session-123");
  } finally {
    delete process.env.STRATEGIST_CHAT_RUNTIME;
  }

  const fallbackRunner = new StrategistRuntimeRunner();
  const fallbackReply = await new Promise<string>((resolve, reject) => {
    fallbackRunner.run(
      {
        message: "hi",
        fallbackReply: "fallback",
        cwd: process.cwd(),
        capabilities: [makeCapability("codex-local", { authStatus: "logged_out" })],
        conversation: {
          latestPlanTaskId: null,
          messages: []
        }
      },
      {
        onDelta: () => undefined,
        onComplete: resolve,
        onError: reject
      }
    );
  });
  assert.equal(fallbackReply, "fallback");
}

async function testStoreAndStrategist(): Promise<void> {
  const strategist = new StrategistService();
  const plan = strategist.plan("goal_test", "Implement routing, verification, and docs for the orchestrator.");
  const graph = materializeTaskGraph(plan);
  const rootTask = graph.rootTask;
  assert.ok(rootTask, "delegating prompts should create a root task");
  const collections = makeCollections();
  collections.tasks.push(rootTask, ...graph.childTasks);
  collections.conversation.latestPlanTaskId = rootTask.id;
  const board = buildBoardState("goal_test", collections);
  assert.ok(graph.childTasks.length >= 3, "strategist should create a task graph");
  assert.ok(graph.childTasks.some((task) => task.taskType === "explore"));
  assert.ok(graph.childTasks.some((task) => task.taskType === "verify"));
  assert.ok(board.tasks.some((task) => task.taskType === "planning"));
  assert.ok(board.stats.queue.readyTasks >= 1);

  const conversational = strategist.plan("goal_test", "what u think?", {
    conversation: {
      latestPlanTaskId: rootTask.id,
      messages: [
        { id: "m1", role: "user", content: "lets harden the accuracy of the pdf ingestion system", createdAt: new Date().toISOString() }
      ]
    },
    projectSnapshot: makeProjectSnapshot({
      evidenceMatches: [
        { term: "pdf", path: "financial-engine_v2/scripts/marketindex_download_pdfs.py" },
        { term: "ingestion", path: "financial-engine_v2/scripts/marketindex_ingest.py" }
      ]
    })
  });
  assert.equal(conversational.mode, "respond");
  assert.equal(conversational.childTasks.length, 0);
  assert.match(conversational.reply, /golden PDF corpus|accuracy/i);

  const assessment = strategist.plan("goal_test", "hows the system looking", {
    conversation: collections.conversation,
    projectSnapshot: makeProjectSnapshot()
  });
  assert.equal(assessment.mode, "respond");
  assert.match(assessment.reply, /Active root/i);
  assert.match(assessment.reply, /Current workspace state/i);
  assert.match(assessment.reply, /agent-orchestrator/i);

  const inspection = strategist.plan("goal_test", "what models do we have on nvme", {
    conversation: collections.conversation,
    projectSnapshot: makeProjectSnapshot({
      queryTerms: ["models", "nvme"],
      evidenceMatches: [{ term: "models", path: "agent-orchestrator/scripts/smoke.ts" }]
    })
  });
  assert.equal(inspection.mode, "delegate");
  const inspectionGraph = materializeTaskGraph(inspection);
  assert.ok(inspectionGraph.rootTask, "concrete local inspection prompts should create a root task");
  assert.ok(inspectionGraph.childTasks.some((task) => task.taskType === "explore"));
  assert.ok(inspectionGraph.childTasks.some((task) => task.taskType === "verify"));
  assert.ok(!inspectionGraph.childTasks.some((task) => task.taskType === "implement"));
  assert.match(inspection.reply, /I'll check that/i);
  assert.doesNotMatch(inspection.reply, /Initial task graph|read-only discovery|token-aware/i);

  const sizeInspection = strategist.plan("goal_test", "repo size?", {
    conversation: collections.conversation,
    projectSnapshot: makeProjectSnapshot({
      queryTerms: ["repo", "size"],
      evidenceMatches: [{ term: "repo", path: "agent-orchestrator/README.md" }]
    })
  });
  assert.equal(sizeInspection.mode, "delegate");
  const sizeGraph = materializeTaskGraph(sizeInspection);
  assert.ok(sizeGraph.rootTask, "repo size prompts should create a root task");
  assert.ok(sizeGraph.childTasks.some((task) => task.taskType === "explore"));
  assert.ok(sizeGraph.childTasks.some((task) => task.taskType === "verify"));
  assert.ok(!sizeGraph.childTasks.some((task) => task.taskType === "implement"));
  assert.match(sizeInspection.reply, /I'll check that/i);
  assert.doesNotMatch(sizeInspection.reply, /Initial task graph|read-only discovery|token-aware/i);
}

async function testProcessAndOpenCodeAttachMode(): Promise<void> {
  const tempBase = path.join(process.cwd(), ".tmp", "tests");
  fs.mkdirSync(tempBase, { recursive: true });
  const executable = path.join(tempBase, "fake-opencode");
  fs.writeFileSync(executable, "#!/usr/bin/env bash\nexit 0\n", "utf8");
  fs.chmodSync(executable, 0o755);
  assert.equal(await findFirstInstalledCommand([executable]), executable);

  const adapter = new TestableOpenCodeAdapter();
  const input: AdapterSpawnInput = {
    task: makeTask({
      id: "task_opencode",
      title: "Inspect local models",
      description: "List local model files on NVMe.",
      taskType: "explore",
      role: "worker"
    }),
    plan: {
      runtime: "opencode",
      provider: "opencode",
      model: "google/gemini-2.5-pro",
      useWorktree: false,
      agentMode: "single",
      delegationMode: "single",
      rationale: {
        summary: "test",
        tokenBudget: {
          estimatedInputTokens: 0,
          estimatedOutputTokens: 0,
          estimatedTotalTokens: 0,
          headroomRatio: 1,
          headroomBand: "healthy"
        },
        reasons: []
      }
    },
    cwd: process.cwd(),
    prompt: "Inspect local models",
    extraEnv: {}
  };

  delete process.env.OPENCODE_SERVER_URL;
  const runArgs = adapter.buildArgs(input);
  assert.equal(runArgs[0], "run");
  assert.ok(runArgs.includes("--agent"));

  process.env.OPENCODE_SERVER_URL = "http://127.0.0.1:4096";
  const attachArgs = adapter.buildArgs(input);
  assert.deepEqual(attachArgs.slice(0, 6), [
    "run",
    "--attach",
    "http://127.0.0.1:4096",
    "--model",
    "google/gemini-2.5-pro",
    "--dir"
  ]);
  assert.equal(attachArgs[6], process.cwd());
  assert.equal(attachArgs[attachArgs.length - 1], adapter["formatPrompt"](input));
  assert.ok(!attachArgs.includes("--max-steps"));
  delete process.env.OPENCODE_SERVER_URL;
}

async function testStrategistDelegationRequiresApproval(): Promise<void> {
  const repo = createTempGitRepo();
  const dataDir = path.join(repo.repoRoot, ".orchestrator-data");
  try {
    const service = await OrchestratorService.create({
      repoRoot: repo.repoRoot,
      dataDir,
      autoSchedule: false,
      goalId: "approval-test"
    });
    try {
      const pending = await service.startStrategistRun("how big is the repo", {
        runtime: "opencode",
        model: "openai/gpt-5.4"
      });
      assert.equal(pending.createdTaskIds.length, 0, "delegation should not create tasks before approval");

      const pendingBoard = await service.getBoardState();
      assert.equal(pendingBoard.tasks.length, 0, "board should remain task-free before approval");
      assert.match(
        pendingBoard.conversation.messages[pendingBoard.conversation.messages.length - 1]?.content ?? "",
        /Do you want me to proceed\?/i
      );

      const unrelated = await service.startStrategistRun("what is 2+2", {
        runtime: "opencode",
        model: "openai/gpt-5.4"
      });
      assert.equal(unrelated.createdTaskIds.length, 0, "unrelated follow-up should not create tasks either");
      const clarificationBoard = await service.getBoardState();
      assert.match(
        clarificationBoard.conversation.messages[clarificationBoard.conversation.messages.length - 1]?.content ?? "",
        /still waiting/i,
        "should reprompt when non-yes/no reply follows approval request"
      );

      const approved = await service.startStrategistRun("yes", {
        runtime: "opencode",
        model: "openai/gpt-5.4"
      });
      assert.ok(approved.createdTaskIds.length > 0, "approval should create delegated tasks");

      const approvedBoard = await service.getBoardState();
      assert.ok(approvedBoard.tasks.length > 0, "board should contain delegated tasks after approval");
      assert.match(
        approvedBoard.conversation.messages[approvedBoard.conversation.messages.length - 1]?.content ?? "",
        /Starting work/i
      );
    } finally {
      await service.dispose();
    }
  } finally {
    repo.cleanup();
  }
}

async function testWorktreeLifecycleAndSpawnWiring(): Promise<void> {
  const repo = createTempGitRepo();
  const worktreeBaseDir = path.join(repo.repoRoot, ".worktrees");
  const worktreeManager = new WorktreeManager(repo.repoRoot, worktreeBaseDir);
  const taskId = "task_worktree";
  try {
    const created = await worktreeManager.create(taskId);
    assert.ok(fs.existsSync(created.path), "worktree should be created on first run");
    assert.match(git(repo.repoRoot, ["branch", "--list", created.branchName]), new RegExp(created.branchName));

    const cleaned = await worktreeManager.cleanup(created);
    assert.equal(cleaned.status, "cleaned");
    assert.ok(!fs.existsSync(created.path), "cleanup should remove the worktree path");
    assert.equal(git(repo.repoRoot, ["branch", "--list", created.branchName]), "", "cleanup should delete the branch");

    const recreated = await worktreeManager.create(taskId);
    assert.ok(fs.existsSync(recreated.path), "rerun should be able to create the same task branch again");
    await worktreeManager.cleanup(recreated);

    let capturedSpawnInput: AdapterSpawnInput | null = null;
    const capturingAdapter: AgentAdapter = {
      runtime: "codex-cloud",
      detectCapability: async () => makeCapability("codex-cloud"),
      spawn: async (input) => {
        capturedSpawnInput = input;
        return makeSpawnHandle("codex-cloud", "cloud-123");
      },
      followUp: async () => makeSpawnHandle("codex-cloud", "cloud-123"),
      cancel: async () => undefined,
      isAlive: async () => false,
      supportsNativeSubagents: () => true
    };
    const captureSpawner = new TaskSpawner({
      repoRoot: repo.repoRoot,
      adapterRegistry: new AdapterRegistry([capturingAdapter]),
      worktreeManager,
      lockManager: new OwnershipLockManager()
    });
    const cloudTask = makeTask({
      id: "cloud-task",
      goalId: "goal-cloud",
      constraints: { cloudEnvironmentId: "env-123" }
    });
    const cloudPlan = new TaskRouter(new TokenBudgetManager()).routeTask(cloudTask, [makeCapability("codex-cloud")]);
    await captureSpawner.spawnTask(cloudTask, cloudPlan, "Prompt");
    assert.equal(capturedSpawnInput?.cloudEnvironmentId, "env-123");

    const failingAdapter: AgentAdapter = {
      runtime: "codex-local",
      detectCapability: async () => makeCapability("codex-local"),
      spawn: async () => {
        throw new Error("spawn failed");
      },
      followUp: async () => makeSpawnHandle("codex-local", "local-123"),
      cancel: async () => undefined,
      isAlive: async () => false,
      supportsNativeSubagents: () => false
    };
    const failingSpawner = new TaskSpawner({
      repoRoot: repo.repoRoot,
      adapterRegistry: new AdapterRegistry([failingAdapter]),
      worktreeManager,
      lockManager: new OwnershipLockManager()
    });
    const failingTask = makeTask({
      id: "spawn-fail-task",
      goalId: "goal-fail"
    });
    const failingPlan = {
      ...new TaskRouter(new TokenBudgetManager()).routeTask(failingTask, [makeCapability("codex-local")]),
      useWorktree: true
    };
    await assert.rejects(() => failingSpawner.spawnTask(failingTask, failingPlan, "Prompt"), /spawn failed/);
    assert.ok(!fs.existsSync(path.join(worktreeBaseDir, failingTask.id)), "failed spawn should clean the worktree path");
    assert.equal(git(repo.repoRoot, ["branch", "--list", `agent/${failingTask.id}`]), "", "failed spawn should clean the branch");
  } finally {
    repo.cleanup();
  }
}

async function main(): Promise<void> {
  testTokenBudget();
  testRouter();
  testScheduler();
  await testStrategistRuntimeRunner();
  await testStoreAndStrategist();
  await testProcessAndOpenCodeAttachMode();
  await testStrategistDelegationRequiresApproval();
  await testWorktreeLifecycleAndSpawnWiring();
  console.log("orchestrator-core tests passed");
}

void main().catch((error) => {
  console.error(error);
  process.exit(1);
});
