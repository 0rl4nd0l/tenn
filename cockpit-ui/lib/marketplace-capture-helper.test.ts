import { describe, expect, it } from 'vitest'

import {
  MARKETPLACE_CAPTURE_CHANNEL,
  buildMarketplaceCaptureBookmarklet,
  buildMarketplaceCaptureScript,
  isMarketplaceCaptureRelayResponse,
} from './marketplace-capture-helper'

describe('marketplace-capture-helper', () => {
  it('builds bookmarklet script with relay token and submit URL', () => {
    const script = buildMarketplaceCaptureScript({
      submitUrl: 'http://localhost:3000/api/cockpit/commentary/marketplace-capture/submit',
      token: 'token-123',
    })

    expect(script).toContain('token-123')
    expect(script).toContain('/api/cockpit/commentary/marketplace-capture/submit')
    expect(script).toContain('Marketplace item page')
  })

  it('builds a javascript bookmarklet URL', () => {
    const bookmarklet = buildMarketplaceCaptureBookmarklet({
      submitUrl: 'http://localhost:3000/api/cockpit/commentary/marketplace-capture/submit',
      token: 'token-123',
    })

    expect(bookmarklet.startsWith('javascript:')).toBe(true)
    expect(decodeURIComponent(bookmarklet.slice('javascript:'.length))).toContain('token-123')
  })

  it('recognizes relay channel payloads', () => {
    expect(
      isMarketplaceCaptureRelayResponse({
        ok: true,
        ingest: { source_id: 'market_commentary:test:123' },
      }),
    ).toBe(true)
    expect(
      isMarketplaceCaptureRelayResponse({
        ok: false,
        message: 'token expired',
      }),
    ).toBe(true)
    expect(isMarketplaceCaptureRelayResponse({ nope: true })).toBe(false)
    expect(MARKETPLACE_CAPTURE_CHANNEL).toBe('cockpit-marketplace-capture')
  })
})
