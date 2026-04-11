import { useCockpitStore } from './cockpit-store'
import type {
  AvailableModelsResponse,
  ChatResponse,
  ContextDocument,
  ExtractionMethod,
  ExtractionReviewDecisionResponse,
  ExtractionReviewErrorQueue,
  ExtractionReviewRunListResponse,
  ExtractionReviewRunStatusResponse,
  ExtractionReviewSession,
  HealthResponse,
  ServiceHealth,
  SystemStatus,
  QueueStatus,
  RestartBackendResponse,
  RenderedChart,
  IntelPulseResponse,
  IntelPulseMatrixResponse,
  ModelLoadResponse,
} from './cockpit-types'

const API_KEY = process.env.NEXT_PUBLIC_API_KEY || ''

function withApiKey(headers?: HeadersInit): HeadersInit {
  const merged: Record<string, string> = {
    ...(headers as Record<string, string> | undefined),
  }
  if (API_KEY) {
    merged['X-API-Key'] = API_KEY
  }
  return merged
}

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

export type ActionJobHandle = {
  action_id: string
  job_id: string
  status: string
  queued: boolean
  result?: string
}

export type ActionJobStatus = {
  job_id: string
  action_id: string
  status: string
  started_at?: string | null
  ended_at?: string | null
  exit_code?: number | null
  result?: string | null
  progress_stage?: string | null
  progress_pct?: number | null
}

// ── Base fetch helper ──────────────────────────────────────────────────────

