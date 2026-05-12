import { COCKPIT_HOME_SOURCE_LABEL_TAXONOMY_VERSION } from './cockpit-home-contract';
import { resolveBackendUrl } from './proxy';
import type {
  CockpitHomeAttentionItemContract,
  CockpitHomeBackendSourceLabel,
  CockpitHomeBffResponse,
  CockpitHomeDataHealthContract,
  CockpitHomeDataMissingSignal,
  CockpitHomeDataState,
  CockpitHomeDeterministicState,
  CockpitHomeMarketSessionContract,
  CockpitHomeMarketMoverContract,
  CockpitHomeNewsItemContract,
  CockpitHomePortfolioContract,
  CockpitHomeSectionKey,
  MarketSessionState,
} from '@/types/cockpit-home';

export type CockpitHomeUpstreamFetch = (input: string, init: RequestInit) => Promise<Response>;

export interface BuildCockpitHomeBffResponseOptions {
  now?: Date;
  headers?: HeadersInit;
  backendUrl?: string;
  fetcher?: CockpitHomeUpstreamFetch;
  commentaryLimit?: number;
}

type UpstreamRead =
  | {
      ok: true;
      status: number;
      payload: unknown;
    }
  | {
      ok: false;
      status: number | null;
      payload: unknown;
      error: string;
    };

interface PortfolioPayload {
  data_state?: unknown;
  degraded?: unknown;
  data_missing?: unknown;
  as_of?: unknown;
  source_label?: unknown;
  total_value?: unknown;
  currency?: unknown;
  day_change?: unknown;
  day_change_percent?: unknown;
  coverage_percent?: unknown;
  holdings_count?: unknown;
  priced_holdings_count?: unknown;
  day_change_priced_holdings_count?: unknown;
}

interface CommentaryRecentItem {
  source_id?: unknown;
  source_name?: unknown;
  source_type?: unknown;
  approved_at?: unknown;
}

interface MarketSessionRecord {
  session?: unknown;
  exchange?: unknown;
  timezone?: unknown;
  session_date?: unknown;
  next_event_label?: unknown;
  next_event_at?: unknown;
  as_of?: unknown;
}

interface AttentionQueueRecord {
  id?: unknown;
  title?: unknown;
  reason?: unknown;
  status?: unknown;
  priority?: unknown;
  source_type?: unknown;
  created_at?: unknown;
  updated_at?: unknown;
  source_id?: unknown;
  target_route?: unknown;
}

interface AttentionQueuePayload {
  data_state?: unknown;
  degraded?: unknown;
  data_missing?: unknown;
  as_of?: unknown;
  items?: unknown;
}

interface MarketSessionAssembly {
  contract: CockpitHomeMarketSessionContract;
  health: CockpitHomeDataHealthContract;
}

interface PortfolioAssembly {
  contract: CockpitHomePortfolioContract;
  health: CockpitHomeDataHealthContract;
}

interface NewsAssembly {
  items: CockpitHomeNewsItemContract[];
  health: CockpitHomeDataHealthContract;
  missing: CockpitHomeDataMissingSignal[];
}

interface AttentionQueueAssembly {
  state: CockpitHomeDeterministicState;
  items: CockpitHomeAttentionItemContract[];
  health: CockpitHomeDataHealthContract;
  missing: CockpitHomeDataMissingSignal[];
}

interface MarketMoversAssembly {
  items: CockpitHomeMarketMoverContract[];
  health: CockpitHomeDataHealthContract;
  missing: CockpitHomeDataMissingSignal[];
}

const DEFAULT_COMMENTARY_LIMIT = 5;

