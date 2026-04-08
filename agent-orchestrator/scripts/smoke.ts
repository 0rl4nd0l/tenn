import fs from "fs";
import path from "path";

import { OrchestratorService } from "../src/server/services/orchestrator";

async function main() {
  const repoRoot = path.resolve(__dirname, "..", "..");
  const dataDir = path.join(repoRoot, "agent-orchestrator", ".tmp", "smoke-data");
  const previousRuntime = process.env.STRATEGIST_CHAT_RUNTIME;
  process.env.STRATEGIST_CHAT_RUNTIME = "";
  fs.rmSync(dataDir, { recursive: true, force: true });
  fs.mkdirSync(dataDir, { recursive: true });

  const service = await OrchestratorService.create({
    repoRoot,
    dataDir,
    goalId: "smoke-goal",
    autoSchedule: false
  });

  try {
    const initialBoard = await service.getBoardState();
    if (initialBoard.conversation.messages.length === 0) {
      throw new Error("Expected seeded strategist readiness message.");
    }

    const response = await service.startStrategistRun("Plan a new verification-focused task graph for the orchestrator.");
    if (!response.createdTaskIds.length) {
      throw new Error("Expected strategist to create delegated tasks.");
    }

    await new Promise<void>((resolve, reject) => {
      const timer = setTimeout(() => {
        unsubscribe();
        reject(new Error("Timed out waiting for strategist stream completion."));
      }, 30000);
      let unsubscribe = () => undefined;
      unsubscribe = service.subscribeStrategistRun(response.runId, {
        onEntry: () => undefined,
        onEnd: () => {
          clearTimeout(timer);
          unsubscribe();
          resolve();
        }
      });
    });

    const board = await service.getBoardState();
    if (board.tasks.length < 4) {
      throw new Error("Expected the strategist to materialize a usable task graph.");
    }

    const detail = await service.getTaskDetail(response.rootTaskId ?? board.tasks[0]?.id ?? "");
    if (!detail) {
      throw new Error("Expected task detail payload to be available.");
    }

    console.log(
      JSON.stringify({
        ok: true,
        conversationMessages: board.conversation.messages.length,
        taskCount: board.tasks.length,
        createdTaskIds: response.createdTaskIds.length,
        firstTaskStatus: board.tasks[0]?.status ?? null
      })
    );
  } finally {
    if (previousRuntime === undefined) {
      delete process.env.STRATEGIST_CHAT_RUNTIME;
    } else {
      process.env.STRATEGIST_CHAT_RUNTIME = previousRuntime;
    }
    await service.dispose();
  }
}

void main().catch((error) => {
  console.error(error);
  process.exit(1);
});
