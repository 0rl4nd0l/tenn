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
  CockpitHomeMarketMoverContract,
  CockpitHomeNewsItemContract,
  CockpitHomePortfolioContract,
  CockpitHomeSectionKey,
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

interface CockpitHoldingRecord {
  ticker?: unknown;
  quantity?: unknown;
  current_price?: unknown;
  price_currency?: unknown;
  price_as_of?: unknown;
  market_value?: unknown;
}

interface CommentaryRecentItem {
  source_id?: unknown;
  source_name?: unknown;
  source_type?: unknown;
  approved_at?: unknown;
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

  const [healthRead, holdingsRead, commentaryRead] = await Promise.all([
    readBackendJson(fetcher, backendUrl, '/api/health', headers),
    readBackendJson(fetcher, backendUrl, '/api/cockpit/holdings', headers),
    readBackendJson(fetcher, backendUrl, `/api/commentary/recent?limit=${commentaryLimit}`, headers),
  ]);

  const marketSession = buildMissingMarketSession(now);
  const portfolio = buildPortfolioContract(holdingsRead, nowIso);
  const news = buildNewsContracts(commentaryRead, nowIso);
  const marketMovers = buildUnimplementedSourceItems('market_movers', nowIso) as CockpitHomeMarketMoverContract[];
  const attentionQueue = buildUnimplementedSourceItems('attention_queue', nowIso) as CockpitHomeAttentionItemContract[];
  const narrative = buildMissingNarrative(nowIso);
  const dataHealth = [
    buildBackendHealthItem(healthRead, nowIso),
    portfolio.health,
    news.health,
    missingHealthItem(
      'market_session',
      'Market session',
      'NO_MARKET_SESSION_ENDPOINT',
      'No backend market-session endpoint is available for Cockpit Home v1.',
      nowIso,
    ),
    missingHealthItem(
      'market_movers',
      'Market movers',
      'NO_MARKET_MOVERS_ENDPOINT',
      'No backend market-movers endpoint is available for Cockpit Home v1.',
      nowIso,
    ),
    missingHealthItem(
      'attention_queue',
      'Attention queue',
      'NO_ATTENTION_QUEUE_ENDPOINT',
      'No backend attention-queue endpoint is available for Cockpit Home v1.',
      nowIso,
    ),
    missingHealthItem(
      'session_summary',
      'Home narrative',
      'NO_HOME_NARRATIVE_ENDPOINT',
      'No backend Home narrative endpoint is available for Cockpit Home v1.',
      nowIso,
    ),
  ];

  const dataMissing = [
    ...marketSession.data_missing,
    ...portfolio.contract.data_missing,
    ...news.missing,
    ...marketMovers.flatMap((item) => item.state.data_missing),
    ...attentionQueue.flatMap((item) => item.state.data_missing),
    ...narrative.data_missing,
  ];
  const sectionStates = [
    marketSession,
    portfolio.contract,
    ...news.items.map((item) => item.state),
    ...marketMovers.map((item) => item.state),
    ...attentionQueue.map((item) => item.state),
    ...dataHealth,
    narrative,
  ];
  const aggregate = aggregateState(sectionStates, dataMissing);

