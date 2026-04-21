import { describe, expect, it } from 'vitest'

import { applyApiDefaultOverride } from './chat-routing'

describe('applyApiDefaultOverride', () => {
  it('prefixes plain messages with /cloud when enabled', () => {
    expect(applyApiDefaultOverride('show BHP news', true)).toBe('/cloud show BHP news')
  })

  it('does not change slash commands that are not routing prefixes', () => {
    expect(applyApiDefaultOverride('/watch add BHP', true)).toBe('/watch add BHP')
  })

  it('keeps explicit backend routing prefixes intact', () => {
    expect(applyApiDefaultOverride('/local summarize BHP', true)).toBe('/local summarize BHP')
    expect(applyApiDefaultOverride('/cloud summarize BHP', true)).toBe('/cloud summarize BHP')
  })

  it('does nothing when api default override is disabled', () => {
    expect(applyApiDefaultOverride('show BHP news', false)).toBe('show BHP news')
  })
})
