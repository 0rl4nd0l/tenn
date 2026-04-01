// Cockpit Types - Based on modernization plan

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
  sources?: Source[]
  toolTraces?: ToolTrace[]
  actionPreview?: ActionPreview
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

export interface RagResult {
  title?: string
  snippet: string
  score: number
  metadata?: Record<string, unknown>
}

// SSE Event Types
export type SSEEventType = 
  | 'chunk'
  | 'sources'
  | 'action_preview'
  | 'tool_trace'
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
