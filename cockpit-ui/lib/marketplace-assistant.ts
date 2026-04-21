'use client'

import { createChatSessionId } from './chat-session-store'
import type { MarketplaceBrowserHealth } from './marketplace-api'

export type MarketplaceAssistantSuggestedAction =
  | 'ask_followup'
  | 'confirm_create'
  | 'confirm_create_and_run'

export interface MarketplaceMissionDraft {
  status: 'collecting' | 'ready'
  missingFields: string[]
  name: string
  brief: string
  categoryHint: string | null
  hardFilters: {
    includeKeywords: string[]
    excludeKeywords: string[]
    locationNames: string[]
    priceMin: number | null
    priceMax: number | null
    radiusKm: number | null
    conditionRequired: string[]
    requiredTerms: string[]
    forbiddenTerms: string[]
  }
  softPreferences: {
    preferredBrands: string[]
    preferredSuburbs: string[]
    preferredConditionTerms: string[]
    niceToHaveTerms: string[]
    urgency: 'low' | 'normal' | 'high'
    priceAggressiveness: 'conservative' | 'balanced' | 'aggressive'
    negotiationExpected: boolean
  }
  searchConfig: {
    queryVariantsEnabled: boolean
    broadeningEnabled: boolean
    maxQueriesPerRun: number
  }
  scanConfig: {
    aggressiveAlerting: boolean
  }
}

export interface MarketplaceAssistantTranscriptMessage {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: string
}

type MarketplaceMissionDraftDelta = Partial<{
  name: string
  brief: string
  categoryHint: string | null
  hardFilters: Partial<MarketplaceMissionDraft['hardFilters']>
  softPreferences: Partial<MarketplaceMissionDraft['softPreferences']>
  searchConfig: Partial<MarketplaceMissionDraft['searchConfig']>
  scanConfig: Partial<MarketplaceMissionDraft['scanConfig']>
}>

export interface MarketplaceAssistantPayload {
  assistantMessage: string
  draftDelta: MarketplaceMissionDraftDelta
  missingFields: string[]
  readyToCreate: boolean
  suggestedAction: MarketplaceAssistantSuggestedAction
  rawAnswer: string
  source?: 'local' | 'anthropic'
  model?: string
}

interface MarketplaceAssistantApiRawResponse {
  content?: {
    answer?: string
    model?: string
    source?: 'local' | 'anthropic'
  }
  type?: string
  data?: {
    text?: string
    model?: string
    source?: 'local' | 'anthropic'
  }
}

interface SendMarketplaceAssistantTurnParams {
  apiKey: string
  browserHealth: MarketplaceBrowserHealth | null
  draft: MarketplaceMissionDraft
  homeLocation: string
  messages: MarketplaceAssistantTranscriptMessage[]
  model: string
  activeSource: 'local' | 'anthropic' | 'unknown'
  apiDefaultEnabled: boolean
  marketplacePreferCloudRouting: boolean
  webSearchEnabled: boolean
  sessionId: string
  userMessage: string
}

const SESSION_STORAGE_KEY = 'cockpit-marketplace-assistant-session-v1'

function cleanText(value: unknown): string {
  return String(value ?? '').trim()
}

function normalizeStringList(value: unknown): string[] {
  if (!Array.isArray(value)) return []
  const items: string[] = []
  const seen = new Set<string>()
  for (const entry of value) {
    const cleaned = cleanText(entry)
    if (!cleaned) continue
    const key = cleaned.toLowerCase()
    if (seen.has(key)) continue
    seen.add(key)
    items.push(cleaned)
  }
  return items
}

function normalizeNumber(value: unknown): number | null {
  if (value == null || value === '') return null
  const parsed = Number(value)
  if (!Number.isFinite(parsed)) return null
  return parsed
}

function normalizeBoolean(value: unknown, fallback: boolean): boolean {
  return typeof value === 'boolean' ? value : fallback
}

function normalizeUrgency(value: unknown): MarketplaceMissionDraft['softPreferences']['urgency'] | null {
  return value === 'low' || value === 'normal' || value === 'high' ? value : null
}

