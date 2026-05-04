import { describe, expect, it } from 'vitest'

import { applyApiDefaultOverride, isApiRoutedMessage } from './chat-routing'

describe('applyApiDefaultOverride', () => {
  it('prefixes plain messages with /cloud when enabled', () => {
    expect(applyApiDefaultOverride('show BHP news', true)).toBe('/cloud show BHP news')
  })

  it('does not change slash commands that are not routing prefixes', () => {
    expect(applyApiDefaultOverride('/watch add BHP', true)).toBe('/watch add BHP')
  })

  it('overrides explicit local routing prefixes when API default is enabled', () => {
    expect(applyApiDefaultOverride('/local summarize BHP', true)).toBe('/cloud summarize BHP')
    expect(applyApiDefaultOverride('/ops summarize BHP', true)).toBe('/cloud summarize BHP')
  })

  it('keeps explicit API routing prefixes intact', () => {
    expect(applyApiDefaultOverride('/cloud summarize BHP', true)).toBe('/cloud summarize BHP')
  })

  it('does nothing when api default override is disabled', () => {
    expect(applyApiDefaultOverride('show BHP news', false)).toBe('show BHP news')
  })
})

describe('isApiRoutedMessage', () => {
  it('recognizes API routing prefixes', () => {
    expect(isApiRoutedMessage('/cloud market update')).toBe(true)
    expect(isApiRoutedMessage('/advisor compare BHP')).toBe(true)
  })

  it('does not treat local or domain slash commands as API routes', () => {
    expect(isApiRoutedMessage('/local summarize BHP')).toBe(false)
    expect(isApiRoutedMessage('/market-update final')).toBe(false)
  })
})
