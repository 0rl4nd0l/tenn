import { mkdir } from "fs/promises";
import { existsSync } from "fs";
import { runCommand } from "./utils/process";
import path from "path";

import { createHttpServer } from "./api/http";
import { OrchestratorService } from "./services/orchestrator";

async function main() {
  const appRoot = resolveAppRoot();
  const workspaceRoot = path.resolve(appRoot, "..");
  const dataDir = path.join(appRoot, ".data");
  ensureOpenCodePath();
  await ensureLocalOpenCodeServer(workspaceRoot);
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

function ensureOpenCodePath(): void {
  const openCodeBinDir = "/home/l4nd0/.opencode/bin";
  const currentPath = process.env.PATH ?? "";
  const pathEntries = currentPath.split(path.delimiter).filter((entry) => entry.length > 0);
  if (!pathEntries.includes(openCodeBinDir)) {
    process.env.PATH = [openCodeBinDir, ...pathEntries].join(path.delimiter);
  }
}

async function ensureLocalOpenCodeServer(workspaceRoot: string): Promise<void> {
  const serverUrl = process.env.OPENCODE_SERVER_URL?.trim();
  if (!serverUrl) {
    return;
  }

  let url: URL;
  try {
    url = new URL(serverUrl);
  } catch {
    console.warn(`[opencode] skipping shared-server bootstrap; invalid OPENCODE_SERVER_URL=${serverUrl}`);
    return;
  }

  const localHosts = new Set(["127.0.0.1", "localhost"]);
  if (!localHosts.has(url.hostname)) {
    return;
  }

  const scriptPath = path.join(workspaceRoot, "scripts", "opencode-server");
  if (!existsSync(scriptPath)) {
    console.warn(`[opencode] shared-server bootstrap script not found at ${scriptPath}`);
    return;
  }

  const result = await runCommand(scriptPath, ["start"], {
    cwd: workspaceRoot,
    env: process.env,
    timeoutMs: 15_000
  });
  if (!result.ok) {
    const detail = result.stderr.trim() || result.stdout.trim() || "unknown error";
    console.warn(`[opencode] shared-server bootstrap failed: ${detail}`);
    return;
  }
  const output = result.stdout.trim();
  if (output) {
    console.log(output);
  }
}

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
