import type {
  ChatResponse,
  HealthResponse,
  SystemStatus,
  QueueStatus,
  RagResult
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

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), 120_000) // 120s timeout

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
      throw new ApiError(504, 'Gateway Timeout', 'Request timed out after 120s')
    }
    throw err
  } finally {
    clearTimeout(timeoutId)
  }
}

// ── Public API functions ───────────────────────────────────────────────────

/** Health check – GET /api/health */
export async function checkHealth(): Promise<HealthResponse> {
  return apiFetch<HealthResponse>("/api/health")
}

/** Send a chat message (blocking) – POST /chat */
export async function sendChatMessage(params: {
  message: string
  mode: "analysis" | "strategy"
  ticker?: string
  sessionId?: string
}): Promise<ChatResponse> {
  return apiFetch<ChatResponse>("/chat", {
    method: "POST",
    body: JSON.stringify({
      message: params.message,
      mode: params.mode,
      ticker: params.ticker,
      session_id: params.sessionId,
    }),
  })
}

/** SSE Streaming chat - POST /chat with streaming */
export async function streamChat(params: {
  message: string
  mode: "analysis" | "strategy"
  ticker?: string
  sessionId?: string
  onMessage: (event: { type: string; data: any }) => void
  onError: (err: any) => void
  onEnd: () => void
}) {
  const { SSE } = await import('sse.js')
  const source = new SSE("/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    payload: JSON.stringify({
      message: params.message,
      mode: params.mode,
      ticker: params.ticker,
      session_id: params.sessionId,
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

  return source
}

/** System status – GET /api/system/status */
export async function getSystemStatus(apiKey?: string): Promise<SystemStatus> {
  const headers: Record<string, string> = {}
  if (apiKey) {
    headers["X-API-Key"] = apiKey
  }
  return apiFetch<SystemStatus>("/api/system/status", { headers })
}

/** Queue status – GET /api/queue/status */
export async function getQueueStatus(): Promise<QueueStatus> {
  return apiFetch<QueueStatus>("/api/queue/status")
}

/** RAG query – POST /rag/query */
export async function queryRag(params: {
  query: string
  collection?: string
  top_k?: number
}): Promise<RagResult[]> {
  return apiFetch<RagResult[]>("/rag/query", {
    method: "POST",
    body: JSON.stringify({
      query: params.query,
      collection: params.collection,
      top_k: params.top_k,
    }),
  })
}

/** Ticker context – GET /api/context/ticker?ticker=XXX */
export async function getTickerContext(ticker: string): Promise<unknown> {
  const encoded = encodeURIComponent(ticker)
  return apiFetch<unknown>(`/api/context/ticker?ticker=${encoded}`)
}

/** Documents list – GET /api/docs */
export async function listDocuments(): Promise<unknown[]> {
  return apiFetch<unknown[]>("/api/docs")
}