export async function buildCockpitHomeBffResponse(
  options: BuildCockpitHomeBffResponseOptions = {},
): Promise<CockpitHomeBffResponse> {
  const now = options.now ?? new Date();
  const nowIso = now.toISOString();
  const backendUrl = (options.backendUrl ?? resolveBackendUrl()).replace(/\/$/, '');
  const fetcher = options.fetcher ?? fetch;
  const headers = new Headers(options.headers);
  const commentaryLimit = Math.max(1, Math.min(options.commentaryLimit ?? DEFAULT_COMMENTARY_LIMIT, 20));

  const [healthRead, marketSessionRead, portfolioRead, commentaryRead, attentionQueueRead] = await Promise.all([
    readBackendJson(fetcher, backendUrl, '/api/health', headers),
    readBackendJson(fetcher, backendUrl, '/api/cockpit/home/market-session', headers),
    readBackendJson(fetcher, backendUrl, '/api/cockpit/home/portfolio', headers),
    readBackendJson(fetcher, backendUrl, `/api/commentary/recent?limit=${commentaryLimit}`, headers),
    readBackendJson(fetcher, backendUrl, '/api/cockpit/home/attention-queue', headers),
  ]);

  const marketSession = buildMarketSessionContract(marketSessionRead, now, nowIso);
  const portfolio = buildPortfolioContract(portfolioRead, nowIso);
  const news = buildNewsContracts(commentaryRead, nowIso);
  const attentionQueue = buildAttentionQueueContracts(attentionQueueRead, nowIso);
  const marketMovers = buildMarketMoverContracts(attentionQueue, nowIso);
  const narrative = buildMissingNarrative(nowIso);
  const dataHealth = [
    buildBackendHealthItem(healthRead, nowIso),
    marketSession.health,
    portfolio.health,
    news.health,
    attentionQueue.health,
    marketMovers.health,
    missingHealthItem(
      'session_summary',
      'Home narrative',
      'NO_HOME_NARRATIVE_ENDPOINT',
      'No backend Home narrative endpoint is available for Cockpit Home v1.',
      nowIso,
    ),
  ];

  const dataMissing = [
    ...marketSession.contract.data_missing,
    ...portfolio.contract.data_missing,
    ...news.missing,
    ...marketMovers.missing,
    ...attentionQueue.missing,
    ...narrative.data_missing,
  ];
  const sectionStates = [
    marketSession.contract,
    portfolio.contract,
    ...news.items.map((item) => item.state),
    ...marketMovers.items.map((item) => item.state),
    attentionQueue.state,
    ...attentionQueue.items.map((item) => item.state),
    ...dataHealth,
    narrative,
  ];
  const aggregate = aggregateState(sectionStates, dataMissing);

  return {
    ok: true,
    generated_at: nowIso,
    source_label_taxonomy_version: COCKPIT_HOME_SOURCE_LABEL_TAXONOMY_VERSION,
    ...aggregate,
    market_session: marketSession.contract,
    portfolio: portfolio.contract,
    market_movers: marketMovers.items,
    news: news.items,
    attention_queue_state: attentionQueue.state,
    attention_queue: attentionQueue.items,
    data_health: dataHealth,
    narrative,
  };
}

async function readBackendJson(
  fetcher: CockpitHomeUpstreamFetch,
  backendUrl: string,
  path: string,
  headers: Headers,
): Promise<UpstreamRead> {
  try {
    const response = await fetcher(`${backendUrl}${path}`, {
      headers: new Headers(headers),
      cache: 'no-store',
    });
    const payload = await readResponsePayload(response);
    if (!response.ok) {
      return {
        ok: false,
        status: response.status,
        payload,
        error: `HTTP ${response.status}`,
      };
    }
    return {
      ok: true,
      status: response.status,
      payload,
    };
  } catch (error) {
    return {
      ok: false,
      status: null,
      payload: null,
      error: error instanceof Error ? error.message : 'Backend request failed',
    };
  }
}

async function readResponsePayload(response: Response): Promise<unknown> {
  const text = await response.text();
  if (!text) {
    return null;
  }
  try {
    return JSON.parse(text) as unknown;
  } catch {
    return text;
  }
}

