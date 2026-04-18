import { describe, expect, it } from 'vitest'

import {
  parseMarketplaceCaptureError,
  shouldOfferMarketplaceBrowserLaunch,
} from './marketplace-bootstrap'

describe('marketplace-bootstrap', () => {
  it('parses browser-unavailable errors from JSON responses', () => {
    expect(
      parseMarketplaceCaptureError(
        JSON.stringify({
          detail:
            'marketplace_browser_unavailable: Could not connect to a local Brave/Chrome debugging session.',
        }),
        503,
      ),
    ).toEqual({
      kind: 'browser_unavailable',
      message: 'Could not connect to a local Brave/Chrome debugging session.',
    })
  })

  it('parses login-required errors from plain text responses', () => {
    expect(
      parseMarketplaceCaptureError(
        'marketplace_login_required: The browser session is not logged into Facebook Marketplace.',
        409,
      ),
    ).toEqual({
      kind: 'login_required',
      message: 'The browser session is not logged into Facebook Marketplace.',
    })
  })

  it('offers the launcher only for browser/login setup failures', () => {
    expect(shouldOfferMarketplaceBrowserLaunch('browser_unavailable')).toBe(true)
    expect(shouldOfferMarketplaceBrowserLaunch('login_required')).toBe(true)
    expect(shouldOfferMarketplaceBrowserLaunch('other')).toBe(false)
  })
})
