import { describe, expect, it } from 'vitest'

import { shouldUseCompactChrome } from './cockpit-mobile-chrome'

describe('Cockpit compact chrome selection', () => {
  it('uses compact chrome for manual iPhone preview mode', () => {
    expect(shouldUseCompactChrome({ iphoneScale: true, isMobileViewport: false })).toBe(true)
  })

  it('uses compact chrome for narrow real viewports without iPhone preview mode', () => {
    expect(shouldUseCompactChrome({ iphoneScale: false, isMobileViewport: true })).toBe(true)
  })

  it('keeps desktop chrome for wide desktop viewports', () => {
    expect(shouldUseCompactChrome({ iphoneScale: false, isMobileViewport: false })).toBe(false)
  })
})