function buildMarketSessionContract(read: UpstreamRead, now: Date, nowIso: string): MarketSessionAssembly {
  const sessionDate = formatMelbourneDate(now);
  if (!read.ok) {
    const missing = dataMissingSignal(
      'market_session',
      'MARKET_SESSION_ENDPOINT_UNAVAILABLE',
      `Backend market-session endpoint unavailable: ${read.error}.`,
      'missing_required_evidence',
    );
    const contract: CockpitHomeMarketSessionContract = {
      ...deterministicState('DATA_MISSING', null, [missing]),
      session: 'DEGRADED',
      exchange: 'ASX',
      timezone: 'Australia/Melbourne',
      session_date: sessionDate,
      next_event_label: null,
      next_event_at: null,
    };
    return {
      contract,
      health: dataHealthItem('market_session', 'Market session', contract, 'DATA_MISSING'),
    };
  }

  const payload = readMarketSession(read.payload);
  const session = marketSessionStateOrNull(payload.session);
  const exchange = requiredString(payload.exchange);
  const timezone = requiredString(payload.timezone);
  const nextEventLabel = stringOrNull(payload.next_event_label);
  const nextEventAt = stringOrNull(payload.next_event_at);
  const asOf = stringOrNull(payload.as_of) ?? nowIso;
  const responseSessionDate = stringOrNull(payload.session_date) ?? sessionDate;
  const invalid =
    !session ||
    exchange !== 'ASX' ||
    timezone !== 'Australia/Melbourne' ||
    !nextEventLabel ||
    !nextEventAt;

  if (invalid) {
    const missing = dataMissingSignal(
      'market_session',
      'MARKET_SESSION_RESPONSE_INVALID',
      'Backend market-session endpoint returned an incomplete Cockpit Home payload.',
      'degraded_runtime',
    );
    const contract: CockpitHomeMarketSessionContract = {
      ...deterministicState('DATA_MISSING', null, [missing]),
      session: 'DEGRADED',
      exchange: 'ASX',
      timezone: 'Australia/Melbourne',
      session_date: responseSessionDate,
      next_event_label: null,
      next_event_at: null,
    };
    return {
      contract,
      health: dataHealthItem('market_session', 'Market session', contract, 'DATA_MISSING'),
    };
  }

  const contract: CockpitHomeMarketSessionContract = {
    ...deterministicState('READY', asOf, []),
    session,
    exchange: 'ASX',
    timezone: 'Australia/Melbourne',
    session_date: responseSessionDate,
    next_event_label: nextEventLabel,
    next_event_at: nextEventAt,
  };
  return {
    contract,
    health: dataHealthItem('market_session', 'Market session', contract, session),
  };
}

function buildPortfolioContract(read: UpstreamRead, nowIso: string): PortfolioAssembly {
  if (!read.ok) {
    const missing = dataMissingSignal(
      'portfolio',
      'PORTFOLIO_ENDPOINT_UNAVAILABLE',
      `Backend Home portfolio endpoint unavailable: ${read.error}.`,
      'missing_required_evidence',
    );
    const contract: CockpitHomePortfolioContract = {
      ...deterministicState('DATA_MISSING', null, [missing]),
      source_label: 'local_personal_data',
      total_value: null,
      currency: null,
      day_change: null,
      day_change_percent: null,
      coverage_percent: null,
      holdings_count: 0,
      priced_holdings_count: 0,
      day_change_priced_holdings_count: 0,
    };
    return {
      contract,
      health: dataHealthItem('portfolio', 'Holdings', contract, 'DATA_MISSING'),
    };
  }

  const payload = readPortfolioPayload(read.payload);
  const backendMissing = readDataMissingSignals(payload.data_missing, 'portfolio');
  const sourceLabel = normalizeSourceLabelOrNull(payload.source_label) ?? 'local_personal_data';
  const backendState = dataStateOrNull(payload.data_state);
  const missing = backendState
    ? backendMissing
    : [
        dataMissingSignal(
          'portfolio',
          'PORTFOLIO_PAYLOAD_INCOMPLETE',
          'Backend Home portfolio endpoint returned an incomplete deterministic portfolio payload.',
          'local_personal_data',
        ),
        ...backendMissing,
      ];
  const dataState: CockpitHomeDataState =
    backendState === 'READY' && missing.length > 0 ? 'PARTIAL' : backendState ?? 'DATA_MISSING';
  const holdingsCount = integerOrZero(payload.holdings_count);
  const pricedHoldingsCount = integerOrZero(payload.priced_holdings_count);
  const dayChangePricedHoldingsCount = integerOrZero(payload.day_change_priced_holdings_count);
  const contract: CockpitHomePortfolioContract = {
    ...deterministicState(dataState, stringOrNull(payload.as_of) ?? nowIso, missing),
    source_label: sourceLabel,
    total_value: numberOrNull(payload.total_value),
    currency: normalizedCurrencyOrNull(payload.currency),
    day_change: numberOrNull(payload.day_change),
    day_change_percent: numberOrNull(payload.day_change_percent),
    coverage_percent: numberOrNull(payload.coverage_percent),
    holdings_count: holdingsCount,
    priced_holdings_count: pricedHoldingsCount,
    day_change_priced_holdings_count: dayChangePricedHoldingsCount,
  };

  return {
    contract,
    health: dataHealthItem(
      'portfolio',
      'Holdings',
      contract,
      `${pricedHoldingsCount}/${holdingsCount} priced`,
    ),
  };
}