  return {
    ok: true,
    generated_at: nowIso,
    source_label_taxonomy_version: COCKPIT_HOME_SOURCE_LABEL_TAXONOMY_VERSION,
    ...aggregate,
    market_session: marketSession,
    portfolio: portfolio.contract,
    market_movers: marketMovers,
    news: news.items,
    attention_queue: attentionQueue,
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

function buildMissingMarketSession(now: Date) {
  const sessionDate = formatMelbourneDate(now);
  const missing = dataMissingSignal(
    'market_session',
    'NO_MARKET_SESSION_ENDPOINT',
    'No backend market-session endpoint is available for Cockpit Home v1.',
  );

  return {
    ...deterministicState('DATA_MISSING', null, [missing]),
    session: 'DEGRADED' as const,
    exchange: 'ASX' as const,
    timezone: 'Australia/Melbourne' as const,
    session_date: sessionDate,
    next_event_label: null,
    next_event_at: null,
  };
}

function buildPortfolioContract(read: UpstreamRead, nowIso: string): PortfolioAssembly {
  if (!read.ok) {
    const missing = dataMissingSignal(
      'portfolio',
      'HOLDINGS_ENDPOINT_UNAVAILABLE',
      `Backend holdings endpoint unavailable: ${read.error}.`,
      'missing_required_evidence',
    );
    const contract: CockpitHomePortfolioContract = {
      ...deterministicState('DATA_MISSING', null, [missing]),
      total_value: null,
      day_change: null,
      day_change_percent: null,
      coverage_percent: null,
      holdings_count: 0,
      priced_holdings_count: 0,
    };
    return {
      contract,
      health: dataHealthItem('portfolio', 'Holdings', contract, 'DATA_MISSING'),
    };
  }

  const holdings = readHoldingItems(read.payload);
  const holdingsCount = holdings.length;
  const pricedHoldings = holdings.filter((item) => numberOrNull(item.market_value) !== null);
  const pricedHoldingsCount = pricedHoldings.length;
  const coverage = holdingsCount === 0 ? 100 : Number(((pricedHoldingsCount / holdingsCount) * 100).toFixed(1));
  const { totalValue, totalMissing } = totalPortfolioValue(pricedHoldings);
  const priceAsOf = latestTimestamp(holdings.map((item) => stringOrNull(item.price_as_of))) ?? nowIso;
  const missing = [
    ...(totalMissing ? [totalMissing] : []),
    ...(holdingsCount > 0
      ? [
          dataMissingSignal(
            'portfolio',
            'PORTFOLIO_DAY_CHANGE_UNAVAILABLE',
            'Backend holdings endpoint does not provide deterministic portfolio day-change fields.',
          ),
        ]
      : []),
  ];
  const dataState: CockpitHomeDataState = missing.length > 0 ? 'PARTIAL' : 'READY';
  const contract: CockpitHomePortfolioContract = {
    ...deterministicState(dataState, priceAsOf, missing),
    total_value: totalValue,
    day_change: holdingsCount === 0 ? 0 : null,
    day_change_percent: holdingsCount === 0 ? 0 : null,
    coverage_percent: coverage,
    holdings_count: holdingsCount,
    priced_holdings_count: pricedHoldingsCount,
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

function readHoldingItems(payload: unknown): CockpitHoldingRecord[] {
  if (!payload || typeof payload !== 'object' || !('items' in payload)) {
    return [];
  }
  const items = (payload as { items?: unknown }).items;
  if (!Array.isArray(items)) {
    return [];
  }
  return items.filter((item): item is CockpitHoldingRecord => Boolean(item) && typeof item === 'object');
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

function totalPortfolioValue(
  pricedHoldings: CockpitHoldingRecord[],
): { totalValue: number | null; totalMissing: CockpitHomeDataMissingSignal | null } {
  if (pricedHoldings.length === 0) {
    return { totalValue: 0, totalMissing: null };
  }

  const currencies = new Set(
    pricedHoldings
      .map((item) => requiredString(item.price_currency).toUpperCase())
      .filter(Boolean),
  );
  if (currencies.size === 0) {
    return {
      totalValue: null,
      totalMissing: dataMissingSignal(
        'portfolio',
        'PORTFOLIO_TOTAL_CURRENCY_MISSING',
        'Priced holdings did not include a currency, so Cockpit Home did not aggregate a currency-less total value.',
      ),
    };
  }
  if (currencies.size > 1) {
    return {
      totalValue: null,
      totalMissing: dataMissingSignal(
        'portfolio',
        'PORTFOLIO_TOTAL_CURRENCY_AMBIGUOUS',
        'Priced holdings use multiple currencies, so Cockpit Home did not aggregate a currency-less total value.',
      ),
    };
  }

  return {
    totalValue: Number(
      pricedHoldings.reduce((total, item) => total + (numberOrNull(item.market_value) ?? 0), 0).toFixed(2),
    ),
    totalMissing: null,
  };
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

function stringOrNull(value: unknown): string | null {
  const raw = typeof value === 'string' ? value.trim() : '';
  return raw || null;
}

function requiredString(value: unknown): string {
  return typeof value === 'string' ? value.trim() : '';
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
