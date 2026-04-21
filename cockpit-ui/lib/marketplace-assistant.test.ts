import { describe, expect, it } from 'vitest'

import {
  createMarketplaceMissionDraft,
  mapMarketplaceDraftToMissionPayload,
  mergeMarketplaceMissionDraft,
  resolveMarketplaceAssistantRoutePrefix,
} from './marketplace-assistant'

describe('marketplace-assistant helpers', () => {
  it('defaults the route prefix to cloud for anthropic activity or claude models', () => {
    expect(resolveMarketplaceAssistantRoutePrefix('anthropic', 'model:any')).toBe('/cloud')
    expect(resolveMarketplaceAssistantRoutePrefix('unknown', 'claude-3-7-sonnet')).toBe('/cloud')
    expect(resolveMarketplaceAssistantRoutePrefix('local', 'claude-3-7-sonnet')).toBe('/local')
  })

  it('merges a structured assistant delta and preserves the saved home location', () => {
    const base = createMarketplaceMissionDraft('Melbourne')
    const merged = mergeMarketplaceMissionDraft(
      base,
      {
        name: 'GPU hunt',
        brief: 'Find an RTX 3090 under $900 with clean condition.',
        hardFilters: {
          includeKeywords: ['RTX 3090', '24GB'],
          priceMax: 900,
        },
      },
      {
        homeLocation: 'Melbourne',
        modelMissingFields: [],
        modelReadyToCreate: true,
      },
    )

    expect(merged.name).toBe('GPU hunt')
    expect(merged.hardFilters.locationNames).toEqual(['Melbourne'])
    expect(merged.hardFilters.includeKeywords).toEqual(['RTX 3090', '24GB'])
    expect(merged.status).toBe('ready')
  })

  it('maps the draft into a paused Marketplace mission payload', () => {
    const draft = mergeMarketplaceMissionDraft(
      createMarketplaceMissionDraft('Melbourne'),
      {
        name: 'Camera hunt',
        brief: 'Find a Sony A7III body under $1500 around Melbourne.',
        hardFilters: {
          includeKeywords: ['Sony A7III'],
          priceMax: 1500,
        },
      },
      {
        homeLocation: 'Melbourne',
        modelMissingFields: [],
        modelReadyToCreate: true,
      },
    )

    expect(mapMarketplaceDraftToMissionPayload(draft)).toEqual(
      expect.objectContaining({
        name: 'Camera hunt',
        status: 'paused',
        hard_filters: expect.objectContaining({
          include_keywords: ['Sony A7III'],
          location_names: ['Melbourne'],
          price_max: 1500,
        }),
        scan_config: {
          aggressive_alerting: false,
        },
      }),
    )
  })
})
