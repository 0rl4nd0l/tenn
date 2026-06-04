import type {
  ChatReadinessCapability,
  ChatReadinessResponse,
  ChatReadinessStatus,
} from './cockpit-types'

export type ChatReadinessTone = 'ready' | 'warning' | 'blocked'

export type ChatReadinessCapabilityRow = {
  id: string
  label: string
  status: ChatReadinessStatus
  ready: boolean
  blockers: string[]
  answerScope: string
}

export type ChatReadinessViewModel = {
  shouldRender: boolean
  tone: ChatReadinessTone
  headline: string
  detail: string
  tickerLabel: string | null
  normalAnalysisAllowed: boolean
  answerReady: boolean
  primaryBlockers: string[]
  capabilityRows: ChatReadinessCapabilityRow[]
  safeActivationActions: string[]
}

const CAPABILITY_ORDER = [
  'financial_fact',
  'filing_document_summary',
  'local_news_rag',
  'portfolio_holdings_context',
  'memory_context',
  'strategy_action_preview',
  'model_route_runtime',
]

function normalizeCapability(capability: ChatReadinessCapability): ChatReadinessCapabilityRow {
  return {
    id: capability.id,
    label: capability.label || capability.id,
    status: capability.status,
    ready: Boolean(capability.ready),
    blockers: Array.isArray(capability.blockers)
      ? capability.blockers.map(String).filter(Boolean)
      : [],
    answerScope: String(capability.answerScope || capability.answer_scope || 'answer'),
  }
}

function orderedCapabilities(
  capabilities: Record<string, ChatReadinessCapability> | undefined,
): ChatReadinessCapabilityRow[] {
  if (!capabilities || typeof capabilities !== 'object') {
    return []
  }
  const ordered = CAPABILITY_ORDER
    .map((id) => capabilities[id])
    .filter((item): item is ChatReadinessCapability => Boolean(item))
    .map(normalizeCapability)
  const rest = Object.entries(capabilities)
    .filter(([id]) => !CAPABILITY_ORDER.includes(id))
    .map(([, item]) => normalizeCapability(item))
  return [...ordered, ...rest]
}

function fallbackBlockedModel(detail: string): ChatReadinessViewModel {
  return {
    shouldRender: true,
    tone: 'blocked',
    headline: 'Normal analysis blocked',
    detail,
    tickerLabel: null,
    normalAnalysisAllowed: false,
    answerReady: false,
    primaryBlockers: ['chat_readiness'],
    capabilityRows: [],
    safeActivationActions: [],
  }
}

export function summarizeChatReadiness(
  payload: ChatReadinessResponse | null | undefined,
  options: { isLoading?: boolean; error?: unknown } = {},
): ChatReadinessViewModel {
  if (options.isLoading && !payload) {
    return {
      ...fallbackBlockedModel('Checking chat evidence and runtime capabilities.'),
      tone: 'warning',
      headline: 'Checking answer readiness',
    }
  }

  if (options.error && !payload) {
    const message = options.error instanceof Error ? options.error.message : 'readiness endpoint unavailable'
    return fallbackBlockedModel(message)
  }

  if (!payload) {
    return fallbackBlockedModel('Readiness contract is unavailable.')
  }

  const capabilityRows = orderedCapabilities(payload.capabilities)
  const normalAnalysisAllowed = Boolean(
    payload.normalAnalysisAllowed ?? payload.normal_analysis_allowed ?? false,
  )
  const answerReady = Boolean(payload.answerReady ?? payload.answer_ready ?? false)
  const summary = payload.summary || {}
  const primaryBlockers = Array.isArray(summary.primaryBlockers)
    ? summary.primaryBlockers
    : (Array.isArray(summary.primary_blockers) ? summary.primary_blockers : [])
  const safeActivationActions = Array.isArray(summary.safeActivationActions)
    ? summary.safeActivationActions
    : (Array.isArray(summary.safe_activation_actions) ? summary.safe_activation_actions : [])
  const blockedRows = capabilityRows.filter((row) => !row.ready)
  const degradedRows = capabilityRows.filter((row) => row.status === 'DEGRADED')
  const tickerLabel = payload.ticker ? String(payload.ticker) : null

  if (normalAnalysisAllowed && answerReady) {
    return {
      shouldRender: false,
      tone: 'ready',
      headline: 'Normal analysis ready',
      detail: 'Core answer capabilities are available.',
      tickerLabel,
      normalAnalysisAllowed,
      answerReady,
      primaryBlockers: [],
      capabilityRows,
      safeActivationActions,
    }
  }

  const detailParts = []
  if (blockedRows.length > 0) {
    detailParts.push(`${blockedRows.length} capability blocker${blockedRows.length === 1 ? '' : 's'}`)
  }
  if (degradedRows.length > 0) {
    detailParts.push(`${degradedRows.length} degraded runtime path${degradedRows.length === 1 ? '' : 's'}`)
  }

  return {
    shouldRender: true,
    tone: degradedRows.length > 0 && blockedRows.length === 0 ? 'warning' : 'blocked',
    headline: normalAnalysisAllowed ? 'Answer readiness partial' : 'Normal analysis blocked',
    detail: detailParts.join(' / ') || 'Required answer capabilities are not ready.',
    tickerLabel,
    normalAnalysisAllowed,
    answerReady,
    primaryBlockers: primaryBlockers.map(String).filter(Boolean),
    capabilityRows,
    safeActivationActions: safeActivationActions.map(String).filter(Boolean),
  }
}
