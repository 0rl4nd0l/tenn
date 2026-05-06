import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import type { ChatMessage } from '@/lib/cockpit-types'

import { TerminalMessage } from './terminal-message'

function buildAssistantMessage(overrides: Partial<ChatMessage> = {}): ChatMessage {
  return {
    id: 'msg-1',
    role: 'assistant',
    content: 'Latency should be visible.',
    timestamp: new Date('2026-04-20T10:00:00Z'),
    ...overrides,
  }
}

describe('TerminalMessage', () => {
  it('renders a visible response timing badge alongside tool timings', () => {
    render(
      <TerminalMessage
        message={buildAssistantMessage({
          metadata: {
            latencyMs: 1425,
            model: 'local-model',
            costUsd: 0,
            source: 'local',
          },
          toolTraces: [
            { tool: 'query_ticker_data', durationMs: 87, status: 'success' },
          ],
        })}
      />,
    )

    expect(screen.getByText('[response: 1.4s]')).toBeInTheDocument()
    expect(screen.getByText('source:local')).toBeInTheDocument()
    expect(screen.getByText('local-model')).toBeInTheDocument()
    expect(screen.getByText('[query_ticker_data: 87ms]')).toBeInTheDocument()
  })

  it('shows API source and model separately in the response footer', () => {
    render(
      <TerminalMessage
        message={buildAssistantMessage({
          metadata: {
            latencyMs: 812,
            model: 'claude-sonnet-4-20250514',
            costUsd: 0.0021,
            source: 'api',
          },
        })}
      />,
    )

    expect(screen.getByText('source:api')).toBeInTheDocument()
    expect(screen.getByText('claude-sonnet-4-20250514')).toBeInTheDocument()
  })

  it('keeps the response timing visible when latency is zero', () => {
    render(
      <TerminalMessage
        message={buildAssistantMessage({
          metadata: {
            latencyMs: 0,
            costUsd: 0,
            source: 'local',
          },
        })}
      />,
    )

    expect(screen.getByText('[response: 0ms]')).toBeInTheDocument()
  })

  it('renders evidence-bound analyst metadata with source access', async () => {
    const user = userEvent.setup()
    render(
      <TerminalMessage
        showSources={false}
        message={buildAssistantMessage({
          content: 'BHP answer.',
          metadata: {
            source: 'orchestrator',
            analyst: {
              ticker: 'BHP',
              entity: 'BHP',
              intent: 'financial_interpretation',
              sourcePlan: ['financial_truth'],
              sufficientForAnalysis: true,
              evidenceLabels: ['claim_verified', 'financial_truth'],
              claimVerifiedSourceCount: 1,
              sourceCoverageStatus: 'claim_verified',
            },
          },
          sources: [
            {
              title: 'BHP FY25 annual report',
              score: 0.92,
              kind: 'document',
              publishedAt: '2025-08-19T00:00:00Z',
              evidenceLabel: 'claim_verified',
              evidenceLabels: ['claim_verified', 'financial_truth'],
              claimVerified: true,
            },
          ],
        })}
      />,
    )

    expect(screen.getByText('Entity: BHP')).toBeInTheDocument()
    expect(screen.getByText('Evidence-bound')).toBeInTheDocument()
    expect(screen.getByText(/Claim-supported/)).toBeInTheDocument()
    expect(screen.getByText('Sources: 1')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /review evidence/i }))
    expect(screen.getByText('BHP FY25 annual report')).toBeInTheDocument()
  })

  it('surfaces missing-data gaps near the top of the answer', () => {
    render(
      <TerminalMessage
        message={buildAssistantMessage({
          content: 'Final verdict: abstain until blocking evidence gaps are resolved.',
          metadata: {
            source: 'orchestrator',
            analyst: {
              ticker: 'MIN',
              entity: 'MIN',
              missingCategories: ['financials', 'market_context'],
              sufficientForAnalysis: false,
            },
          },
        })}
      />,
    )

    expect(screen.getByText('Partial evidence')).toBeInTheDocument()
    expect(screen.getByText('Missing data / gaps')).toBeInTheDocument()
    expect(screen.getByText('financials')).toBeInTheDocument()
    expect(screen.getByText('market_context')).toBeInTheDocument()
  })

  it('does not call no-hit audit sources source-backed', () => {
    render(
      <TerminalMessage
        showSources={false}
        message={buildAssistantMessage({
          content: 'No news results were returned for A2M.',
          metadata: {
            source: 'local',
            analyst: {
              evidenceLabels: ['no_hit', 'operational_trace'],
              claimVerifiedSourceCount: 0,
              sourceCoverageStatus: 'no_hit',
            },
          },
          sources: [
            {
              title: 'News search: no hits for A2M recall',
              score: 1,
              kind: 'context',
              docType: 'operational_no_hit',
              evidenceLabel: 'no_hit',
              evidenceLabels: ['no_hit', 'operational_trace'],
              claimVerified: false,
            },
          ],
        })}
      />,
    )

    expect(screen.getByText(/No-hit audit/)).toBeInTheDocument()
    expect(screen.queryByText('Source-backed')).not.toBeInTheDocument()
  })

  it('renders action proposals as confirmation-gated and does not auto-run', async () => {
    const user = userEvent.setup()
    const onConfirm = vi.fn()
    const onCancel = vi.fn()
    render(
      <TerminalMessage
        message={buildAssistantMessage({
          content: 'Action ready: run analysis.',
          actionPreview: {
            id: 'run_analysis',
            name: 'Run company analysis',
            description: 'The answer needs a fuller company analysis.',
            args: { ticker: 'BHP' },
            requiresConfirmation: true,
          },
        })}
        onConfirmAction={onConfirm}
        onCancelAction={onCancel}
      />,
    )

    expect(screen.getAllByText('Confirmation required').length).toBeGreaterThan(0)
    expect(screen.getByText('No action runs until you confirm.')).toBeInTheDocument()
    expect(onConfirm).not.toHaveBeenCalled()
    expect(onCancel).not.toHaveBeenCalled()

    await user.click(screen.getByRole('button', { name: 'Cancel' }))
    expect(onCancel).toHaveBeenCalledTimes(1)
    expect(onConfirm).not.toHaveBeenCalled()
  })

  it('renders thesis-note proposals without treating NOTE as the ticker', () => {
    render(
      <TerminalMessage
        message={buildAssistantMessage({
          content: 'Thesis note proposal ready.',
          actionPreview: {
            id: 'create_thesis',
            name: 'Save thesis note',
            description: 'Save this thesis note after confirmation.',
            args: { ticker: 'BHP', thesis: 'BHP copper growth note' },
            requiresConfirmation: true,
            isMutating: true,
          },
        })}
      />,
    )

    expect(screen.getByText('Entity: BHP')).toBeInTheDocument()
    expect(screen.queryByText('Entity: NOTE')).not.toBeInTheDocument()
    expect(screen.getByText('Memory write')).toBeInTheDocument()
  })

  it('renders diagnostic handoff controls without raw Codex command or prompt text', () => {
    render(
      <TerminalMessage
        message={{
          id: 'sys-1',
          role: 'system',
          content: [
            'Potential issue detected.',
            '',
            'Report id: `auto_1`',
            'Draft repair prompt: `reports/cockpit/flagged_sessions/auto_1/codex_prompt.md`',
            'View diagnostic: `/api/cockpit/feedback/flags/auto_1`',
          ].join('\n'),
          timestamp: new Date('2026-04-20T10:00:00Z'),
          metadata: {
            source: 'cockpit',
            codexDeploy: {
              reportId: 'auto_1',
              promptPath: 'reports/cockpit/flagged_sessions/auto_1/codex_prompt.md',
              readApiPath: '/api/cockpit/feedback/flags/auto_1',
            },
          },
        }}
        onDeployCodexFlag={vi.fn()}
      />,
    )

    expect(screen.getAllByText('Potential issue detected').length).toBeGreaterThan(0)
    expect(screen.getByText('Draft repair prompt')).toBeInTheDocument()
    expect(screen.queryByText(/codex exec/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/CODEX PROMPT/i)).not.toBeInTheDocument()
  })

  it('keeps plain conversational answers lightweight', () => {
    render(
      <TerminalMessage
        message={buildAssistantMessage({
          content: 'Sure, I can help narrow that down.',
        })}
      />,
    )

    expect(screen.getByText('Sure, I can help narrow that down.')).toBeInTheDocument()
    expect(screen.queryByText(/Sources:/)).not.toBeInTheDocument()
    expect(screen.queryByText(/Trust:/)).not.toBeInTheDocument()
  })
})
