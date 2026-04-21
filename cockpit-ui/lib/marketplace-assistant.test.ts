import { beforeEach, describe, expect, it, vi } from 'vitest'

import {
  buildMarketplaceAssistantGreeting,
  createTranscriptMessage,
  createMarketplaceMissionDraft,
  mapMarketplaceDraftToMissionPayload,
  mergeMarketplaceMissionDraft,
  resolveMarketplaceAssistantRoutePrefix,
  sendMarketplaceAssistantTurn,
} from './marketplace-assistant'

describe('marketplace-assistant helpers', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

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

  it('falls back to local parsing when the model returns a web-access error instead of JSON', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        content: {
          answer: 'Web access is required to fetch that URL. Enable web and try again.',
          model: 'model:qwen-test',
          source: 'local',
        },
      }),
    })

    vi.stubGlobal('fetch', fetchMock)

    const response = await sendMarketplaceAssistantTurn({
      apiKey: '',
      browserHealth: null,
      draft: createMarketplaceMissionDraft('Melbourne'),
      homeLocation: 'Melbourne',
      messages: [
        createTranscriptMessage('assistant', buildMarketplaceAssistantGreeting('Melbourne')),
        createTranscriptMessage(
          'user',
          'I want to buy a GPU that is good for our system, ideally 24GB of VRAM. Eaglemont/Victoriua is the location.',
        ),
      ],
      model: 'model:qwen-test',
      activeSource: 'local',
      webSearchEnabled: true,
      sessionId: 'session-1',
      userMessage:
        'I want to buy a GPU that is good for our system, ideally 24GB of VRAM. Eaglemont/Victoriua is the location.',
    })

    expect(response.assistantMessage).not.toContain('Web access is required')
    expect(response.assistantMessage).toContain('Eaglemont, Victoriua')
    expect(response.assistantMessage).toMatch(/budget/i)
    expect(response.readyToCreate).toBe(true)
    expect(response.suggestedAction).toBe('confirm_create')
    expect(response.draftDelta.name).toBe('24GB GPU for local inference')
    expect(response.draftDelta.brief).toContain('Eaglemont, Victoriua')
    expect(response.draftDelta.hardFilters).toEqual(
      expect.objectContaining({
        locationNames: ['Eaglemont, Victoriua'],
        includeKeywords: expect.arrayContaining(['GPU', '24GB VRAM']),
      }),
    )
  })
})