function buildNewsContracts(read: UpstreamRead, nowIso: string): NewsAssembly {
  if (!read.ok) {
    const missing = dataMissingSignal(
      'news',
      'COMMENTARY_RECENT_UNAVAILABLE',
      `Recent commentary endpoint unavailable: ${read.error}.`,
      'missing_required_evidence',
    );
    const state = deterministicState('DATA_MISSING', null, [missing]);
    return {
      items: [],
      missing: [missing],
      health: dataHealthItem('news', 'Recent commentary', state, 'DATA_MISSING'),
    };
  }

  const rows = readCommentaryItems(read.payload);
  if (rows.length === 0) {
    const missing = dataMissingSignal(
      'news',
      'NO_RECENT_COMMENTARY',
      'Recent commentary endpoint returned no approved commentary sources.',
      'no_hit',
    );
    const state = deterministicState('DATA_MISSING', nowIso, [missing]);
    return {
      items: [],
      missing: [missing],
      health: dataHealthItem('news', 'Recent commentary', state, '0 approved'),
    };
  }

  const items = rows.map((row, index): CockpitHomeNewsItemContract => {
    const sourceId = requiredString(row.source_id);
    const sourceName = requiredString(row.source_name) || sourceId || 'Approved commentary source';
    const sourceType = requiredString(row.source_type) || 'commentary';
    const approvedAt = requiredString(row.approved_at) || nowIso;
    const missing = sourceId
      ? []
      : [
          dataMissingSignal(
            'news',
            'RECENT_COMMENTARY_SOURCE_ID_MISSING',
            'Recent commentary item did not include a backend-resolvable source_id.',
          ),
        ];
    const state = deterministicState(sourceId ? 'READY' : 'DATA_MISSING', sourceId ? approvedAt : null, missing);
    return {
      id: `home-news:${sourceId || index}`,
      section: 'news',
      title: sourceName,
      ticker: null,
      observed_at: approvedAt,
      state,
      evidence: {
        source_id: sourceId || null,
        source_kind: sourceId ? 'ephemeral' : null,
        source_label: sourceId ? 'context_only' : 'missing_required_evidence',
        evidence_labels: sourceId ? ['context_only'] : ['missing_required_evidence'],
        resolvable: Boolean(sourceId),
        resolver: sourceId ? 'cockpit_chat_attached_sources' : 'none',
        evidence_id: sourceId || null,
        document_id: null,
        chunk_id: null,
        url: null,
        title: sourceName,
        published_at: approvedAt,
      },
      headline: sourceName,
      source_name: sourceType,
      relevance: 'medium',
    };
  });
  const missing = items.flatMap((item) => item.state.data_missing);

  return {
    items,
    missing,
    health: dataHealthItem(
      'news',
      'Recent commentary',
      deterministicState(
        missing.length > 0 ? 'PARTIAL' : 'READY',
        latestTimestamp(items.map((item) => item.observed_at ?? null)) ?? nowIso,
        missing,
      ),
      `${items.length} approved`,
    ),
  };
}

