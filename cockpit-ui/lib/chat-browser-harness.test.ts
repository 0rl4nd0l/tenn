import { describe, expect, it } from 'vitest'

import {
  buildParityReportMarkdown,
  createSseStream,
  sanitizeParityCell,
} from '../tests/chat-browser-harness'

describe('chat browser harness', () => {
  it('serializes chat SSE events in the same shape as the browser BFF stream', () => {
    const stream = createSseStream([
      ['sources', { items: [{ title: 'BHP source' }] }],
      ['done', { text: 'BHP answer.' }],
    ])

    expect(stream).toContain('data: {"type":"sources","data":{"items":[{"title":"BHP source"}]}}')
    expect(stream).toContain('data: {"type":"done","data":{"text":"BHP answer."}}')
    expect(stream.endsWith('event: end\ndata: {}\n\n')).toBe(true)
  })

  it('renders route parity markdown with escaped table cells', () => {
    const markdown = buildParityReportMarkdown({
      generatedAt: '2026-06-04T00:00:00.000Z',
      verificationTarget: 'http://localhost:3000',
      rows: [
        {
          route: '/',
          area: 'Chat | Shell',
          expected: 'Loads',
          observed: 'HTTP 200',
          status: 'PASS',
          notes: 'mocked   APIs',
        },
      ],
    })

    expect(sanitizeParityCell('Chat | Shell')).toBe('Chat \\| Shell')
    expect(markdown).toContain('Generated: 2026-06-04T00:00:00.000Z')
    expect(markdown).toContain('| / | Chat \\| Shell | Loads | HTTP 200 | PASS | mocked APIs |')
  })
})
