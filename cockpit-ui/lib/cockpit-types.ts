// Cockpit Types - Based on modernization plan

export interface ThinkingStep {
  assessment: string
  plan: string
}

export interface RenderedChart {
  title: string
  html: string
}

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: Date
  metadata?: {
    model?: string
    latencyMs?: number
    costUsd?: number
    source?: 'local' | 'anthropic'
  }
  thinking?: ThinkingStep
  sources?: Source[]
  toolTraces?: ToolTrace[]
  actionPreview?: ActionPreview
  chart?: RenderedChart
}

export interface Source {
  title: string
  url?: string
  score: number
  snippet?: string
}

export interface ToolTrace {
  tool: string
  durationMs: number
  status: 'success' | 'error'
}

export interface ActionPreview {
  id: string
  name: string
  description: string
  args: Record<string, unknown>
  requiresConfirmation: boolean
}

export interface ServiceHealth {
  name: string
  status: 'healthy' | 'degraded' | 'down' | 'unknown'
  endpoint?: string
  responseTimeMs?: number
  lastChecked?: Date
  error?: string
  details?: Record<string, unknown>
}

export interface CockpitPreferences {
  webSearchEnabled: boolean
  ragEnabled: boolean
  dbDiagnosticsEnabled: boolean
  showSources: boolean
  theme: 'dark' | 'light'
}

export interface Job {
  id: string
  action: string
  args: Record<string, unknown>
  status: 'pending' | 'running' | 'completed' | 'failed'
  startedAt: Date
  completedAt?: Date
  output?: string
  error?: string
}

export interface WatchlistItem {
  ticker: string
  addedAt: Date
  lastScanned?: Date
  notes?: string
}

export interface Strategy {
  id: string
  ticker: string
  criterion: string
  decision?: 'buy' | 'watchlist' | 'avoid'
  createdAt: Date
}

export interface NewsSearchResult {
  id: string
  headline: string
  source: string
  date: Date
  relevanceScore: number
  ticker?: string
  content?: string
  url?: string
}

export interface VerificationResult {
  metric: string
  expected: string | number
  actual: string | number
  passed: boolean
  details?: string
}

export interface ContextDocument {
  document_id: string
  ticker?: string | null
  exchange?: string | null
  doc_class?: string | null
  doc_subtype?: string | null
  published_at?: string | null
  period_end?: string | null
  title?: string | null
  source_url?: string | null
}

export type ExtractionMethod = 'auto' | 'docling' | 'pymupdf' | 'anthropic'

export interface ExtractionReviewSnippet {
  kind: string
  status: string
  image_path?: string | null
  image_name?: string | null
  image_url?: string | null
  ascii_preview?: string | null
  matched_text?: string | null
  page_number?: number | null
  reason?: string | null
}

export interface ExtractionReviewItem {
  item_id: string
  run_id: string
  document_id: string
  ticker?: string | null
  title?: string | null
  file_path?: string | null
  metric_name: string
  extracted_value: string | number | boolean | null
  period_end?: string | null
  period_type?: string | null
  currency?: string | null
  scale?: string | null
  page_number?: number | null
  evidence_reference?: string | null
  evidence_text?: string | null
  evidence_summary?: string | null
  provenance_status?: string | null
  source_label?: string | null
  location_ref?: string | null
  requested_method?: ExtractionMethod | null
  actual_method?: string | null
  strict_method?: boolean | null
  parser_id?: string | null
  model_id?: string | null
  runtime_id?: string | null
  fallback_used?: boolean | null
  error_stage?: string | null
  method_warnings?: string[] | null
  gold_document_id?: string | null
  gold_expected_trust?: string | null
  snippet: ExtractionReviewSnippet
  review_status: 'pending' | 'approved' | 'wrong' | 'abstain'
  reviewed_at?: string | null
  expected_value?: string | number | boolean | null
  reviewer_note?: string | null
}

export interface ExtractionReviewSession {
  session_id: string
  created_at: string
  updated_at?: string | null
  document_ids: string[]
  missing_document_ids?: string[]
  documents?: Array<{
    document_id: string
    ticker?: string | null
    title?: string | null
    status?: string | null
    run_id?: string | null
    requested_method?: ExtractionMethod | null
    actual_method?: string | null
    strict_method?: boolean | null
    items_count?: number
    created_at?: string | null
  }>
  items: ExtractionReviewItem[]
  summary?: {
    total: number
    approved: number
    wrong: number
    abstain: number
    pending: number
  }
}

export interface ExtractionReviewDecisionResponse {
  session_id: string
  item: ExtractionReviewItem
  summary: {
    total: number
    approved: number
    wrong: number
    abstain: number
    pending: number
  }
}

export interface ExtractionReviewErrorQueue {
  updated_at?: string | null
  count: number
  items: ExtractionReviewItem[]
}

export interface FinancialData {
  ticker: string
  date: Date
  revenue?: number
  netIncome?: number
  eps?: number
  marketCap?: number
  peRatio?: number
  auditConfidence?: number
}