export async function apiFetch<T>(path: string, options?: RequestInit, timeoutMs: number = 120_000): Promise<T> {
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

      // If we got a 5xx, mark as unhealthy
      if (res.status >= 500) {
        useCockpitStore.getState().setBackendStatus(false, `Server error: ${res.status}`)
      }

      throw new ApiError(res.status, res.statusText, body)
    }

    // Success! Mark as healthy
    useCockpitStore.getState().setBackendStatus(true)

    if (res.status === 204) {
      return undefined as unknown as T
    }

    return res.json() as Promise<T>
  } catch (err) {
    if (err instanceof DOMException && err.name === 'AbortError') {
      const errorMsg = `Request timed out after ${Math.round(timeoutMs / 1000)}s`
      useCockpitStore.getState().setBackendStatus(false, errorMsg)
      throw new ApiError(504, 'Gateway Timeout', errorMsg)
    }

    // For connection refused / network errors
    const errorMsg = err instanceof Error ? err.message : 'Network error'
    // Don't report "Aborted" (manual cancel) as a backend failure
    if (errorMsg !== 'The user aborted a request.' && errorMsg !== 'signal is aborted without reason') {
      useCockpitStore.getState().setBackendStatus(false, errorMsg)
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
  const raw = await apiFetch<any>("/api/cockpit/chat", {
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

  if (
    raw
    && typeof raw === 'object'
    && raw.content
    && typeof raw.content === 'object'
    && typeof raw.content.answer === 'string'
  ) {
    return raw as ChatResponse
  }

  if (
    raw
    && typeof raw === 'object'
    && raw.type === 'done'
    && raw.data
    && typeof raw.data === 'object'
  ) {
    return {
      content: {
        answer: String(raw.data.text || ''),
        model: raw.data.model,
        latency_ms: raw.data.latency_ms,
        cost_usd: raw.data.cost_usd,
        source: raw.data.source,
        chart: raw.data.chart,
      },
    }
  }

  return {
    content: {
      answer: typeof raw === 'string' ? raw : JSON.stringify(raw),
    },
  }
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

/** Available models – GET /api/cockpit/models */
export async function fetchAvailableModels(): Promise<AvailableModelsResponse> {
  return apiFetch<AvailableModelsResponse>("/api/cockpit/models")
}

export async function loadCockpitModel(modelId?: string): Promise<ModelLoadResponse> {
  return apiFetch<ModelLoadResponse>("/api/cockpit/models/load", {
    method: "POST",
    body: JSON.stringify({
      model_id: modelId ?? null,
    }),
  }, 360_000)
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
}): Promise<{ result: string; chart?: RenderedChart }> {
  return apiFetch<{ result: string; chart?: RenderedChart }>("/api/cockpit/action/execute", {
    method: "POST",
    body: JSON.stringify({
      action_id: params.actionId,
      args: params.args,
      session_id: params.sessionId,
    }),
  }, 900_000)
}

/** Start a long-running action and return its queued job handle immediately. */
export async function startActionJob(params: {
  actionId: string
  args: Record<string, unknown>
  sessionId?: string
}): Promise<ActionJobHandle> {
  return apiFetch<ActionJobHandle>("/api/cockpit/action/execute", {
    method: "POST",
    body: JSON.stringify({
      action_id: params.actionId,
      args: params.args,
      session_id: params.sessionId,
      return_job_handle: true,
    }),
  }, 120_000)
}

export async function getActionJob(jobId: string): Promise<ActionJobStatus> {
  return apiFetch<ActionJobStatus>(`/api/cockpit/action/jobs/${encodeURIComponent(jobId)}`)
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

/** Financials for a ticker – GET /api/financials?ticker=... */
export async function fetchFinancials(ticker: string): Promise<unknown[]> {
  return apiFetch<unknown[]>(`/api/financials?ticker=${encodeURIComponent(ticker)}`)
}

/** Documents list – GET /api/cockpit/docs */
export async function listDocuments(): Promise<unknown[]> {
  return apiFetch<unknown[]>("/api/cockpit/docs")
}

export async function getTickerDocuments(ticker: string, docsLimit: number = 10): Promise<ContextDocument[]> {
  const payload = await apiFetch<{ docs?: ContextDocument[] }>(
    `/api/context/ticker?ticker=${encodeURIComponent(ticker)}&docs_limit=${docsLimit}&financials_limit=1&announcements_limit=1&failures_limit=5&low_confidence_limit=5`
  )
  return Array.isArray(payload.docs) ? payload.docs : []
}

export async function processDocument(params: {
  documentId: string
  method?: ExtractionMethod
  strictMethod?: boolean
}): Promise<Record<string, unknown>> {
  return apiFetch<Record<string, unknown>>(
    `/api/process/document/${encodeURIComponent(params.documentId)}`,
    {
      method: 'POST',
      headers: withApiKey(),
      body: JSON.stringify({
        method: params.method ?? 'auto',
        strict_method: params.strictMethod ?? false,
      }),
    },
    900_000,
  )
}

export async function createExtractionReviewSession(params: {
  documentIds?: string[]
  runIds?: string[]
}): Promise<ExtractionReviewSession> {
  return apiFetch<ExtractionReviewSession>(
    '/api/extraction-review/session',
    {
      method: 'POST',
      headers: withApiKey(),
      body: JSON.stringify({
        document_ids: params.documentIds ?? [],
        run_ids: params.runIds ?? [],
      }),
    },
    120_000,
  )
}

export async function getExtractionReviewSession(sessionId: string): Promise<ExtractionReviewSession> {
  return apiFetch<ExtractionReviewSession>(
    `/api/extraction-review/session/${encodeURIComponent(sessionId)}`,
  )
}

export async function submitExtractionReviewDecision(params: {
  sessionId: string
  itemId: string
  status: 'approved' | 'wrong' | 'abstain'
  expectedValue?: string | null
  reviewerNote?: string | null
}): Promise<ExtractionReviewDecisionResponse> {
  return apiFetch<ExtractionReviewDecisionResponse>(
    `/api/extraction-review/session/${encodeURIComponent(params.sessionId)}/decision`,
    {
      method: 'POST',
      headers: withApiKey(),
      body: JSON.stringify({
        item_id: params.itemId,
        status: params.status,
        expected_value: params.expectedValue ?? null,
        reviewer_note: params.reviewerNote ?? null,
      }),
    },
    120_000,
  )
}

export async function getExtractionReviewErrors(limit: number = 200): Promise<ExtractionReviewErrorQueue> {
  return apiFetch<ExtractionReviewErrorQueue>(`/api/extraction-review/errors?limit=${limit}`)
}

export async function getExtractionReviewRuns(ticker?: string, limit: number = 50): Promise<ExtractionReviewRunListResponse> {
  const params = new URLSearchParams({ limit: String(limit) })
  if (ticker?.trim()) {
    params.set('ticker', ticker.trim().toUpperCase())
  }
  return apiFetch<ExtractionReviewRunListResponse>(`/api/extraction-review/runs?${params.toString()}`)
}

export async function getExtractionReviewRunStatus(runId: string, limit: number = 200): Promise<ExtractionReviewRunStatusResponse> {
  return apiFetch<ExtractionReviewRunStatusResponse>(
    `/api/extraction-review/run/${encodeURIComponent(runId)}?limit=${limit}`
  )
}

/** Intel Pulse – GET /api/cockpit/pulse */
export async function getIntelPulse(ticker?: string): Promise<IntelPulseResponse> {
  const normalizedTicker = ticker?.trim().toUpperCase()
  const url = normalizedTicker
    ? `/api/cockpit/pulse?ticker=${encodeURIComponent(normalizedTicker)}`
    : "/api/cockpit/pulse"
  return apiFetch<IntelPulseResponse>(url)
}

/** Diagnostic Matrix – GET /api/cockpit/matrix */
export async function getDiagnosticMatrix(stage: string, ticker?: string): Promise<IntelPulseMatrixResponse> {
  const base = `/api/cockpit/matrix?stage=${encodeURIComponent(stage)}`
  const normalizedTicker = ticker?.trim().toUpperCase()
  const url = normalizedTicker ? `${base}&ticker=${encodeURIComponent(normalizedTicker)}` : base
  return apiFetch<IntelPulseMatrixResponse>(url)
}