function normalizeAggressiveness(
  value: unknown,
): MarketplaceMissionDraft['softPreferences']['priceAggressiveness'] | null {
  return value === 'conservative' || value === 'balanced' || value === 'aggressive'
    ? value
    : null
}

function normalizeSuggestedAction(value: unknown): MarketplaceAssistantSuggestedAction {
  if (value === 'confirm_create' || value === 'confirm_create_and_run') {
    return value
  }
  return 'ask_followup'
}

function titleCaseWords(value: string): string {
  return value.replace(/\b([a-z])([a-z]*)\b/gi, (_match, first: string, rest: string) => {
    return `${first.toUpperCase()}${rest.toLowerCase()}`
  })
}

function normalizeLocationLabel(value: string): string {
  return titleCaseWords(
    value
      .replace(/[\\/|]+/g, ', ')
      .replace(/\s*,\s*/g, ', ')
      .replace(/\s+/g, ' ')
      .trim()
      .replace(/^[,.\- ]+|[,.\- ]+$/g, ''),
  )
}

function parseBudgetCap(text: string): number | null {
  const patterns = [
    /\bunder\s*\$?\s*(\d[\d,]*(?:\.\d+)?)\b/i,
    /\bup to\s*\$?\s*(\d[\d,]*(?:\.\d+)?)\b/i,
    /\bmax(?:imum)?\s*(?:budget|price)?\s*\$?\s*(\d[\d,]*(?:\.\d+)?)\b/i,
    /\bbudget(?:\s+is|\s+of)?\s*\$?\s*(\d[\d,]*(?:\.\d+)?)\b/i,
  ]

  for (const pattern of patterns) {
    const match = text.match(pattern)
    const candidate = match?.[1]?.replace(/,/g, '')
    if (!candidate) continue
    const parsed = Number(candidate)
    if (Number.isFinite(parsed)) {
      return parsed
    }
  }

  return null
}

function parsePreferredVramGb(text: string): number | null {
  const match = text.match(/\b(?:ideally|at least|minimum|with)?\s*(\d{1,2})\s*gb(?:\s+of)?\s*vram\b/i)
    ?? text.match(/\b(\d{1,2})\s*gb\b/i)
  const candidate = match?.[1]
  if (!candidate) return null
  const parsed = Number(candidate)
  return Number.isFinite(parsed) ? parsed : null
}

function parseExplicitLocation(text: string): string[] {
  const patterns = [
    /\blocation\s+(?:is|should be|to use is)\s+(.+)$/i,
    /(?:^|[.!?]\s*|,\s*)([a-z][a-z\s,\/-]{2,})\s+is\s+the\s+location\b/i,
    /\buse\s+(.+?)\s+for\s+the\s+search\b/i,
  ]

  for (const pattern of patterns) {
    const match = text.match(pattern)
    const candidate = cleanText(match?.[1])
    if (!candidate) continue
    const normalized = normalizeLocationLabel(candidate)
    return normalized ? [normalized] : []
  }

  return []
}

function parseGpuModelKeywords(text: string): string[] {
  const patterns = [
    /\b(?:rtx|gtx)\s*\d{3,4}(?:\s*ti)?\b/gi,
    /\b(?:rtx\s*a\d{3,4}|a\d{3,4})\b/gi,
  ]
  const matches: string[] = []
  for (const pattern of patterns) {
    for (const match of text.matchAll(pattern)) {
      matches.push(cleanText(match[0]).replace(/\s+/g, ' ').toUpperCase())
    }
  }
  return normalizeStringList(matches)
}

