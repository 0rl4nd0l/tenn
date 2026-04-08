import type {
  ChatResponse,
  HealthResponse,
  ServiceHealth,
  SystemStatus,
  QueueStatus,
  RestartBackendResponse,
} from './cockpit-types'

// ── Error class ────────────────────────────────────────────────────────────

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly statusText: string,
    public readonly body: unknown,
  ) {
    super(`API ${status} ${statusText}: ${typeof body === "string" ? body : JSON.stringify(body)}`)
    this.name = "ApiError"
  }
}

// ── Base fetch helper ──────────────────────────────────────────────────────

async function apiFetch<T>(path: string, options?: RequestInit, timeoutMs: number = 120_000): Promise<T> {
  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs)

  try {
    const res = await fetch(path, {
      ...options,
      signal: controller.signal,
      headers: {
        "Content-Type": "application/json",
        ...(options?.headers as Record<string, string> | undefined),
      },
    })

    if (!res.ok) {
      let body: unknown
      try {
        body = await res.json()
      } catch {
        try {
          body = await res.text()
        } catch {
          body = `HTTP ${res.status}`
        }
      }
      throw new ApiError(res.status, res.statusText, body)
    }

    if (res.status === 204) {
      return undefined as unknown as T
    }

    return res.json() as Promise<T>
  } catch (err) {
    if (err instanceof DOMException && err.name === 'AbortError') {
      throw new ApiError(504, 'Gateway Timeout', `Request timed out after ${Math.round(timeoutMs / 1000)}s`)
    }
    throw err
  } finally {
    clearTimeout(timeoutId)
  }
}

// ── Public API functions ───────────────────────────────────────────────────

/** Health check – GET /api/cockpit/health (aggregated) */
export async function checkHealth(): Promise<HealthResponse> {
  return apiFetch<HealthResponse>("/api/cockpit/health")
}

export function isHealthyService(service?: ServiceHealth): boolean {
  return service?.status === 'healthy'
}

export function isBackendHealthy(health?: HealthResponse): boolean {
  const backendService = health?.services?.find((service) => service.name === 'backend')
  if (backendService) return isHealthyService(backendService)
  return health?.status === 'healthy'
}

/** Send a chat message (blocking) – POST /api/cockpit/chat */
export async function sendChatMessage(params: {
  message: string
  mode: "analysis" | "strategy"
  ticker?: string
  sessionId?: string
  model?: string
  webSearch?: boolean
  rag?: boolean
  dbDiagnostics?: boolean
}): Promise<ChatResponse> {
  return apiFetch<ChatResponse>("/api/cockpit/chat", {
    method: "POST",
    body: JSON.stringify({
      message: params.message,
      mode: params.mode,
      ticker: params.ticker,
      session_id: params.sessionId,
      model: params.model,
      web_search: params.webSearch,
      rag: params.rag,
      db_diagnostics: params.dbDiagnostics,
      stream: false,
    }),
  })
}

/** SSE Streaming chat - POST /api/cockpit/chat with streaming */
export async function streamChat(params: {
  message: string
  mode: "analysis" | "strategy"
  ticker?: string
  sessionId?: string
  model?: string
  webSearch?: boolean
  rag?: boolean
  dbDiagnostics?: boolean
  onMessage: (event: { type: string; data: any }) => void
  onError: (err: any) => void
  onEnd: () => void
}) {
  const { SSE } = await import('sse.js')
  const source = new SSE("/api/cockpit/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    payload: JSON.stringify({
      message: params.message,
      mode: params.mode,
      ticker: params.ticker,
      session_id: params.sessionId,
      model: params.model,
      web_search: params.webSearch,
      rag: params.rag,
      db_diagnostics: params.dbDiagnostics,
      stream: true,
    }),
  })

  source.addEventListener('message', (e: any) => {
    try {
      const payload = JSON.parse(e.data)
      params.onMessage(payload)
    } catch (err) {
      console.error("Failed to parse SSE message:", err)
    }
  })

  source.addEventListener('error', (e: any) => {
    params.onError(e)
    source.close()
  })

  source.addEventListener('end', () => {
    params.onEnd()
    source.close()
  })

  try {
    source.stream()
  } catch (err) {
    params.onError(err)
    source.close()
  }

  return source
}

/** System config – GET /api/cockpit/config */
export async function getSystemStatus(): Promise<SystemStatus> {
  return apiFetch<SystemStatus>("/api/cockpit/config")
}

/** Queue status – GET /api/cockpit/queue */
export async function getQueueStatus(): Promise<QueueStatus> {
  return apiFetch<QueueStatus>("/api/cockpit/queue")
}

/** Restart backend – POST /api/cockpit/restart */
export async function restartBackend(): Promise<RestartBackendResponse> {
  return apiFetch<RestartBackendResponse>('/api/cockpit/restart', {
    method: 'POST',
  })
}

/** Execute a confirmed action – POST /api/cockpit/action/execute */
export async function executeAction(params: {
  actionId: string
  args: Record<string, unknown>
  sessionId?: string
}): Promise<{ result: string }> {
  return apiFetch<{ result: string }>("/api/cockpit/action/execute", {
    method: "POST",
    body: JSON.stringify({
      action_id: params.actionId,
      args: params.args,
      session_id: params.sessionId,
    }),
  }, 900_000)
}

/** Action preview – POST /api/cockpit/action/preview */
export async function previewAction(params: {
  actionId: string
  args: Record<string, unknown>
}): Promise<{
  action_id: string
  command: string[]
  summary: string
  estimated_impact: string
  timeout_seconds: number
  guard_message: string | null
}> {
  return apiFetch("/api/cockpit/action/preview", {
    method: "POST",
    body: JSON.stringify({
      action_id: params.actionId,
      args: params.args,
    }),
  })
}

/** Re-run a historical job via the action registry */
export async function rerunJob(params: {
  jobId: string
  action: string
  args: Record<string, unknown>
}): Promise<{ jobId: string; status: string }> {
  const result = await executeAction({
    actionId: params.action,
    args: params.args,
  })
  return { jobId: params.jobId, status: result.result ? 'triggered' : 'failed' }
}

/** Documents list – GET /api/cockpit/docs */
export async function listDocuments(): Promise<unknown[]> {
  return apiFetch<unknown[]>("/api/cockpit/docs")
}
