import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { CitationLink } from './citation-link'

describe('CitationLink', () => {
  it('builds the correct deep link with a rounded timestamp', () => {
    render(<CitationLink videoId="abc123" segmentStartSeconds={125.4} />)

    const link = screen.getByRole('link') as HTMLAnchorElement

    expect(link.href).toBe('https://youtu.be/abc123?t=125s')
    expect(link.textContent).toBe('▶ 2:05')
    expect(link.getAttribute('target')).toBe('_blank')
    expect(link.getAttribute('rel')).toBe('noreferrer noopener')
  })
})