function inferMarketplaceDraftDeltaFromUserMessage(
  userMessage: string,
  currentDraft: MarketplaceMissionDraft,
  homeLocation: string,
): MarketplaceMissionDraftDelta {
  const text = cleanText(userMessage)
  if (!text) return {}

  const normalized = text.replace(/\s+/g, ' ')
  const lower = normalized.toLowerCase()
  const wantsGpu = /\b(gpu|graphics card|video card|rtx|gtx|nvidia)\b/i.test(normalized)
  const preferredVramGb = parsePreferredVramGb(normalized)
  const explicitLocations = parseExplicitLocation(normalized)
  const modelKeywords = parseGpuModelKeywords(normalized)
  const includeKeywords = normalizeStringList([
    ...currentDraft.hardFilters.includeKeywords,
    ...(wantsGpu ? ['GPU'] : []),
    ...modelKeywords,
    ...(preferredVramGb != null ? [`${preferredVramGb}GB VRAM`] : []),
  ])
  const priceMax = parseBudgetCap(normalized) ?? currentDraft.hardFilters.priceMax
  const locationNames = explicitLocations.length > 0
    ? explicitLocations
    : currentDraft.hardFilters.locationNames.length > 0
      ? currentDraft.hardFilters.locationNames
      : cleanText(homeLocation)
        ? [cleanText(homeLocation)]
        : []

  const delta: MarketplaceMissionDraftDelta = {}

  if (!cleanText(currentDraft.name)) {
    if (modelKeywords.length === 1) {
      delta.name = `${modelKeywords[0]} hunt`
    } else if (wantsGpu && preferredVramGb != null) {
      delta.name = `${preferredVramGb}GB GPU for local inference`
    } else if (wantsGpu) {
      delta.name = 'GPU hunt'
    }
  }

  if (!cleanText(currentDraft.brief) && wantsGpu) {
    const budgetText = priceMax != null ? ` under $${priceMax}` : ''
    const locationText = locationNames.length > 0 ? ` around ${locationNames.join(', ')}` : ''
    const vramText = preferredVramGb != null ? ` with ideally ${preferredVramGb}GB VRAM` : ''
    delta.brief = `Find a used GPU suitable for the Tenn local workstation${budgetText}${locationText}${vramText}.`
  }

  const hardFilters: NonNullable<MarketplaceMissionDraftDelta['hardFilters']> = {}
  if (includeKeywords.length > 0) {
    hardFilters.includeKeywords = includeKeywords
  }
  if (locationNames.length > 0) {
    hardFilters.locationNames = locationNames
  }
  if (priceMax != null) {
    hardFilters.priceMax = priceMax
  }
  if (Object.keys(hardFilters).length > 0) {
    delta.hardFilters = hardFilters
  }

  if (wantsGpu) {
    const niceToHaveTerms = normalizeStringList([
      ...currentDraft.softPreferences.niceToHaveTerms,
      ...(preferredVramGb != null ? [`${preferredVramGb}GB VRAM preferred`] : []),
      ...(lower.includes('good for our system') || lower.includes('good for the system')
        ? ['suitable for local inference workstation']
        : []),
    ])
    if (niceToHaveTerms.length > 0) {
      delta.softPreferences = {
        ...(delta.softPreferences ?? {}),
        niceToHaveTerms,
      }
    }
  }

  return delta
}

function looksLikeMarketplaceAssistantToolError(answer: string): boolean {
  const normalized = cleanText(answer).toLowerCase()
  if (!normalized) return false
  return (
    normalized.includes('web access is required') ||
    normalized.includes('enable web and try again') ||
    normalized.includes('fetch that url') ||
    normalized.includes('cannot access that url') ||
    normalized.includes('can’t access that url') ||
    normalized.includes('need web access') ||
    normalized.includes('need browsing')
  )
}

function buildMarketplaceAssistantFallbackReply(
  draft: MarketplaceMissionDraft,
): string {
  const questions: string[] = []
  const locations = draft.hardFilters.locationNames
  const hasExplicitGpuTarget = draft.hardFilters.includeKeywords.some((keyword) => {
    return /\b(?:rtx|gtx|a\d{3,4}|\d{1,2}gb vram)\b/i.test(keyword)
  })
  const preferredVram = draft.hardFilters.includeKeywords.find((keyword) => /\b\d{1,2}gb vram\b/i.test(keyword))

  if (draft.hardFilters.priceMax == null) {
    questions.push("What's your hard max budget?")
  }
  if (preferredVram) {
    questions.push(`Should I keep the hunt strict to ${preferredVram}, or include strong 16GB cards as backups?`)
  } else if (!hasExplicitGpuTarget) {
    questions.push('Do you want me to target specific GPU models, or keep it broad and optimise for VRAM per dollar?')
  }

  const intro = locations.length > 0
    ? `I’ll use ${locations.join(', ')} for the search.`
    : 'I can draft the mission now.'

  if (questions.length === 0) {
    return `${intro} I can turn that into a mission now, or tighten it further if you give me a budget cap and any model preferences.`
  }

  return `${intro} ${questions.slice(0, 2).join(' ')}`
}