function buildMarketMoverContracts(
  attentionQueue: AttentionQueueAssembly,
  nowIso: string,
): MarketMoversAssembly {
  const signals = attentionQueue.items.filter((item) => item.source_type === 'market_update_followup');

  if (signals.length === 0) {
    const items = buildUnimplementedSourceItems('market_movers', nowIso) as CockpitHomeMarketMoverContract[];
    return {
      items,
      missing: items.flatMap((item) => item.state.data_missing),
      health: missingHealthItem(
        'market_movers',
        'Market movers',
        'NO_MARKET_MOVERS_ENDPOINT',
        'No backend market-movers endpoint is available for Cockpit Home v1.',
        nowIso,
      ),
    };
  }

  const items = signals.slice(0, 5).map((item): CockpitHomeMarketMoverContract => {
    const ticker = tickerFromMarketUpdateTitle(item.title);
    const missing = [
      dataMissingSignal(
        'market_movers',
        'MARKET_MOVER_PRICE_FIELDS_MISSING',
        'Market update follow-up did not include deterministic price, change, and change-percent fields.',
        'operational_trace',
      ),
      ...(!ticker
        ? [
            dataMissingSignal(
              'market_movers',
              'MARKET_MOVER_TICKER_MISSING',
              'Market update follow-up title did not include a deterministic ticker prefix.',
              'operational_trace',
            ),
          ]
        : []),
    ];
    const state = deterministicState(ticker ? 'PARTIAL' : 'DATA_MISSING', item.observed_at ?? nowIso, missing);

    return {
      id: `home-market-movers:${item.id}`,
      section: 'market_movers',
      title: item.title,
      ticker,
      observed_at: item.observed_at ?? state.as_of,
      state,
      evidence: {
        source_id: null,
        source_kind: null,
        source_label: 'operational_trace',
        evidence_labels: ['operational_trace'],
        resolvable: false,
        resolver: 'none',
        evidence_id: item.id,
        document_id: null,
        chunk_id: null,
        url: null,
        title: item.title,
        published_at: item.observed_at ?? state.as_of,
      },
      price: null,
      change: null,
      change_percent: null,
      reason: item.reason,
    };
  });
  const missing = items.flatMap((item) => item.state.data_missing);

  return {
    items,
    missing,
    health: dataHealthItem(
      'market_movers',
      'Market movers',
      deterministicState('PARTIAL', latestTimestamp(items.map((item) => item.observed_at ?? null)) ?? nowIso, missing),
      `${items.length} update signal${items.length === 1 ? '' : 's'}`,
    ),
  };
}

function buildAttentionQueueContracts(read: UpstreamRead, nowIso: string): AttentionQueueAssembly {
  if (!read.ok) {
    const missing = dataMissingSignal(
      'attention_queue',
      'NO_ATTENTION_QUEUE_ENDPOINT',
      `Backend attention-queue endpoint unavailable: ${read.error}.`,
      'missing_required_evidence',
    );
    const state = deterministicState('DATA_MISSING', null, [missing]);
    return {
      state,
      items: [],
      missing: [missing],
      health: dataHealthItem('attention_queue', 'Attention queue', state, 'DATA_MISSING'),
    };
  }

  const payload = readAttentionQueuePayload(read.payload);
  const rawItems = readAttentionQueueItems(payload.items);
  const backendMissing = readDataMissingSignals(payload.data_missing, 'attention_queue');
  const asOf = stringOrNull(payload.as_of) ?? nowIso;
  const payloadState = dataStateOrNull(payload.data_state) ?? 'READY';

  if (!payload || !Array.isArray(payload.items)) {
    const missing = dataMissingSignal(
      'attention_queue',
      'ATTENTION_QUEUE_RESPONSE_INVALID',
      'Backend attention-queue endpoint returned an incomplete Cockpit Home payload.',
      'degraded_runtime',
    );
    const state = deterministicState('DATA_MISSING', null, [missing]);
    return {
      state,
      items: [],
      missing: [missing],
      health: dataHealthItem('attention_queue', 'Attention queue', state, 'DATA_MISSING'),
    };
  }

  const items = rawItems.map((row, index): CockpitHomeAttentionItemContract => {
    const id = requiredString(row.id);
    const title = requiredString(row.title);
    const reason = requiredString(row.reason);
    const status = requiredString(row.status) || 'queued';
    const sourceType = requiredString(row.source_type) || 'operational';
    const priority = attentionPriorityOrLow(row.priority);
    const createdAt = stringOrNull(row.created_at);
    const updatedAt = stringOrNull(row.updated_at) ?? createdAt;
    const itemMissing =
      id && title && reason
        ? []
        : [
            dataMissingSignal(
              'attention_queue',
              'ATTENTION_QUEUE_ITEM_INVALID',
              'Backend attention-queue item did not include deterministic id, title, and reason fields.',
              'degraded_runtime',
            ),
          ];
    const state = deterministicState(
      itemMissing.length > 0 ? 'DATA_MISSING' : 'READY',
      itemMissing.length > 0 ? null : updatedAt ?? asOf,
      itemMissing,
    );
    const evidenceLabel: CockpitHomeBackendSourceLabel =
      itemMissing.length > 0 ? 'degraded_runtime' : 'operational_trace';

    return {
      id: id || `home-attention-queue:invalid-${index}`,
      section: 'attention_queue',
      title: title || 'Attention item unavailable',
      ticker: null,
      observed_at: updatedAt ?? createdAt ?? asOf,
      state,
      evidence: {
        source_id: null,
        source_kind: null,
        source_label: evidenceLabel,
        evidence_labels: [evidenceLabel],
        resolvable: false,
        resolver: 'none',
        evidence_id: id || null,
        document_id: null,
        chunk_id: null,
        url: null,
        title: title || null,
        published_at: updatedAt ?? createdAt ?? null,
      },
      priority,
      description: reason || 'Attention item is missing a deterministic reason.',
      reason: reason || 'Attention item is missing a deterministic reason.',
      status,
      source_type: sourceType,
      created_at: createdAt,
      updated_at: updatedAt,
      source_id: null,
      target_route: null,
    };
  });
  const itemMissing = items.flatMap((item) => item.state.data_missing);
  const missing = [...backendMissing, ...itemMissing];
  const state = deterministicState(
    missing.length > 0 ? 'PARTIAL' : payloadState,
    asOf,
    missing,
  );

  return {
    state,
    items,
    missing,
    health: dataHealthItem('attention_queue', 'Attention queue', state, `${items.length} queued`),
  };
}

