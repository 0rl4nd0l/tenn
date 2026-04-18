import { describe, expect, it } from 'vitest'

import { extractMarketplaceUrl, isMarketplaceUrl } from './marketplace-url'

describe('marketplace-url', () => {
  it('detects Facebook Marketplace item URLs', () => {
    expect(isMarketplaceUrl('https://www.facebook.com/marketplace/item/1234567890')).toBe(true)
    expect(isMarketplaceUrl('https://m.facebook.com/marketplace/item/1234567890/?ref=search')).toBe(true)
  })

  it('rejects non-marketplace URLs', () => {
    expect(isMarketplaceUrl('https://facebook.com/groups/123')).toBe(false)
    expect(isMarketplaceUrl('not a url')).toBe(false)
  })

  it('extracts the first Marketplace URL from text', () => {
    expect(
      extractMarketplaceUrl(
        'check this https://www.facebook.com/marketplace/item/1234567890?ref=search now',
      ),
    ).toBe('https://www.facebook.com/marketplace/item/1234567890?ref=search')
  })

  it('returns null when no Marketplace URL exists', () => {
    expect(extractMarketplaceUrl('plain text')).toBeNull()
  })
})