function parseAssistantJson(answer: string): Record<string, unknown> | null {
  const trimmed = answer.trim()
  if (!trimmed) return null

  const candidates = [trimmed]
  const fencedMatch = trimmed.match(/```(?:json)?\s*([\s\S]*?)```/i)
  if (fencedMatch?.[1]) {
    candidates.push(fencedMatch[1].trim())
  }
  const firstBrace = trimmed.indexOf('{')
  const lastBrace = trimmed.lastIndexOf('}')
  if (firstBrace >= 0 && lastBrace > firstBrace) {
    candidates.push(trimmed.slice(firstBrace, lastBrace + 1))
  }

  for (const candidate of candidates) {
    try {
      const parsed = JSON.parse(candidate) as Record<string, unknown>
      if (parsed && typeof parsed === 'object') {
        return parsed
      }
    } catch {
      continue
    }
  }

  return null
}

function buildHeaders(apiKey: string): HeadersInit {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  }
  if (apiKey) {
    headers['X-API-Key'] = apiKey
  }
  return headers
}

function normalizeChatAnswer(raw: MarketplaceAssistantApiRawResponse): {
  answer: string
  source?: 'local' | 'anthropic'
  model?: string
} {
  if (
    raw
    && typeof raw === 'object'
    && raw.content
    && typeof raw.content.answer === 'string'
  ) {
    return {
      answer: raw.content.answer,
      source: raw.content.source,
      model: raw.content.model,
    }
  }

  if (
    raw
    && typeof raw === 'object'
    && raw.type === 'done'
    && raw.data
    && typeof raw.data.text === 'string'
  ) {
    return {
      answer: raw.data.text,
      source: raw.data.source,
      model: raw.data.model,
    }
  }

  return {
    answer: typeof raw === 'string' ? raw : JSON.stringify(raw),
  }
}

function parseAssistantPayload(answer: string): {
  assistantMessage: string
  draftDelta: MarketplaceMissionDraftDelta
  missingFields: string[]
  readyToCreate: boolean
  suggestedAction: MarketplaceAssistantSuggestedAction
} {
  const parsed = parseAssistantJson(answer)
  if (!parsed) {
    return {
      assistantMessage: answer.trim() || 'I could not parse that reply into a Marketplace draft yet.',
      draftDelta: {},
      missingFields: [],
      readyToCreate: false,
      suggestedAction: 'ask_followup',
    }
  }

  return {
    assistantMessage: cleanText(parsed.assistant_message) || answer.trim(),
    draftDelta:
      parsed.draft && typeof parsed.draft === 'object'
        ? (parsed.draft as MarketplaceMissionDraftDelta)
        : {},
    missingFields: normalizeStringList(parsed.missing_fields),
    readyToCreate: Boolean(parsed.ready_to_create),
    suggestedAction: normalizeSuggestedAction(parsed.suggested_action),
  }
}

function buildRoutePrefix(
  activeSource: 'local' | 'anthropic' | 'unknown',
  model: string,
  apiDefaultEnabled = false,
  marketplacePreferCloudRouting = false,
): '/local' | '/cloud' {
  if (apiDefaultEnabled || marketplacePreferCloudRouting) return '/cloud'
  if (activeSource === 'anthropic') return '/cloud'
  if (activeSource === 'local') return '/local'
  return /claude|anthropic/i.test(model) ? '/cloud' : '/local'
}

