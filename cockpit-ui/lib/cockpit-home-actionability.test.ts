import { describe, expect, it } from 'vitest';

import {
  buildHomeChatDraftHref,
  buildHomeUsefulNowActions,
  getHomeAssistantContext,
  getHomeSourceActionability,
  homeSectionState,
  safeInternalHomeRoute,
} from './cockpit-home-actionability';
import type {
  CockpitHomeBffResponse,
  CockpitHomeDataMissingSignal,
  NewsItem,
} from '@/types/cockpit-home';

describe('Cockpit Home actionability helpers', () => {
  it('allows source-backed Home news items to attach to Full Chat drafts', () => {
    const item = newsItem();

    expect(getHomeSourceActionability(item)).toMatchObject({
      reason: 'SOURCE_READY',
      label: 'SOURCE',
      canInspect: true,
      canAttachToChat: true,
    });
    expect(buildHomeChatDraftHref('Assess this source.', item)).toBe(
      '/full-chat?prompt=Assess+this+source.&source_id=youtube_transcript%3Asource-a&source_kind=ephemeral&source_title=BHP+operating+update',
    );
  });

  it('blocks chat attachment for DATA_MISSING, degraded, demo, and unresolved Home sources', () => {
    const cases: Array<[string, NewsItem, string]> = [
      [
        'missing',
        newsItem({
          dataState: 'DATA_MISSING',
          dataMissing: [signal('news', 'RECENT_COMMENTARY_SOURCE_ID_MISSING')],
          chatBlockedReason: 'DATA_MISSING',
        }),
        'DATA_MISSING',
      ],
      [
        'degraded',
        newsItem({ dataState: 'DEGRADED', degraded: true, chatBlockedReason: 'DEGRADED' }),
        'DEGRADED',
      ],
      [
        'demo',
        newsItem({ isDemo: true, sourceId: null, sourceKind: null, resolvable: false }),
        'DEMO_ONLY',
      ],
      [
        'unresolved',
        newsItem({ sourceId: null, sourceKind: null, resolvable: false, chatBlockedReason: 'UNRESOLVABLE_SOURCE' }),
        'UNRESOLVABLE_SOURCE',
      ],
    ];

    for (const [name, item, reason] of cases) {
      const actionability = getHomeSourceActionability(item);
      expect(actionability.reason, name).toBe(reason);
      expect(actionability.canAttachToChat, name).toBe(false);
      expect(buildHomeChatDraftHref('Assess this source.', item), name).toBe('/full-chat?prompt=Assess+this+source.');
    }
  });

  it('reports assistant context from explicit Home shell state', () => {
    expect(getHomeAssistantContext('demo', 'data_missing')).toMatchObject({
      stateLabel: 'DEMO',
      defaultPrompt: 'Summarize visible demo-state limitations.',
    });
    expect(getHomeAssistantContext('live', 'data_missing')).toMatchObject({
      stateLabel: 'DATA_MISSING',
      defaultPrompt: 'What Home evidence is currently missing?',
    });
    expect(getHomeAssistantContext('live', 'partial')).toMatchObject({
      stateLabel: 'PARTIAL',
      defaultPrompt: "Summarize today's available Home context.",
    });
  });

  it('keeps Useful Now source actions limited to attachable sources', () => {
    const portfolioSignal = signal('portfolio', 'PORTFOLIO_DAY_CHANGE_PARTIAL');
    const response = homeResponse({
      data_missing: [portfolioSignal],
      news: [
        homeNewsContract('missing-source', 'Missing source item', {
          data_state: 'DATA_MISSING',
          data_missing: [signal('news', 'RECENT_COMMENTARY_SOURCE_ID_MISSING')],
          source_id: null,
          source_kind: null,
          resolvable: false,
        }),
        homeNewsContract('ready-source', 'Ready source item', {
          source_id: 'youtube_transcript:ready-source',
          source_kind: 'ephemeral',
          resolvable: true,
        }),
      ],
    });
    const news = [
      newsItem({
        id: 'missing-source',
        headline: 'Missing source item',
        dataState: 'DATA_MISSING',
        dataMissing: [signal('news', 'RECENT_COMMENTARY_SOURCE_ID_MISSING')],
        sourceId: null,
        sourceKind: null,
        resolvable: false,
        chatBlockedReason: 'DATA_MISSING',
      }),
      newsItem({
        id: 'ready-source',
        headline: 'Ready source item',
        sourceId: 'youtube_transcript:ready-source',
      }),
    ];

    const actions = buildHomeUsefulNowActions(response, news, [
      {
        id: 'queued-action',
        label: 'Portfolio check',
        priority: 'high',
        description: 'Review the priced holdings gap.',
        status: 'queued',
        source: 'local_personal_data',
        targetRoute: '//example.com/not-allowed',
      },
    ]);

    expect(actions).toEqual([
      expect.objectContaining({
        id: 'attention:queued-action',
        href: null,
      }),
      expect.objectContaining({
        id: 'source:ready-source',
        title: 'Inspect source: Ready source item',
      }),
      expect.objectContaining({
        id: 'blocker:portfolio|PORTFOLIO_DAY_CHANGE_PARTIAL|Missing portfolio evidence.|||missing_required_evidence',
        title: 'Portfolio gap',
      }),
    ]);
  });

  it('normalizes Home section state and internal routes without inventing links', () => {
    const response = homeResponse({
      data_missing: [signal('news', 'NO_RECENT_COMMENTARY')],
      news: [],
    });

    expect(homeSectionState('news', response)).toBe('DATA_MISSING');
    expect(safeInternalHomeRoute('/news')).toBe('/news');
    expect(safeInternalHomeRoute('//example.com/news')).toBeNull();
    expect(safeInternalHomeRoute('news')).toBeNull();
  });
});

