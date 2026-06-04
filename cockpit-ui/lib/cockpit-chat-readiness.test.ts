import { describe, expect, it } from 'vitest'

import type { ChatReadinessResponse } from './cockpit-types'
import { summarizeChatReadiness } from './cockpit-chat-readiness'

function blockedPayload(): ChatReadinessResponse {
  return {
    schema_version: 1,
    ticker: 'BHP',
    answer_ready: false,
    normal_analysis_allowed: false,
    capabilities: {
      financial_fact: {
        id: 'financial_fact',
        label: 'Financial facts',
        status: 'DATA_MISSING',
        ready: false,
        blockers: ['asx_periodic_financials table unavailable'],
      },
      filing_document_summary: {
        id: 'filing_document_summary',
        label: 'Filing and document summaries',
        status: 'DATA_MISSING',
        ready: false,
        blockers: ['no filings/documents for requested ticker'],
      },
      model_route_runtime: {
        id: 'model_route_runtime',
        label: 'Model route and runtime',
        status: 'DEGRADED',
        ready: false,
        blockers: ['connection refused'],
      },
    },
    summary: {
      primary_blockers: ['financial_fact', 'filing_document_summary'],
      safe_activation_actions: [
        'Run reviewed metric extraction for the ticker before numeric financial questions.',
      ],
    },
  }
}

describe('cockpit chat readiness summary', () => {
  it('keeps normal analysis blocked when core capabilities are missing', () => {
    const model = summarizeChatReadiness(blockedPayload())

    expect(model.shouldRender).toBe(true)
    expect(model.headline).toBe('Normal analysis blocked')
    expect(model.tone).toBe('blocked')
    expect(model.tickerLabel).toBe('BHP')
    expect(model.normalAnalysisAllowed).toBe(false)
    expect(model.primaryBlockers).toEqual(['financial_fact', 'filing_document_summary'])
    expect(model.capabilityRows[0]).toMatchObject({
      id: 'financial_fact',
      label: 'Financial facts',
      ready: false,
      status: 'DATA_MISSING',
    })
    expect(model.safeActivationActions).toHaveLength(1)
  })

  it('hides the panel when core analysis is ready', () => {
    const ready = blockedPayload()
    ready.answer_ready = true
    ready.normal_analysis_allowed = true
    ready.capabilities = Object.fromEntries(
      Object.entries(ready.capabilities).map(([id, capability]) => [
        id,
        { ...capability, status: 'READY', ready: true, blockers: [] },
      ]),
    ) as ChatReadinessResponse['capabilities']
    ready.summary = { primary_blockers: [], safe_activation_actions: [] }

    const model = summarizeChatReadiness(ready)

    expect(model.shouldRender).toBe(false)
    expect(model.headline).toBe('Normal analysis ready')
    expect(model.normalAnalysisAllowed).toBe(true)
  })

  it('fails closed when the readiness payload is absent', () => {
    const model = summarizeChatReadiness(null)

    expect(model.shouldRender).toBe(true)
    expect(model.tone).toBe('blocked')
    expect(model.normalAnalysisAllowed).toBe(false)
    expect(model.detail).toMatch(/unavailable/i)
  })
})