function summarizeBrowserHealth(browserHealth: MarketplaceBrowserHealth | null): Record<string, unknown> {
  if (!browserHealth) {
    return {
      status: 'unknown',
    }
  }

  return {
    status: browserHealth.status,
    loggedIn: browserHealth.logged_in,
    challengeDetected: browserHealth.challenge_detected,
    finalUrl: browserHealth.final_url ?? null,
  }
}

function buildPrompt(params: {
  browserHealth: MarketplaceBrowserHealth | null
  draft: MarketplaceMissionDraft
  homeLocation: string
  messages: MarketplaceAssistantTranscriptMessage[]
  userMessage: string
}): string {
  const transcript = params.messages.slice(-8).map((message) => ({
    role: message.role,
    content: message.content,
  }))

  return [
    'You are the Tenn Marketplace mission assistant.',
    'Your job is to turn the user conversation into a Marketplace mission draft only.',
    'Never claim live listing results, product facts, or external facts unless the user explicitly provided them.',
    'Do not say that a mission has been created or run. The UI handles real actions separately.',
    'Ask at most two concise follow-up questions when information is still missing.',
    'Return strict JSON only. No markdown fences. No prose outside the JSON object.',
    'Use this exact schema:',
    JSON.stringify(
      {
        assistant_message: 'Human-readable reply shown to the user.',
        draft: {
          name: 'optional string',
          brief: 'optional string',
          categoryHint: 'optional string or null',
          hardFilters: {
            includeKeywords: ['optional strings'],
            excludeKeywords: ['optional strings'],
            locationNames: ['optional strings'],
            priceMin: null,
            priceMax: null,
            radiusKm: null,
            conditionRequired: ['optional strings'],
            requiredTerms: ['optional strings'],
            forbiddenTerms: ['optional strings'],
          },
          softPreferences: {
            preferredBrands: ['optional strings'],
            preferredSuburbs: ['optional strings'],
            preferredConditionTerms: ['optional strings'],
            niceToHaveTerms: ['optional strings'],
            urgency: 'low | normal | high',
            priceAggressiveness: 'conservative | balanced | aggressive',
            negotiationExpected: false,
          },
          searchConfig: {
            queryVariantsEnabled: true,
            broadeningEnabled: true,
            maxQueriesPerRun: 6,
          },
          scanConfig: {
            aggressiveAlerting: false,
          },
        },
        missing_fields: ['name', 'brief', 'location'],
        ready_to_create: false,
        suggested_action: 'ask_followup',
      },
      null,
      2,
    ),
    `Saved home location: ${params.homeLocation || '(none saved)'}`,
    `Browser health: ${JSON.stringify(summarizeBrowserHealth(params.browserHealth))}`,
    `Current draft: ${JSON.stringify(params.draft, null, 2)}`,
    `Recent transcript: ${JSON.stringify(transcript, null, 2)}`,
    `Latest user message: ${params.userMessage}`,
    'Prefer the saved home location when the user did not override it.',
    'If the user asks to run, use suggested_action "confirm_create_and_run" only when the draft is ready.',
    'If the draft is ready but the user has not explicitly asked to run now, use suggested_action "confirm_create".',
  ].join('\n\n')
}

export function buildMarketplaceAssistantGreeting(homeLocation: string): string {
  if (cleanText(homeLocation)) {
    return `I know your default Marketplace location is ${cleanText(homeLocation)}. What are you hunting for, what budget do you have, and what deal-breakers matter most?`
  }
  return 'What are you hunting for, what budget do you have, and what location should I use for the search?'
}

export function createMarketplaceMissionDraft(homeLocation: string): MarketplaceMissionDraft {
  const normalizedHomeLocation = cleanText(homeLocation)
  const locationNames = normalizedHomeLocation ? [normalizedHomeLocation] : []

  return {
    status: locationNames.length > 0 ? 'collecting' : 'collecting',
    missingFields: normalizedHomeLocation ? ['name', 'brief'] : ['name', 'brief', 'location'],
    name: '',
    brief: '',
    categoryHint: null,
    hardFilters: {
      includeKeywords: [],
      excludeKeywords: [],
      locationNames,
      priceMin: null,
      priceMax: null,
      radiusKm: null,
      conditionRequired: [],
      requiredTerms: [],
      forbiddenTerms: [],
    },
    softPreferences: {
      preferredBrands: [],
      preferredSuburbs: [],
      preferredConditionTerms: [],
      niceToHaveTerms: [],
      urgency: 'normal',
      priceAggressiveness: 'balanced',
      negotiationExpected: false,
    },
    searchConfig: {
      queryVariantsEnabled: true,
      broadeningEnabled: true,
      maxQueriesPerRun: 6,
    },
    scanConfig: {
      aggressiveAlerting: false,
    },
  }
}

