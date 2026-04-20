import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

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
    expect(screen.getByText('[query_ticker_data: 87ms]')).toBeInTheDocument()
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
})