function newsItem(overrides: Partial<NewsItem> = {}): NewsItem {
  return {
    id: 'home-news:source-a',
    ticker: 'BHP',
    headline: 'BHP operating update',
    timestamp: '12:00 pm',
    source: 'youtube_transcript',
    trustLevel: 'CONTEXT-ONLY',
    relevance: 'medium',
    dataState: 'READY',
    degraded: false,
    dataMissing: [],
    sourceId: 'youtube_transcript:source-a',
    sourceKind: 'ephemeral',
    sourceLabel: 'context_only',
    evidenceLabels: ['context_only'],
    resolvable: true,
    resolver: 'cockpit_chat_attached_sources',
    sourceUrl: null,
    ...overrides,
  };
}

function homeResponse(overrides: Partial<CockpitHomeBffResponse> = {}): CockpitHomeBffResponse {
  const now = '2026-05-07T02:00:00.000Z';
  return {
    ok: true,
    generated_at: now,
    source_label_taxonomy_version: 'source_label_semantics_v1',
    data_state: 'PARTIAL',
    degraded: false,
    data_missing: [],
    as_of: now,
    market_session: {
      data_state: 'READY',
      degraded: false,
      data_missing: [],
      as_of: now,
      session: 'OPEN',
      exchange: 'ASX',
      timezone: 'Australia/Melbourne',
      session_date: '2026-05-07',
      next_event_label: 'ASX close',
      next_event_at: '2026-05-07T06:00:00+00:00',
    },
    portfolio: {
      data_state: 'PARTIAL',
      degraded: false,
      data_missing: [signal('portfolio', 'PORTFOLIO_DAY_CHANGE_PARTIAL')],
      as_of: now,
      source_label: 'local_personal_data',
      total_value: 1000,
      currency: 'AUD',
      day_change: null,
      day_change_percent: null,
      coverage_percent: 50,
      holdings_count: 2,
      priced_holdings_count: 1,
      day_change_priced_holdings_count: 1,
    },
    market_movers: [],
    news: [],
    attention_queue_state: {
      data_state: 'READY',
      degraded: false,
      data_missing: [],
      as_of: now,
    },
    attention_queue: [],
    data_health: [
      {
        data_state: 'READY',
        degraded: false,
        data_missing: [],
        as_of: now,
        section: 'data_health',
        label: 'Backend liveness',
        value: 'HTTP 200',
      },
    ],
    narrative: {
      data_state: 'DATA_MISSING',
      degraded: true,
      data_missing: [signal('session_summary', 'NO_SESSION_SUMMARY_ENDPOINT')],
      as_of: now,
      session_summary: null,
      theme_candidates: [],
      tomorrow_prep: [],
    },
    ...overrides,
  };
}

function homeNewsContract(
  id: string,
  headline: string,
  overrides: {
    data_state?: 'READY' | 'PARTIAL' | 'DEGRADED' | 'DATA_MISSING';
    data_missing?: CockpitHomeDataMissingSignal[];
    source_id?: string | null;
    source_kind?: 'ephemeral' | 'concat' | 'primary' | null;
    resolvable?: boolean;
  } = {},
): CockpitHomeBffResponse['news'][number] {
  const dataState = overrides.data_state ?? 'READY';
  const sourceId = overrides.source_id === undefined ? `youtube_transcript:${id}` : overrides.source_id;
  const sourceKind = overrides.source_kind === undefined ? 'ephemeral' : overrides.source_kind;
  const resolvable = overrides.resolvable ?? true;

  return {
    id,
    section: 'news',
    title: headline,
    ticker: 'BHP',
    observed_at: '2026-05-07T02:00:00.000Z',
    state: {
      data_state: dataState,
      degraded: dataState === 'DEGRADED',
      data_missing: overrides.data_missing ?? [],
      as_of: '2026-05-07T02:00:00.000Z',
    },
    evidence: {
      source_id: sourceId,
      source_kind: sourceKind,
      source_label: sourceId ? 'context_only' : 'missing_required_evidence',
      evidence_labels: [sourceId ? 'context_only' : 'missing_required_evidence'],
      resolvable,
      resolver: resolvable ? 'cockpit_chat_attached_sources' : 'none',
      evidence_id: sourceId,
      document_id: null,
      chunk_id: null,
      url: null,
      title: headline,
      published_at: '2026-05-07T02:00:00.000Z',
    },
    headline,
    source_name: 'youtube_transcript',
    relevance: 'medium',
  };
}

function signal(
  section: CockpitHomeDataMissingSignal['section'],
  code: string,
  message = `Missing ${section.replace('_', ' ')} evidence.`,
): CockpitHomeDataMissingSignal {
  return {
    section,
    code,
    message,
    source_id: null,
    evidence_id: null,
    source_label: 'missing_required_evidence',
  };
}