export function evaluateMarketplaceMissionDraft(draft: MarketplaceMissionDraft): {
  missingFields: string[]
  readyToCreate: boolean
} {
  const missingFields: string[] = []
  if (!cleanText(draft.name)) missingFields.push('name')
  if (!cleanText(draft.brief)) missingFields.push('brief')
  if ((draft.hardFilters.locationNames || []).length === 0) missingFields.push('location')
  return {
    missingFields,
    readyToCreate: missingFields.length === 0,
  }
}

export function mergeMarketplaceMissionDraft(
  currentDraft: MarketplaceMissionDraft,
  delta: MarketplaceMissionDraftDelta,
  options?: { homeLocation?: string; modelMissingFields?: string[]; modelReadyToCreate?: boolean },
): MarketplaceMissionDraft {
  const nextDraft: MarketplaceMissionDraft = {
    ...currentDraft,
    hardFilters: { ...currentDraft.hardFilters },
    softPreferences: { ...currentDraft.softPreferences },
    searchConfig: { ...currentDraft.searchConfig },
    scanConfig: { ...currentDraft.scanConfig },
  }

  if ('name' in delta) {
    nextDraft.name = cleanText(delta.name)
  }
  if ('brief' in delta) {
    nextDraft.brief = cleanText(delta.brief)
  }
  if ('categoryHint' in delta) {
    nextDraft.categoryHint = delta.categoryHint == null ? null : cleanText(delta.categoryHint)
  }

  if (delta.hardFilters && typeof delta.hardFilters === 'object') {
    const hard = delta.hardFilters
    if ('includeKeywords' in hard) nextDraft.hardFilters.includeKeywords = normalizeStringList(hard.includeKeywords)
    if ('excludeKeywords' in hard) nextDraft.hardFilters.excludeKeywords = normalizeStringList(hard.excludeKeywords)
    if ('locationNames' in hard) nextDraft.hardFilters.locationNames = normalizeStringList(hard.locationNames)
    if ('conditionRequired' in hard) nextDraft.hardFilters.conditionRequired = normalizeStringList(hard.conditionRequired)
    if ('requiredTerms' in hard) nextDraft.hardFilters.requiredTerms = normalizeStringList(hard.requiredTerms)
    if ('forbiddenTerms' in hard) nextDraft.hardFilters.forbiddenTerms = normalizeStringList(hard.forbiddenTerms)
    if ('priceMin' in hard) nextDraft.hardFilters.priceMin = normalizeNumber(hard.priceMin)
    if ('priceMax' in hard) nextDraft.hardFilters.priceMax = normalizeNumber(hard.priceMax)
    if ('radiusKm' in hard) nextDraft.hardFilters.radiusKm = normalizeNumber(hard.radiusKm)
  }

  if (delta.softPreferences && typeof delta.softPreferences === 'object') {
    const soft = delta.softPreferences
    if ('preferredBrands' in soft) nextDraft.softPreferences.preferredBrands = normalizeStringList(soft.preferredBrands)
    if ('preferredSuburbs' in soft) nextDraft.softPreferences.preferredSuburbs = normalizeStringList(soft.preferredSuburbs)
    if ('preferredConditionTerms' in soft) {
      nextDraft.softPreferences.preferredConditionTerms = normalizeStringList(soft.preferredConditionTerms)
    }
    if ('niceToHaveTerms' in soft) nextDraft.softPreferences.niceToHaveTerms = normalizeStringList(soft.niceToHaveTerms)
    if ('urgency' in soft) {
      nextDraft.softPreferences.urgency = normalizeUrgency(soft.urgency) ?? nextDraft.softPreferences.urgency
    }
    if ('priceAggressiveness' in soft) {
      nextDraft.softPreferences.priceAggressiveness =
        normalizeAggressiveness(soft.priceAggressiveness) ?? nextDraft.softPreferences.priceAggressiveness
    }
    if ('negotiationExpected' in soft) {
      nextDraft.softPreferences.negotiationExpected = normalizeBoolean(
        soft.negotiationExpected,
        nextDraft.softPreferences.negotiationExpected,
      )
    }
  }

  if (delta.searchConfig && typeof delta.searchConfig === 'object') {
    const search = delta.searchConfig
    if ('queryVariantsEnabled' in search) {
      nextDraft.searchConfig.queryVariantsEnabled = normalizeBoolean(
        search.queryVariantsEnabled,
        nextDraft.searchConfig.queryVariantsEnabled,
      )
    }
    if ('broadeningEnabled' in search) {
      nextDraft.searchConfig.broadeningEnabled = normalizeBoolean(
        search.broadeningEnabled,
        nextDraft.searchConfig.broadeningEnabled,
      )
    }
    if ('maxQueriesPerRun' in search) {
      nextDraft.searchConfig.maxQueriesPerRun =
        normalizeNumber(search.maxQueriesPerRun) ?? nextDraft.searchConfig.maxQueriesPerRun
    }
  }

  if (delta.scanConfig && typeof delta.scanConfig === 'object') {
    const scan = delta.scanConfig
    if ('aggressiveAlerting' in scan) {
      nextDraft.scanConfig.aggressiveAlerting = normalizeBoolean(
        scan.aggressiveAlerting,
        nextDraft.scanConfig.aggressiveAlerting,
      )
    }
  }

  if (
    nextDraft.hardFilters.locationNames.length === 0
    && cleanText(options?.homeLocation)
  ) {
    nextDraft.hardFilters.locationNames = [cleanText(options?.homeLocation)]
  }

  const evaluated = evaluateMarketplaceMissionDraft(nextDraft)
  const mergedMissing = new Set<string>([
    ...evaluated.missingFields,
    ...(options?.modelMissingFields ?? []),
  ])

  nextDraft.missingFields = Array.from(mergedMissing)
  nextDraft.status =
    evaluated.readyToCreate && options?.modelReadyToCreate !== false ? 'ready' : 'collecting'

  return nextDraft
}

