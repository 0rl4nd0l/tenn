import { execFile, spawn, type ChildProcess } from "child_process";
import { promisify } from "util";

import { createId } from "./id";
import { nowIso } from "./time";

const execFileAsync = promisify(execFile);

export interface CommandResult {
  ok: boolean;
  command: string;
  args: string[];
  stdout: string;
  stderr: string;
  exitCode: number | null;
  durationMs: number;
}

export interface SpawnedProcessHandle {
  id: string;
  pid: number | undefined;
  startedAt: string;
  wait: () => Promise<CommandResult>;
  cancel: () => Promise<void>;
  isAlive: () => boolean;
  child: ChildProcess;
}

export async function runCommand(
  command: string,
  args: string[],
  options: {
    cwd?: string;
    env?: NodeJS.ProcessEnv;
    timeoutMs?: number;
  } = {}
): Promise<CommandResult> {
  const startedAt = Date.now();
  try {
    const result = await execFileAsync(command, args, {
      cwd: options.cwd,
      env: options.env,
      timeout: options.timeoutMs,
      maxBuffer: 10 * 1024 * 1024
    });
    return {
      ok: true,
      command,
      args,
      stdout: result.stdout ?? "",
      stderr: result.stderr ?? "",
      exitCode: 0,
      durationMs: Date.now() - startedAt
    };
  } catch (error) {
    const failure = error as NodeJS.ErrnoException & {
      stdout?: string;
      stderr?: string;
      code?: number | string;
    };
    return {
      ok: false,
      command,
      args,
      stdout: failure.stdout ?? "",
      stderr: failure.stderr ?? failure.message ?? "",
      exitCode: typeof failure.code === "number" ? failure.code : null,
      durationMs: Date.now() - startedAt
    };
  }
}

export function spawnCommand(
  command: string,
  args: string[],
  options: {
    cwd?: string;
    env?: NodeJS.ProcessEnv;
    onStdout?: (chunk: string) => void;
    onStderr?: (chunk: string) => void;
  } = {}
): SpawnedProcessHandle {
  const child = spawn(command, args, {
    cwd: options.cwd,
    env: options.env,
    stdio: ["ignore", "pipe", "pipe"]
  });
  let stdout = "";
  let stderr = "";
  const startedAt = nowIso();

  child.stdout?.on("data", (chunk: Buffer | string) => {
    const text = chunk.toString();
    stdout += text;
    options.onStdout?.(text);
  });

  child.stderr?.on("data", (chunk: Buffer | string) => {
    const text = chunk.toString();
    stderr += text;
    options.onStderr?.(text);
  });

  return {
    id: createId("proc"),
    pid: child.pid,
    startedAt,
    child,
    wait: async () =>
      new Promise<CommandResult>((resolve) => {
        child.once("close", (code) => {
          resolve({
            ok: code === 0,
            command,
            args,
            stdout,
            stderr,
            exitCode: code,
            durationMs: Date.now() - Date.parse(startedAt)
          });
        });
      }),
    cancel: async () =>
      new Promise<void>((resolve) => {
        if (child.killed || child.exitCode !== null) {
          resolve();
          return;
        }
        child.once("close", () => resolve());
        child.kill("SIGTERM");
        setTimeout(() => {
          if (child.exitCode === null) {
            child.kill("SIGKILL");
          }
        }, 2500);
      }),
    isAlive: () => child.exitCode === null && !child.killed
  };
}

export async function findFirstInstalledCommand(commands: string[]): Promise<string | null> {
  for (const command of commands) {
    const result = await runCommand("which", [command]);
    if (result.ok && result.stdout.trim()) {
      return result.stdout.trim();
    }
  }
  return null;
}
