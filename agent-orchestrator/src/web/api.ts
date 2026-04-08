import { BoardState, StrategistResponse, TaskDetailPayload } from "../shared/types";

const BASE_URL = "";

async function readJson<T>(input: RequestInfo, init?: RequestInit): Promise<T> {
  const response = await fetch(input, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {})
    }
  });

  const raw = await response.text();
  const contentType = response.headers.get("content-type") ?? "";

  let payload: unknown = null;
  if (raw.trim().length > 0) {
    try {
      payload = JSON.parse(raw);
    } catch {
      payload = null;
    }
  }

  if (!response.ok) {
    if (payload && typeof payload === "object" && "error" in payload && typeof (payload as { error: unknown }).error === "string") {
      throw new Error((payload as { error: string }).error);
    }
    if (raw.trim().startsWith("<!DOCTYPE") || raw.trim().startsWith("<html")) {
      throw new Error("API returned HTML instead of JSON. Check that the web app is pointed at the orchestrator server.");
    }
    throw new Error(response.statusText || `HTTP ${response.status}`);
  }

  if (!payload) {
    if (raw.trim().startsWith("<!DOCTYPE") || raw.trim().startsWith("<html") || contentType.includes("text/html")) {
      throw new Error("API returned HTML instead of JSON. Check that the web app is pointed at the orchestrator server.");
    }
    throw new Error("API returned a non-JSON response.");
  }

  return payload as T;
}

export const api = {
  getBoard(): Promise<BoardState> {
    return readJson<BoardState>(`${BASE_URL}/api/board`);
  },
  getTask(taskId: string): Promise<TaskDetailPayload> {
    return readJson<TaskDetailPayload>(`${BASE_URL}/api/tasks/${taskId}`);
  },
  sendChat(message: string): Promise<StrategistResponse> {
    return readJson<StrategistResponse>(`${BASE_URL}/api/chat`, {
      method: "POST",
      body: JSON.stringify({ message })
    });
  },
  retryTask(taskId: string) {
    return readJson(`${BASE_URL}/api/tasks/${taskId}/retry`, { method: "POST" });
  },
  reassignTask(taskId: string, runtime: string) {
    return readJson(`${BASE_URL}/api/tasks/${taskId}/reassign`, {
      method: "POST",
      body: JSON.stringify({ runtime })
    });
  },
  approveTask(taskId: string) {
    return readJson(`${BASE_URL}/api/tasks/${taskId}/approve`, { method: "POST" });
  },
  rejectTask(taskId: string) {
    return readJson(`${BASE_URL}/api/tasks/${taskId}/reject`, { method: "POST" });
  },
  reopenTask(taskId: string) {
    return readJson(`${BASE_URL}/api/tasks/${taskId}/reopen`, { method: "POST" });
  },
  tick() {
    return readJson(`${BASE_URL}/api/tick`, { method: "POST" });
  },
  refreshRuntimes() {
    return readJson(`${BASE_URL}/api/runtimes/refresh`, { method: "POST" });
  }
};