export function mapMarketplaceDraftToMissionPayload(draft: MarketplaceMissionDraft): Record<string, unknown> {
  return {
    name: draft.name,
    brief: draft.brief,
    category_hint: draft.categoryHint,
    status: 'paused',
    hard_filters: {
      include_keywords: draft.hardFilters.includeKeywords,
      exclude_keywords: draft.hardFilters.excludeKeywords,
      location_names: draft.hardFilters.locationNames,
      price_min: draft.hardFilters.priceMin,
      price_max: draft.hardFilters.priceMax,
      radius_km: draft.hardFilters.radiusKm,
      condition_required: draft.hardFilters.conditionRequired,
      required_terms: draft.hardFilters.requiredTerms,
      forbidden_terms: draft.hardFilters.forbiddenTerms,
    },
    soft_preferences: {
      preferred_brands: draft.softPreferences.preferredBrands,
      preferred_suburbs: draft.softPreferences.preferredSuburbs,
      preferred_condition_terms: draft.softPreferences.preferredConditionTerms,
      nice_to_have_terms: draft.softPreferences.niceToHaveTerms,
      urgency: draft.softPreferences.urgency,
      price_aggressiveness: draft.softPreferences.priceAggressiveness,
      negotiation_expected: draft.softPreferences.negotiationExpected,
    },
    search_config: {
      query_variants_enabled: draft.searchConfig.queryVariantsEnabled,
      broadening_enabled: draft.searchConfig.broadeningEnabled,
      max_queries_per_run: draft.searchConfig.maxQueriesPerRun,
    },
    scan_config: {
      aggressive_alerting: draft.scanConfig.aggressiveAlerting,
    },
  }
}