function buildUnimplementedSourceItems(section: CockpitHomeSectionKey, nowIso: string) {
  const codeBySection: Partial<Record<CockpitHomeSectionKey, string>> = {
    market_movers: 'NO_MARKET_MOVERS_ENDPOINT',
    attention_queue: 'NO_ATTENTION_QUEUE_ENDPOINT',
  };
  const messageBySection: Partial<Record<CockpitHomeSectionKey, string>> = {
    market_movers: 'No backend market-movers endpoint is available for Cockpit Home v1.',
    attention_queue: 'No backend attention-queue endpoint is available for Cockpit Home v1.',
  };
  const code = codeBySection[section] ?? 'SECTION_NOT_IMPLEMENTED';
  const message = messageBySection[section] ?? 'This Cockpit Home section is not implemented in v1.';
  const state = deterministicState('DATA_MISSING', nowIso, [dataMissingSignal(section, code, message)]);

  if (section === 'market_movers') {
    return [
      {
        id: 'home-market-movers:data-missing',
        section,
        title: 'Market movers unavailable',
        ticker: '',
        observed_at: nowIso,
        state,
        evidence: missingEvidence(),
        price: null,
        change: null,
        change_percent: null,
        reason: null,
      },
    ];
  }

  return [
    {
      id: 'home-attention-queue:data-missing',
      section,
      title: 'Attention queue unavailable',
      observed_at: nowIso,
      state,
      evidence: missingEvidence(),
      priority: 'low' as const,
      description: message,
    },
  ];
}

function buildMissingNarrative(nowIso: string) {
  const missing = [
    dataMissingSignal(
      'session_summary',
      'NO_SESSION_SUMMARY_ENDPOINT',
      'No backend session-summary endpoint is available for Cockpit Home v1.',
    ),
    dataMissingSignal(
      'theme_candidates',
      'NO_THEME_CANDIDATES_ENDPOINT',
      'No backend theme-candidates endpoint is available for Cockpit Home v1.',
    ),
    dataMissingSignal(
      'tomorrow_prep',
      'NO_TOMORROW_PREP_ENDPOINT',
      'No backend tomorrow-prep endpoint is available for Cockpit Home v1.',
    ),
  ];

  return {
    ...deterministicState('DATA_MISSING', nowIso, missing),
    session_summary: null,
    theme_candidates: [],
    tomorrow_prep: [],
  };
}

function buildBackendHealthItem(read: UpstreamRead, nowIso: string): CockpitHomeDataHealthContract {
  if (read.ok) {
    return dataHealthItem(
      'data_health',
      'Backend liveness',
      deterministicState('READY', nowIso, []),
      `HTTP ${read.status}`,
    );
  }
  const missing = dataMissingSignal(
    'data_health',
    'BACKEND_HEALTH_UNAVAILABLE',
    `Backend liveness endpoint unavailable: ${read.error}.`,
  );
  return dataHealthItem(
    'data_health',
    'Backend liveness',
    deterministicState('DATA_MISSING', null, [missing]),
    'DATA_MISSING',
  );
}