export interface IntelPulseStats {
  document_count: number
  extraction_count: number
  signal_count: number
  memory_count: number
  population_index: number
  trust_score_avg: number
  quarantine_rate: number
}

export interface IntelPulseStageHealth {
  id: string
  label: string
  health: number
  status: string
}

export interface IntelPulseFailure {
  id: string
  entity: string
  type: string
  message: string
  confidence: number
  timestamp: string
}

export interface IntelPulseResponse {
  stats: IntelPulseStats
  pipeline: IntelPulseStageHealth[]
  failures: IntelPulseFailure[]
}

export interface IntelPulseEntityMetric {
  entity: string
  metrics: Record<string, 'populated' | 'abstain' | 'failed' | 'sparse'>
}

export interface IntelPulseMatrixResponse {
  stage: string
  entities: IntelPulseEntityMetric[]
}

// ── API Response Types ────────────────────────────────────────────────────

export interface HealthResponse {
  status: string
  version?: string
  uptime?: number
  services?: ServiceHealth[]
}

export interface ChatResponse {
  content: {
    answer: string
    model?: string
    latency_ms?: number
    cost_usd?: number
    source?: 'local' | 'anthropic'
    chart?: RenderedChart
  }
  session_id?: string
}

export interface SystemStatus {
  status: string
  services?: ServiceHealth[]
  version?: string
  uptime?: number
}

export interface QueueStatus {
  pending: number
  active: number
  completed: number
  failed: number
}

export interface RestartBackendResponse {
  ok: boolean
  message?: string
  error?: string
  stopped?: boolean
  pid?: string | null
}

export interface RagResult {
  title?: string
  snippet: string
  score: number
  metadata?: Record<string, unknown>
}

// ── Model Discovery Types ─────────────────────────────────────────────────

export interface ModelInfo {
  id: string
  filename: string
  size_gb: number
  quantization: string | null
  available: boolean
}

export interface ModelGroup {
  location: string
  label: string
  models: ModelInfo[]
}

export interface AvailableModelsResponse {
  groups: ModelGroup[]
  active_model: string | null
}

// SSE Event Types
export type SSEEventType =
  | 'chunk'
  | 'status'
  | 'thinking'
  | 'sources'
  | 'action_preview'
  | 'tool_trace'
  | 'chart'
  | 'done'
  | 'error'

export interface SSEEvent {
  type: SSEEventType
  data: unknown
}

// Slash Commands
export const SLASH_COMMANDS = [
  // Watchlist
  { command: '/watch add', description: 'Add ticker to watchlist', args: '<TICKER>' },
  { command: '/watch list', description: 'List all watchlist items', args: '' },
  { command: '/watch remove', description: 'Remove ticker from watchlist', args: '<TICKER>' },
  { command: '/watch clear', description: 'Clear entire watchlist', args: '' },
  { command: '/watch scan', description: 'Scan watchlist ticker(s)', args: '[TICKER]' },
  
  // Strategy
  { command: '/strategy list', description: 'List strategies', args: '[TICKER]' },
  { command: '/strategy add', description: 'Add strategy criterion', args: '[TICKER] <criterion>' },
  { command: '/strategy decide', description: 'Set decision for ticker', args: '<TICKER> <buy|watchlist|avoid>' },
  { command: '/strategy delete', description: 'Delete strategy', args: '<id>' },
  
  // Control
  { command: '/confirm', description: 'Confirm pending action', args: '' },
  { command: '/cancel', description: 'Cancel pending action', args: '' },
  { command: '/read', description: 'Read file contents', args: '<path> [max_chars=N]' },
  { command: '/run', description: 'Run action directly', args: '<action_id> [args]' },
  
  // Access
  { command: '/web', description: 'Toggle web search', args: 'on|off' },
  { command: '/rag', description: 'Toggle RAG', args: 'on|off' },
  { command: '/dbdiag', description: 'Toggle DB diagnostics', args: 'on|off' },
  { command: '/health', description: 'Check service health', args: '' },
  { command: '/access', description: 'Show access status', args: '' },
  { command: '/reconnect', description: 'Reconnect services', args: '' },
  
  // Preferences
  { command: '/prefer', description: 'Set preference', args: '<key>=<value>' },
  { command: '/sources', description: 'Toggle source display', args: 'on|off' },
  
  // Review
  { command: '/review list', description: 'List pending reviews', args: '' },
  { command: '/review approve', description: 'Approve review', args: '<source_id>' },
  { command: '/review reject', description: 'Reject review', args: '<source_id>' },
  { command: '/review approve-all', description: 'Approve all pending', args: '' },
  
  // Debug
  { command: '/prompt', description: 'Show system prompt', args: '' },
  { command: '/restart', description: 'Restart service', args: 'backend' },
] as const

export type Screen = 'boot' | 'chat' | 'operations' | 'updater' | 'verification' | 'history' | 'settings' | 'news'
