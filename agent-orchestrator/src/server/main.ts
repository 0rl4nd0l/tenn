import { mkdir } from "fs/promises";
import { existsSync } from "fs";
import path from "path";

import { createHttpServer } from "./api/http";
import { OrchestratorService } from "./services/orchestrator";

async function main() {
  const appRoot = resolveAppRoot();
  const workspaceRoot = path.resolve(appRoot, "..");
  const dataDir = path.join(appRoot, ".data");
  await mkdir(dataDir, { recursive: true });

  const service = await OrchestratorService.create({
    repoRoot: process.env.AGENT_ORCHESTRATOR_WORKSPACE_ROOT ?? workspaceRoot,
    dataDir: process.env.AGENT_ORCHESTRATOR_DATA_DIR ?? dataDir
  });
  const { httpServer } = await createHttpServer(service);
  const port = Number(process.env.PORT ?? 4317);

  httpServer.listen(port, "127.0.0.1", () => {
    console.log(`Agent Orchestrator listening on http://127.0.0.1:${port}`);
  });
}

void main();

function resolveAppRoot(): string {
  const candidates = [
    process.env.AGENT_ORCHESTRATOR_APP_ROOT,
    process.cwd(),
    path.resolve(__dirname, "..", "..", "..", ".."),
    path.resolve(__dirname, "..", "..", ".."),
    path.resolve(__dirname, "..", "..")
  ].filter((candidate): candidate is string => Boolean(candidate));

  for (const candidate of candidates) {
    if (existsSync(path.join(candidate, "package.json"))) {
      return candidate;
    }
  }

  throw new Error("Unable to resolve agent-orchestrator app root");
}