function missingHealthItem(
  section: CockpitHomeSectionKey,
  label: string,
  code: string,
  message: string,
  nowIso: string,
): CockpitHomeDataHealthContract {
  return dataHealthItem(
    section,
    label,
    deterministicState('DATA_MISSING', nowIso, [dataMissingSignal(section, code, message)]),
    'DATA_MISSING',
  );
}

function dataHealthItem(
  section: CockpitHomeSectionKey,
  label: string,
  state: CockpitHomeDeterministicState,
  value: string | null,
): CockpitHomeDataHealthContract {
  return {
    ...state,
    section,
    label,
    value,
  };
}

function deterministicState(
  dataState: CockpitHomeDataState,
  asOf: string | null,
  dataMissing: CockpitHomeDataMissingSignal[],
): CockpitHomeDeterministicState {
  return {
    data_state: dataState,
    degraded: dataState === 'DEGRADED' || dataState === 'DATA_MISSING',
    data_missing: dataMissing,
    as_of: asOf,
  };
}

function aggregateState(
  states: CockpitHomeDeterministicState[],
  dataMissing: CockpitHomeDataMissingSignal[],
): CockpitHomeDeterministicState {
  if (states.every((state) => state.data_state === 'DATA_MISSING')) {
    return deterministicState('DATA_MISSING', null, dataMissing);
  }
  if (states.some((state) => state.data_state === 'DEGRADED')) {
    return deterministicState('DEGRADED', latestTimestamp(states.map((state) => state.as_of)), dataMissing);
  }
  if (dataMissing.length > 0 || states.some((state) => state.data_state === 'PARTIAL')) {
    return deterministicState('PARTIAL', latestTimestamp(states.map((state) => state.as_of)), dataMissing);
  }
  return deterministicState('READY', latestTimestamp(states.map((state) => state.as_of)), []);
}

function dataMissingSignal(
  section: CockpitHomeSectionKey,
  code: string,
  message: string,
  sourceLabel: CockpitHomeBackendSourceLabel = 'missing_required_evidence',
): CockpitHomeDataMissingSignal {
  return {
    section,
    code,
    message,
    source_id: null,
    evidence_id: null,
    source_label: sourceLabel,
  };
}

function missingEvidence() {
  return {
    source_id: null,
    source_kind: null,
    source_label: 'missing_required_evidence' as const,
    evidence_labels: ['missing_required_evidence' as const],
    resolvable: false,
    resolver: 'none' as const,
    evidence_id: null,
    document_id: null,
    chunk_id: null,
    url: null,
    title: null,
    published_at: null,
  };
}

function readPortfolioPayload(payload: unknown): PortfolioPayload {
  if (!payload || typeof payload !== 'object') {
    return {};
  }
  return payload as PortfolioPayload;
}

function readCommentaryItems(payload: unknown): CommentaryRecentItem[] {
  if (!payload || typeof payload !== 'object' || !('items' in payload)) {
    return [];
  }
  const items = (payload as { items?: unknown }).items;
  if (!Array.isArray(items)) {
    return [];
  }
  return items.filter((item): item is CommentaryRecentItem => Boolean(item) && typeof item === 'object');
}

function readAttentionQueuePayload(payload: unknown): AttentionQueuePayload {
  if (!payload || typeof payload !== 'object') {
    return {};
  }
  return payload as AttentionQueuePayload;
}

function readAttentionQueueItems(payload: unknown): AttentionQueueRecord[] {
  if (!Array.isArray(payload)) {
    return [];
  }
  return payload.filter((item): item is AttentionQueueRecord => Boolean(item) && typeof item === 'object');
}

function readMarketSession(payload: unknown): MarketSessionRecord {
  if (!payload || typeof payload !== 'object') {
    return {};
  }
  return payload as MarketSessionRecord;
}

function latestTimestamp(values: Array<string | null | undefined>): string | null {
  const timestamps = values
    .map((value) => {
      const raw = typeof value === 'string' ? value.trim() : '';
      if (!raw) {
        return null;
      }
      const timestamp = Date.parse(raw);
      return Number.isFinite(timestamp) ? { raw, timestamp } : null;
    })
    .filter((value): value is { raw: string; timestamp: number } => value !== null);
  if (timestamps.length === 0) {
    return null;
  }
  timestamps.sort((left, right) => right.timestamp - left.timestamp);
  return timestamps[0].raw;
}

