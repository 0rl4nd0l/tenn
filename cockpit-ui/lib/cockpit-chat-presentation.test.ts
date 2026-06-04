import { describe, expect, it } from 'vitest'

import type { ChatMessage } from './cockpit-types'
import {
  buildChatPresentationModel,
  deriveActionPreviewPresentation,
} from './cockpit-chat-presentation'

function buildAssistantMessage(overrides: Partial<ChatMessage> = {}): ChatMessage {
  return {
    id: 'msg-1',
    role: 'assistant',
    content: 'BHP answer.',
    timestamp: new Date('2026-04-20T10:00:00Z'),
    ...overrides,
  }
}

describe('cockpit chat presentation model', () => {
  it('keeps memory context with raw claim metadata context-only in the shell model', () => {
    const model = buildChatPresentationModel(
      buildAssistantMessage({
        metadata: {
          source: 'orchestrator',
          analyst: {
            ticker: 'BHP',
            entity: 'BHP',
            evidenceLabels: ['claim_verified', 'financial_truth', 'memory_context'],
            claimVerifiedSourceCount: 1,
            sourceCoverageStatus: 'claim_verified',
          },
        },
        sources: [
          {
            title: 'BHP company memory',
            score: 0.6,
            kind: 'context',
            docType: 'company_memory',
            sourceId: 'company_memory:BHP:margin',
            evidenceLabel: 'claim_verified',
            evidenceLabels: ['claim_verified', 'financial_truth', 'memory_context'],
            claimVerified: true,
          },
        ],
      }),
    )

    expect(model.shell.shouldRender).toBe(true)
    expect(model.shell.entityLabel).toBe('BHP')
    expect(model.shell.answerType).toBe('Context only')
    expect(model.shell.trustLabel).toBe('Context sources only')
    expect(model.shell.sourceSummaryLabel).toBe('Memory context')
    expect(model.shell.evidenceStateLabels).toContain('Memory context')
    expect(model.shell.evidenceStateLabels).not.toContain('Claim verified')
  })

  it('derives action preview risk and parameter display state without executing actions', () => {
    const action = deriveActionPreviewPresentation({
      id: 'create_thesis',
      name: 'Save thesis note',
      description: 'Save this thesis note after confirmation.',
      args: { ticker: 'BHP', thesis: 'BHP copper growth note' },
      requiresConfirmation: true,
      isMutating: true,
    })

    expect(action.riskLabels).toEqual([
      'Confirmation required',
      'Memory write',
    ])
    expect(action.whyLabel).toBe('Save this thesis note after confirmation.')
    expect(action.impactLabel).toBe('Run the named backend action with the parameters shown below.')
    expect(action.argsSummary).toBe('ticker=BHP, thesis=BHP copper growth note')
    expect(action.safetyLabel).toBe('No action runs until you confirm.')
  })
})
