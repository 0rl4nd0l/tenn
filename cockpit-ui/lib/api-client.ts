import { useCockpitStore } from './cockpit-store'
import type {
  AvailableModelsResponse,
  ClaimVerificationResponse,
  ChatReadinessResponse,
  ChatResponse,
  ChatRuntimeTarget,
  ContextDocument,
  ExtractionMethod,
  ExtractionReviewDecisionResponse,
  ExtractionReviewErrorQueue,
  ExtractionReviewRunListResponse,
  ExtractionReviewRunStatusResponse,
  ExtractionReviewSessionListResponse,
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
  PromptLabDryRunResponse,
  PromptLabPreviewRequest,
  PromptLabPreviewResponse,
  PromptLabRoutesResponse,
  ResponseFeedbackReasonCode,
  ResponseFeedbackResponse,
  Source,
  VerificationContextResponse,
} from './cockpit-types'

const API_KEY = process.env.NEXT_PUBLIC_API_KEY || ''

function browserApiKey(): string {
  if (typeof window === 'undefined') {
    return ''
  }
  try {
    return window.localStorage.getItem('cockpit.apiKey')?.trim() ?? ''
  } catch {
    return ''
  }
}

function configuredApiKey(): string {
  return browserApiKey() || API_KEY
}

function withApiKey(headers?: HeadersInit): HeadersInit {
  const merged: Record<string, string> = {
    ...(headers as Record<string, string> | undefined),
  }
  const apiKey = configuredApiKey()
  if (apiKey) {
    merged['X-API-Key'] = apiKey
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
  chart?: RenderedChart
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

export type ChatSessionSummary = {
  session_id: string
  updated_at?: string | null
  message_count: number
  title?: string | null
  last_message?: string | null
}

export type ChatSessionListResponse = {
  items: ChatSessionSummary[]
}

export type ChatSessionMessage = {
  id: number
  session_id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  created_at: string
  metadata?: Record<string, unknown>
  sources?: Source[]
  routing_metadata?: Record<string, unknown>
  tool_traces?: Array<Record<string, unknown>>
  action_preview?: unknown
  chart?: unknown
}

export type ChatSessionMessagesResponse = {
  session_id: string
  message_count: number
  items: ChatSessionMessage[]
}

export type ChatSessionCreateResponse = {
  ok: boolean
  session_id: string
  created: boolean
}

export type VerificationRunsResponse = {
  ok?: boolean
  runs?: unknown[]
  count?: number
  error?: string
}

export type CockpitPreferences = {
  api_default_enabled: boolean
  marketplace_prefer_cloud_routing: boolean
  chat_routing_policy_override: 'config_default' | 'local_preferred' | 'local_only' | 'api_preferred' | 'api_only'
  chat_runtime_target: ChatRuntimeTarget
}

export type CockpitPreferencesPatch = {
  api_default_enabled?: boolean
  marketplace_prefer_cloud_routing?: boolean
  chat_routing_policy_override?: 'config_default' | 'local_preferred' | 'local_only' | 'api_preferred' | 'api_only'
  chat_runtime_target?: ChatRuntimeTarget
}

type AttachedChatSource = {
  source_id: string
  source_kind: string
}

export type VerifyClaimsRequest = {
  sessionId?: string | null
  messageId?: string | null
  parentPrompt?: string | null
  assistantText: string
  ticker?: string | null
  routeType?: string | null
  visibleSources?: Source[]
}

export type SubmitResponseFeedbackRequest = {
  sessionId?: string | null
  messageId?: string | null
  parentMessageId?: string | null
  userLabel?: string | null
  reasonCode: ResponseFeedbackReasonCode
  note?: string | null
  queryText?: string | null
  finalAnswerText: string
  ticker?: string | null
  companyName?: string | null
  routeType?: string | null
  modelLabel?: string | null
  confidenceLabel?: string | null
  trustLabel?: string | null
  visibleSources?: Source[]
  sourceIds?: string[]
  sourceSummary?: Record<string, unknown>[]
  traceArtifactId?: string | null
  scratchpadArtifactId?: string | null
  evidenceBundleId?: string | null
  usedFinancialTruth?: boolean | null
  usedCompanyMemory?: boolean | null
  usedMarketMemory?: boolean | null
  usedTranscriptContext?: boolean | null
  responseLatencyMs?: number | null
  extractionRunIds?: string[]
  documentIds?: string[]
  provenanceStatus?: Record<string, unknown> | null
  appVersion?: string | null
  commitHash?: string | null
  verifierResult?: ClaimVerificationResponse | null
}

export type ThesisClaimType =
  | 'numeric_fact'
  | 'company_narrative'
  | 'causal_claim'
  | 'catalyst_timing'
  | 'valuation_assumption'
  | 'market_sector_claim'

export type ThesisClaimStatus =
  | 'supported'
  | 'partially_supported'
  | 'contradicted'
  | 'stale'
  | 'assumption'
  | 'DATA_MISSING'

export type ThesisConfidenceLabel = 'Confirmed' | 'Inferred' | 'Speculative'

export type ReportSpan = {
  span_id: string
  start: number
  end: number
  text: string
}

export type EvidenceSpan = {
  evidence_id: string
  source_layer: string
  source_type: string
  text: string
  title?: string | null
  published_at?: string | null
  document_id?: string | null
  url?: string | null
  metadata?: Record<string, unknown>
}

export type ThesisClaim = {
  claim_id: string
  text: string
  claim_type: ThesisClaimType
  report_span: ReportSpan
  confidence_label: ThesisConfidenceLabel
  load_bearing_score: number
  load_bearing_rank: number
}

export type ThesisAssumption = {
  assumption_id: string
  text: string
  report_span?: ReportSpan | null
  confidence_label: ThesisConfidenceLabel
  related_claim_ids: string[]
}

export type ClaimVerification = {
  claim_id: string
  status: ThesisClaimStatus
  confidence_label: ThesisConfidenceLabel
  rationale: string
  report_span: ReportSpan
  independent_evidence_spans: EvidenceSpan[]
  contradicting_evidence_spans: EvidenceSpan[]
  evidence_gap?: string | null
}

export type ContrarianFinding = {
  break_pack: string
  finding: string
  claim_ids: string[]
  status: ThesisClaimStatus
  confidence_label: ThesisConfidenceLabel
  evidence_spans: EvidenceSpan[]
}

export type ThesisMemoryProposalCandidate = {
  proposal_type: 'create_thesis' | 'add_evidence' | 'invalidate'
  statement: string
  signal?: string | null
  confidence: number
  metadata: Record<string, unknown>
}

export type ThesisAuditEvidenceSummary = {
  evidence_span_count?: number | string | null
  memory_read_only?: boolean | null
  sufficient_for_analysis?: boolean | null
  missing_categories_after_recovery?: string[] | null
  coverage_status?: string | null
  coverage_message?: string | null
  proposal_gate?: {
    allowed?: boolean | null
    reason?: string | null
    message?: string | null
  } | null
}

export type ThesisAuditReport = {
  audit_id: string
  ticker: string
  generated_at: string
  report_source: Record<string, unknown>
  thesis_summary: string
  claims: ThesisClaim[]
  hidden_assumptions: ThesisAssumption[]
  verification_matrix: ClaimVerification[]
  contrarian_findings: ContrarianFinding[]
  strongest_disconfirming_evidence: ContrarianFinding[]
  report_to_reality_delta: string | null
  change_my_mind_triggers: string[]
  next_diligence_questions: string[]
  user_thesis_memory_proposals: ThesisMemoryProposalCandidate[]
  evidence_summary: ThesisAuditEvidenceSummary
  guardrails: Record<string, unknown>
}

export type ThesisWatchdogAlert = {
  alert_id: string
  entry_id: number
  ticker: string
  severity: 'contradict' | 'support' | 'diverge' | 'neutral'
  finding: string
  evidence_source_id: string
  status: 'unread' | 'read' | 'dismissed' | 'acted'
  metadata: {
    excerpt?: string
    severity_score?: number
  }
  created_at: string
}

export type ThesisAuditCoverageReport = {
  ticker: string
  generated_at?: string | null
  evidence_summary: ThesisAuditEvidenceSummary
  guardrails: Record<string, unknown>
}

export type RunThesisAuditRequest = {
  ticker: string
  reportText?: string
  filename?: string
  mimeType?: string
  contentBase64?: string
  focus?: string
}

export type CreateUserThesisProposalRequest = {
  ticker: string
  proposal_type: 'create_thesis' | 'add_evidence' | 'invalidate'
  statement: string
  signal?: string | null
  confidence?: number
  metadata?: Record<string, unknown>
  note?: string | null
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

    if (err instanceof ApiError) {
      // Only mark as offline for 5xx errors
      if (err.status >= 500) {
        useCockpitStore.getState().setBackendStatus(false, err.message)
      }
      throw err
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

/** Chat answer readiness – GET /api/cockpit/chat/readiness */
export async function fetchChatReadiness(ticker?: string | null): Promise<ChatReadinessResponse> {
  const normalizedTicker = String(ticker || '').trim().toUpperCase()
  const query = normalizedTicker ? `?ticker=${encodeURIComponent(normalizedTicker)}` : ''
  return apiFetch<ChatReadinessResponse>(`/api/cockpit/chat/readiness${query}`, undefined, 30_000)
}

/** Shared chat sessions – GET /api/cockpit/chat/sessions */
export async function listChatSessions(limit: number = 100): Promise<ChatSessionSummary[]> {
  const safeLimit = Math.max(1, Math.min(limit, 500))
  const response = await apiFetch<ChatSessionListResponse>(`/api/cockpit/chat/sessions?limit=${safeLimit}`)
  return Array.isArray(response.items) ? response.items : []
}

/** Cockpit routing preferences – GET /api/cockpit/preferences */
export async function getCockpitPreferences(): Promise<CockpitPreferences> {
  return apiFetch<CockpitPreferences>('/api/cockpit/preferences')
}

/** Cockpit routing preferences – PATCH /api/cockpit/preferences */
export async function patchCockpitPreferences(patch: CockpitPreferencesPatch): Promise<CockpitPreferences> {
  return apiFetch<CockpitPreferences>(
    '/api/cockpit/preferences',
    {
      method: 'PATCH',
      body: JSON.stringify(patch),
    },
  )
}

/** Shared chat messages for a session – GET /api/cockpit/chat/sessions/{session_id} */
export async function getChatSessionMessages(
  sessionId: string,
  limit: number = 400,
): Promise<ChatSessionMessage[]> {
  const safeSessionId = encodeURIComponent((sessionId || '').trim())
  const safeLimit = Math.max(1, Math.min(limit, 2000))
  const response = await apiFetch<ChatSessionMessagesResponse>(
    `/api/cockpit/chat/sessions/${safeSessionId}?limit=${safeLimit}`,
  )
  return Array.isArray(response.items) ? response.items : []
}

/** Create or touch a shared chat session – POST /api/cockpit/chat/sessions */
export async function createChatSessionRemote(sessionId?: string): Promise<ChatSessionCreateResponse> {
  const payload = typeof sessionId === 'string' && sessionId.trim()
    ? { session_id: sessionId.trim() }
    : {}
  return apiFetch<ChatSessionCreateResponse>(
    '/api/cockpit/chat/sessions',
    {
      method: 'POST',
      body: JSON.stringify(payload),
    },
  )
}

function serializeVerificationSource(source: Source): Record<string, unknown> {
  return {
    title: source.title,
    url: source.url,
    score: source.score,
    snippet: source.snippet,
    published_at: source.publishedAt,
    document_id: source.documentId,
    source_id: source.sourceId,
    doc_type: source.docType,
    path: source.path,
    kind: source.kind,
  }
}

export async function verifyClaims(
  params: VerifyClaimsRequest,
  apiKey?: string,
): Promise<ClaimVerificationResponse> {
  return apiFetch<ClaimVerificationResponse>(
    '/api/cockpit/claims/verify',
    {
      method: 'POST',
      headers: apiKey ? { 'X-API-Key': apiKey } : undefined,
      body: JSON.stringify({
        session_id: params.sessionId || null,
        message_id: params.messageId || null,
        parent_prompt: params.parentPrompt || null,
        assistant_text: params.assistantText,
        ticker: params.ticker || null,
        route_type: params.routeType || null,
        visible_sources: (params.visibleSources || []).map(serializeVerificationSource),
      }),
    },
  )
}

export async function submitResponseFeedback(
  params: SubmitResponseFeedbackRequest,
  apiKey?: string,
): Promise<ResponseFeedbackResponse> {
  const visibleSources = params.visibleSources || []
  const sourceIds = params.sourceIds
    ?? visibleSources
      .map((source) => source.sourceId || source.documentId || source.url || source.title)
      .filter((value): value is string => Boolean(value))
  const documentIds = params.documentIds
    ?? visibleSources
      .map((source) => source.documentId)
      .filter((value): value is string => Boolean(value))
  const sourceSummary = params.sourceSummary
    ?? visibleSources.map(serializeVerificationSource)

  return apiFetch<ResponseFeedbackResponse>(
    '/api/cockpit/feedback',
    {
      method: 'POST',
      headers: apiKey ? { 'X-API-Key': apiKey } : undefined,
      body: JSON.stringify({
        session_id: params.sessionId || null,
        message_id: params.messageId || null,
        parent_message_id: params.parentMessageId || null,
        user_label: params.userLabel || 'issue_report',
        reason_code: params.reasonCode,
        note: params.note || null,
        query_text: params.queryText || null,
        final_answer_text: params.finalAnswerText,
        ticker: params.ticker || null,
        company_name: params.companyName || null,
        route_type: params.routeType || null,
        model_label: params.modelLabel || null,
        confidence_label: params.confidenceLabel || null,
        trust_label: params.trustLabel || null,
        sources_present: sourceIds.length > 0 || sourceSummary.length > 0,
        source_ids: sourceIds,
        source_summary: sourceSummary,
        trace_artifact_id: params.traceArtifactId || null,
        scratchpad_artifact_id: params.scratchpadArtifactId || null,
        evidence_bundle_id: params.evidenceBundleId || null,
        used_financial_truth: params.usedFinancialTruth ?? null,
        used_company_memory: params.usedCompanyMemory ?? null,
        used_market_memory: params.usedMarketMemory ?? null,
        used_transcript_context: params.usedTranscriptContext ?? null,
        response_latency_ms: params.responseLatencyMs ?? null,
        extraction_run_ids: params.extractionRunIds || [],
        document_ids: documentIds,
        provenance_status: params.provenanceStatus || null,
        app_version: params.appVersion || null,
        commit_hash: params.commitHash || null,
        verifier_result: params.verifierResult || null,
      }),
    },
  )
}

export async function runThesisAudit(
  params: RunThesisAuditRequest,
  apiKey?: string,
): Promise<ThesisAuditReport> {
  return apiFetch<ThesisAuditReport>(
    '/api/cockpit/thesis-audit',
    {
      method: 'POST',
      headers: apiKey ? { 'X-API-Key': apiKey } : undefined,
      body: JSON.stringify({
        ticker: params.ticker,
        report_text: params.reportText || null,
        filename: params.filename || null,
        mime_type: params.mimeType || null,
        content_base64: params.contentBase64 || null,
        focus: params.focus || null,
      }),
    },
    240_000,
  )
}

export async function getThesisAuditCoverage(
  ticker: string,
  apiKey?: string,
): Promise<ThesisAuditCoverageReport> {
  return apiFetch<ThesisAuditCoverageReport>(
    `/api/cockpit/thesis-audit/coverage?ticker=${encodeURIComponent(ticker)}`,
    {
      method: 'GET',
      headers: apiKey ? { 'X-API-Key': apiKey } : undefined,
    },
    60_000,
  )
}

export async function listThesisWatchdogAlerts(
  params: { ticker?: string; status?: string } = {},
  apiKey?: string,
): Promise<{ ok: boolean; alerts: ThesisWatchdogAlert[] }> {
  let url = '/api/cockpit/thesis-audit/alerts'
  const searchParams = new URLSearchParams()
  if (params.ticker) searchParams.append('ticker', params.ticker)
  if (params.status) searchParams.append('status', params.status)
  if (searchParams.toString()) url += `?${searchParams.toString()}`

  return apiFetch<{ ok: boolean; alerts: ThesisWatchdogAlert[] }>(url, {
    method: 'GET',
    headers: apiKey ? { 'X-API-Key': apiKey } : undefined,
  })
}

export async function updateThesisWatchdogAlertStatus(
  alertId: string,
  status: ThesisWatchdogAlert['status'],
  apiKey?: string,
): Promise<{ ok: boolean; alert: ThesisWatchdogAlert }> {
  return apiFetch<{ ok: boolean; alert: ThesisWatchdogAlert }>(
    `/api/cockpit/thesis-audit/alerts/${alertId}/status`,
    {
      method: 'POST',
      headers: apiKey ? { 'X-API-Key': apiKey } : undefined,
      body: JSON.stringify({ status }),
    },
  )
}

export async function createUserThesisProposal(
  params: CreateUserThesisProposalRequest,
  apiKey?: string,
): Promise<{ ok: boolean; proposal: Record<string, unknown> }> {
  return apiFetch<{ ok: boolean; proposal: Record<string, unknown> }>(
    '/api/cockpit/memory/thesis/proposals',
    {
      method: 'POST',
      headers: apiKey ? { 'X-API-Key': apiKey } : undefined,
      body: JSON.stringify({
        ticker: params.ticker,
        proposal_type: params.proposal_type,
        statement: params.statement,
        signal: params.signal || null,
        confidence: params.confidence ?? 0.6,
        metadata: params.metadata || {},
        note: params.note || null,
      }),
    },
  )
}

/** Delete shared chat session – DELETE /api/cockpit/chat/sessions/{session_id} */
export async function deleteChatSessionRemote(sessionId: string): Promise<{ ok: boolean; deleted_count: number }> {
  const safeSessionId = encodeURIComponent((sessionId || '').trim())
  const response = await apiFetch<{ ok: boolean; deleted_count: number }>(
    `/api/cockpit/chat/sessions/${safeSessionId}`,
    { method: 'DELETE' },
  )
  return response
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
  attachedSources?: AttachedChatSource[]
  runtimeTarget?: ChatRuntimeTarget
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
      attached_sources: params.attachedSources,
      runtime_target: params.runtimeTarget,
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
	        provider_error: raw.data.provider_error ?? null,
	        chart: raw.data.chart,
	        action_preview: raw.data.action_preview,
	        routing_metadata: raw.data.routing_metadata,
        sources: Array.isArray(raw.data.sources)
          ? raw.data.sources.map((s: any) => ({
              title: s.title,
              url: s.url,
              score: s.score,
              snippet: s.snippet,
              publishedAt: s.published_at,
              documentId: s.document_id,
              sourceId: s.source_id,
              docType: s.doc_type,
              path: s.path,
              kind: s.kind,
              evidenceLabel: s.evidence_label,
              evidenceLabels: Array.isArray(s.evidence_labels) ? s.evidence_labels : undefined,
              claimVerified: Boolean(s.claim_verified),
            }))
          : undefined,
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
  attachedSources?: AttachedChatSource[]
  runtimeTarget?: ChatRuntimeTarget
  onMessage: (event: { type: string; data: any }) => void
  onError: (err: any) => void
  onEnd: () => void
}) {
  const { SSE } = await import('sse.js')
  const source = new SSE("/api/cockpit/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    // sse.js starts streaming in the constructor by default. Disable that so
    // we can attach listeners before the first status event is emitted.
    start: false,
    payload: JSON.stringify({
      message: params.message,
      mode: params.mode,
      ticker: params.ticker,
      session_id: params.sessionId,
      model: params.model,
      web_search: params.webSearch,
      rag: params.rag,
      db_diagnostics: params.dbDiagnostics,
      attached_sources: params.attachedSources,
      runtime_target: params.runtimeTarget,
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

export async function loadCockpitModel(modelId?: string, runtimeTarget?: ChatRuntimeTarget): Promise<ModelLoadResponse> {
  return apiFetch<ModelLoadResponse>("/api/cockpit/models/load", {
    method: "POST",
    body: JSON.stringify({
      model_id: modelId ?? null,
      runtime_target: runtimeTarget,
    }),
  }, 360_000)
}

export async function getPromptLabRoutes(): Promise<PromptLabRoutesResponse> {
  return apiFetch<PromptLabRoutesResponse>('/api/cockpit/prompts/routes')
}

export async function previewPromptLabRoute(
  payload: PromptLabPreviewRequest,
): Promise<PromptLabPreviewResponse> {
  return apiFetch<PromptLabPreviewResponse>('/api/cockpit/prompts/preview', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export async function dryRunPromptLabRoute(
  payload: PromptLabPreviewRequest,
): Promise<PromptLabDryRunResponse> {
  return apiFetch<PromptLabDryRunResponse>('/api/cockpit/prompts/dry-run', {
    method: 'POST',
    body: JSON.stringify(payload),
  }, 180_000)
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
    headers: {
      'X-Cockpit-Restart-Intent': 'restart-backend',
    },
    body: JSON.stringify({
      intent: 'restart-backend',
      confirmation: 'RESTART BACKEND',
    }),
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

export async function stopActionJob(jobId: string): Promise<{
  ok: boolean
  job_id: string
  status: string
}> {
  return apiFetch(`/api/cockpit/action/jobs/${encodeURIComponent(jobId)}/stop`, {
    method: 'POST',
  })
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
  return apiFetch<unknown[]>("/api/cockpit/docs", { headers: withApiKey() })
}

export async function getTickerDocuments(ticker: string, docsLimit: number = 10): Promise<ContextDocument[]> {
  const normalizedTicker = ticker.trim().toUpperCase()
  const payload = await apiFetch<{ docs?: ContextDocument[] }>(
    `/api/context/ticker?ticker=${encodeURIComponent(normalizedTicker)}&docs_limit=${docsLimit}&financials_limit=1&announcements_limit=1&failures_limit=5&low_confidence_limit=5`,
    { headers: withApiKey() },
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
    { headers: withApiKey() },
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
  return apiFetch<ExtractionReviewErrorQueue>(
    `/api/extraction-review/errors?limit=${limit}`,
    { headers: withApiKey() },
  )
}

export async function getExtractionReviewRuns(ticker?: string, limit: number = 50): Promise<ExtractionReviewRunListResponse> {
  const params = new URLSearchParams({ limit: String(limit) })
  if (ticker?.trim()) {
    params.set('ticker', ticker.trim().toUpperCase())
  }
  return apiFetch<ExtractionReviewRunListResponse>(
    `/api/extraction-review/runs?${params.toString()}`,
    { headers: withApiKey() },
  )
}

export async function getExtractionReviewSessions(ticker?: string, limit: number = 50): Promise<ExtractionReviewSessionListResponse> {
  const params = new URLSearchParams({ limit: String(limit) })
  if (ticker?.trim()) {
    params.set('ticker', ticker.trim().toUpperCase())
  }
  return apiFetch<ExtractionReviewSessionListResponse>(
    `/api/extraction-review/sessions?${params.toString()}`,
    { headers: withApiKey() },
  )
}

export async function getExtractionReviewRunStatus(runId: string, limit: number = 200): Promise<ExtractionReviewRunStatusResponse> {
  return apiFetch<ExtractionReviewRunStatusResponse>(
    `/api/extraction-review/run/${encodeURIComponent(runId)}?limit=${limit}`,
    { headers: withApiKey() },
  )
}

function extractionReviewSnippetPath(imageUrl: string): string {
  const prefix = '/api/extraction-review/snippets/'
  const path = imageUrl.trim()
  const imageName = path.startsWith(prefix) ? path.slice(prefix.length) : ''
  if (!imageName || imageName.includes('/') || imageName.includes('\\')) {
    throw new Error('Invalid extraction review snippet URL')
  }
  return path
}

export async function getExtractionReviewSnippetObjectUrl(imageUrl: string): Promise<string> {
  const snippetPath = extractionReviewSnippetPath(imageUrl)
  const response = await fetch(snippetPath, { headers: withApiKey() })

  if (!response.ok) {
    let body: unknown = `HTTP ${response.status}`
    try {
      body = await response.json()
    } catch {
      try {
        body = await response.text()
      } catch {
        body = `HTTP ${response.status}`
      }
    }
    throw new ApiError(response.status, response.statusText, body)
  }

  const blob = await response.blob()
  return URL.createObjectURL(blob)
}

export async function runVerificationContext(params: {
  ticker?: string | null
  failuresLimit?: number
  lowConfidenceThreshold?: number
  lowConfidenceLimit?: number
}): Promise<VerificationContextResponse> {
  return apiFetch<VerificationContextResponse>(
    '/api/context/verification/run',
    {
      method: 'POST',
      headers: withApiKey(),
      body: JSON.stringify({
        ticker: params.ticker?.trim() || null,
        failures_limit: params.failuresLimit ?? 100,
        low_confidence_threshold: params.lowConfidenceThreshold ?? 0.4,
        low_confidence_limit: params.lowConfidenceLimit ?? 100,
      }),
    },
  )
}

export async function getVerificationRuns(limit: number = 10): Promise<VerificationRunsResponse> {
  return apiFetch<VerificationRunsResponse>(
    `/api/context/verification/runs?limit=${limit}`,
    { headers: withApiKey() },
  )
}

/** Intel Pulse – GET /api/cockpit/pulse */
export async function getIntelPulse(ticker?: string): Promise<IntelPulseResponse> {
  const normalizedTicker = ticker?.trim().toUpperCase()
  const url = normalizedTicker
    ? `/api/cockpit/pulse?ticker=${encodeURIComponent(normalizedTicker)}`
    : "/api/cockpit/pulse"
  return apiFetch<IntelPulseResponse>(url, { headers: withApiKey() })
}

/** Diagnostic Matrix – GET /api/cockpit/matrix */
export async function getDiagnosticMatrix(stage: string, ticker?: string): Promise<IntelPulseMatrixResponse> {
  const base = `/api/cockpit/matrix?stage=${encodeURIComponent(stage)}`
  const normalizedTicker = ticker?.trim().toUpperCase()
  const url = normalizedTicker ? `${base}&ticker=${encodeURIComponent(normalizedTicker)}` : base
  return apiFetch<IntelPulseMatrixResponse>(url, { headers: withApiKey() })
}