function numberOrNull(value: unknown): number | null {
  if (value === null || value === undefined || value === '') {
    return null;
  }
  const parsed = typeof value === 'number' ? value : Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function integerOrZero(value: unknown): number {
  const parsed = numberOrNull(value);
  if (parsed === null || parsed < 0) {
    return 0;
  }
  return Math.trunc(parsed);
}

function stringOrNull(value: unknown): string | null {
  const raw = typeof value === 'string' ? value.trim() : '';
  return raw || null;
}

function normalizedCurrencyOrNull(value: unknown): string | null {
  const raw = stringOrNull(value);
  return raw ? raw.toUpperCase() : null;
}

function requiredString(value: unknown): string {
  return typeof value === 'string' ? value.trim() : '';
}

function marketSessionStateOrNull(value: unknown): MarketSessionState | null {
  const raw = requiredString(value);
  if (raw === 'PRE_MARKET' || raw === 'OPEN' || raw === 'POST_MARKET' || raw === 'DEGRADED') {
    return raw;
  }
  return null;
}

function dataStateOrNull(value: unknown): CockpitHomeDataState | null {
  const raw = requiredString(value);
  if (raw === 'READY' || raw === 'PARTIAL' || raw === 'DEGRADED' || raw === 'DATA_MISSING') {
    return raw;
  }
  return null;
}

function attentionPriorityOrLow(value: unknown): CockpitHomeAttentionItemContract['priority'] {
  const raw = requiredString(value);
  if (raw === 'high' || raw === 'medium' || raw === 'low') {
    return raw;
  }
  return 'low';
}

function tickerFromMarketUpdateTitle(value: unknown): string {
  const raw = requiredString(value);
  const match = /^([A-Z][A-Z0-9]{1,5})(?=:)/.exec(raw);
  return match ? match[1] : '';
}

function readDataMissingSignals(
  value: unknown,
  fallbackSection: CockpitHomeSectionKey,
): CockpitHomeDataMissingSignal[] {
  if (!Array.isArray(value)) {
    return [];
  }
  return value
    .filter((item): item is Record<string, unknown> => Boolean(item) && typeof item === 'object')
    .map((item) => ({
      section: sectionKeyOrFallback(item.section, fallbackSection),
      code: requiredString(item.code) || 'DATA_MISSING',
      message: requiredString(item.message) || 'Backend reported missing Home data.',
      source_id: stringOrNull(item.source_id),
      evidence_id: stringOrNull(item.evidence_id),
      source_label: normalizeSourceLabelOrNull(item.source_label),
    }));
}

function sectionKeyOrFallback(value: unknown, fallback: CockpitHomeSectionKey): CockpitHomeSectionKey {
  const raw = requiredString(value);
  const valid = new Set<CockpitHomeSectionKey>([
    'market_session',
    'portfolio',
    'market_movers',
    'news',
    'attention_queue',
    'data_health',
    'session_summary',
    'theme_candidates',
    'tomorrow_prep',
  ]);
  return valid.has(raw as CockpitHomeSectionKey) ? (raw as CockpitHomeSectionKey) : fallback;
}

function normalizeSourceLabelOrNull(value: unknown): CockpitHomeBackendSourceLabel | null {
  const raw = requiredString(value) as CockpitHomeBackendSourceLabel;
  const valid = new Set<CockpitHomeBackendSourceLabel>([
    'claim_verified',
    'context_only',
    'no_hit',
    'operational_trace',
    'local_personal_data',
    'memory_context',
    'external_web_context',
    'local_news_context',
    'financial_truth',
    'degraded_runtime',
    'missing_required_evidence',
    'unknown_unclassified',
  ]);
  return valid.has(raw) ? raw : null;
}

function formatMelbourneDate(now: Date): string {
  const parts = new Intl.DateTimeFormat('en-AU', {
    timeZone: 'Australia/Melbourne',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).formatToParts(now);
  const values = new Map(parts.map((part) => [part.type, part.value]));
  return `${values.get('year') ?? '0000'}-${values.get('month') ?? '00'}-${values.get('day') ?? '00'}`;
}