export function getMarketplaceAssistantSessionId(): string {
  if (typeof window === 'undefined') {
    return createChatSessionId()
  }

  const existing = window.sessionStorage.getItem(SESSION_STORAGE_KEY)
  if (existing && existing.trim()) {
    return existing
  }

  const nextId = createChatSessionId()
  window.sessionStorage.setItem(SESSION_STORAGE_KEY, nextId)
  return nextId
}

export function createTranscriptMessage(
  role: MarketplaceAssistantTranscriptMessage['role'],
  content: string,
): MarketplaceAssistantTranscriptMessage {
  return {
    id: createChatSessionId(),
    role,
    content,
    timestamp: new Date().toISOString(),
  }
}

export async function sendMarketplaceAssistantTurn(
  params: SendMarketplaceAssistantTurnParams,
): Promise<MarketplaceAssistantPayload> {
  const routePrefix = buildRoutePrefix(
    params.activeSource,
    params.model,
    params.apiDefaultEnabled,
    params.marketplacePreferCloudRouting,
  )
  const prompt = buildPrompt({
    browserHealth: params.browserHealth,
    draft: params.draft,
    homeLocation: params.homeLocation,
    messages: params.messages,
    userMessage: params.userMessage,
  })

  const response = await fetch('/api/cockpit/chat', {
    method: 'POST',
    headers: buildHeaders(params.apiKey),
    body: JSON.stringify({
      message: `${routePrefix} ${prompt}`,
      mode: 'marketplace',
      session_id: params.sessionId,
      model: params.model || undefined,
      web_search: params.webSearchEnabled,
      rag: false,
      db_diagnostics: false,
      stream: false,
    }),
  })

  if (!response.ok) {
    let detail = `${response.status}`
    const rawBody = await response.text()
    if (rawBody) {
      try {
        const body = JSON.parse(rawBody) as { detail?: string }
        if (cleanText(body?.detail)) {
          detail = cleanText(body.detail)
        } else {
          detail = rawBody
        }
      } catch {
        detail = rawBody
      }
    }
    throw new Error(detail || 'Marketplace assistant request failed')
  }

  const raw = (await response.json()) as MarketplaceAssistantApiRawResponse
  const normalized = normalizeChatAnswer(raw)
  const heuristicDraftDelta = inferMarketplaceDraftDeltaFromUserMessage(
    params.userMessage,
    params.draft,
    params.homeLocation,
  )
  const parsed = parseAssistantPayload(normalized.answer)
  const shouldUseHeuristicFallback = (
    Object.keys(heuristicDraftDelta).length > 0
    && (
      !parseAssistantJson(normalized.answer)
      || looksLikeMarketplaceAssistantToolError(normalized.answer)
    )
  )

  if (shouldUseHeuristicFallback) {
    const nextDraft = mergeMarketplaceMissionDraft(params.draft, heuristicDraftDelta, {
      homeLocation: params.homeLocation,
    })
    const evaluated = evaluateMarketplaceMissionDraft(nextDraft)
    return {
      assistantMessage: buildMarketplaceAssistantFallbackReply(nextDraft),
      draftDelta: heuristicDraftDelta,
      missingFields: evaluated.missingFields,
      readyToCreate: evaluated.readyToCreate,
      suggestedAction: evaluated.readyToCreate ? 'confirm_create' : 'ask_followup',
      rawAnswer: normalized.answer,
      source: normalized.source,
      model: normalized.model,
    }
  }

  return {
    ...parsed,
    rawAnswer: normalized.answer,
    source: normalized.source,
    model: normalized.model,
  }
}

export function resolveMarketplaceAssistantRoutePrefix(
  activeSource: 'local' | 'anthropic' | 'unknown',
  model: string,
  apiDefaultEnabled = false,
  marketplacePreferCloudRouting = false,
): '/local' | '/cloud' {
  return buildRoutePrefix(
    activeSource,
    model,
    apiDefaultEnabled,
    marketplacePreferCloudRouting,
  )
}
