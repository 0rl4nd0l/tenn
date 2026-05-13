export type MarketSessionState = 'PRE_MARKET' | 'OPEN' | 'POST_MARKET' | 'DEGRADED';

export type TrustLevel =
  | 'CLAIM-VERIFIED'
  | 'CONTEXT-ONLY'
  | 'NO-HIT'
  | 'OPERATIONAL-TRACE'
  | 'LOCAL-PERSONAL-DATA'
  | 'MEMORY-CONTEXT'
  | 'EXTERNAL-WEB-CONTEXT'
  | 'LOCAL-NEWS-CONTEXT'
  | 'FINANCIAL-TRUTH'
  | 'DEGRADED-RUNTIME'
  | 'MISSING-EVIDENCE'
  | 'UNKNOWN-UNCLASSIFIED'
  | 'STALE'
  | 'EVIDENCE-READY';

export interface DataHealthItem {
  label: string;
  status: 'healthy' | 'degraded' | 'failed' | 'stale';
  value?: string;
}

export interface MarketMover {
  ticker: string;
  price: number;
  change: number;
  changePercent: number;
  reason?: string;
}

export interface NewsItem {
  id: string;
  ticker: string;
  headline: string;
  timestamp: string;
  source: string;
  trustLevel: TrustLevel;
  relevance: 'high' | 'medium' | 'low';
  dataState?: CockpitHomeDataState;
  degraded?: boolean;
  dataMissing?: CockpitHomeDataMissingSignal[];
  sourceId?: string | null;
  sourceKind?: CockpitHomeSourceKind | null;
  sourceLabel?: CockpitHomeBackendSourceLabel | null;
  evidenceLabels?: CockpitHomeBackendSourceLabel[];
  resolvable?: boolean;
  resolver?: CockpitHomeEvidenceIdentity['resolver'];
  sourceUrl?: string | null;
  chatBlockedReason?: CockpitHomeChatHandoff['blocked_reason'];
  isDemo?: boolean;
}

export interface ThemeCandidate {
  label: string;
  sentiment: 'positive' | 'negative' | 'neutral';
  evidenceCount: number;
  description: string;
}

export interface CockpitHomeState {
  dataState?: CockpitHomeDataState;
  degraded?: boolean;
  dataMissing?: CockpitHomeDataMissingSignal[];
  asOf?: string | null;
  isDemo?: boolean;
  session: MarketSessionState;
  melbourneTime: string;
  nextEvent: string;
  portfolio: {
    value: number;
    dayChange: number;
    dayChangePercent: number;
    coverage: number;
  };
  marketMovers: MarketMover[];
  news: NewsItem[];
  attentionQueue: {
    id: string;
    label: string;
    priority: 'high' | 'medium' | 'low';
    description: string;
    status?: string;
    source?: string;
    updatedAt?: string | null;
    targetRoute?: string | null;
  }[];
  dataHealth: DataHealthItem[];
  // State-specific additions
  overnightLead?: {
    market: string;
    changePercent: number;
    summary: string;
  };
  sessionSummary?: string;
  themeCandidates?: ThemeCandidate[];
  tomorrowPrep?: string[];
}

export type CockpitHomeSourceLabelTaxonomyVersion = 'source_label_semantics_v1';

export type CockpitHomeBackendSourceLabel =
  | 'claim_verified'
  | 'context_only'
  | 'no_hit'
  | 'operational_trace'
  | 'local_personal_data'
  | 'memory_context'
  | 'external_web_context'
  | 'local_news_context'
  | 'financial_truth'
  | 'degraded_runtime'
  | 'missing_required_evidence'
  | 'unknown_unclassified';

export type CockpitHomeDataState = 'READY' | 'PARTIAL' | 'DEGRADED' | 'DATA_MISSING';

export type CockpitHomeSectionKey =
  | 'market_session'
  | 'portfolio'
  | 'market_movers'
  | 'news'
  | 'attention_queue'
  | 'data_health'
  | 'session_summary'
  | 'theme_candidates'
  | 'tomorrow_prep';

export type CockpitHomeSourceKind = 'ephemeral' | 'concat' | 'primary';

export interface CockpitHomeDataMissingSignal {
  section: CockpitHomeSectionKey;
  code: string;
  message: string;
  source_id?: string | null;
  evidence_id?: string | null;
  source_label?: CockpitHomeBackendSourceLabel | null;
}

export interface CockpitHomeDeterministicState {
  data_state: CockpitHomeDataState;
  degraded: boolean;
  data_missing: CockpitHomeDataMissingSignal[];
  as_of: string | null;
}

export interface CockpitHomeEvidenceIdentity {
  source_id: string | null;
  source_kind: CockpitHomeSourceKind | null;
  source_label: CockpitHomeBackendSourceLabel;
  evidence_labels: CockpitHomeBackendSourceLabel[];
  resolvable: boolean;
  resolver: 'cockpit_chat_attached_sources' | 'home_source_detail' | 'none';
  evidence_id?: string | null;
  document_id?: string | null;
  chunk_id?: string | null;
  url?: string | null;
  title?: string | null;
  published_at?: string | null;
}

export interface CockpitHomeSourceBearingItem {
  id: string;
  section: CockpitHomeSectionKey;
  title: string;
  ticker?: string | null;
  observed_at?: string | null;
  state: CockpitHomeDeterministicState;
  evidence: CockpitHomeEvidenceIdentity;
}

export interface CockpitHomeMarketSessionContract extends CockpitHomeDeterministicState {
  session: MarketSessionState;
  exchange: 'ASX';
  timezone: 'Australia/Melbourne';
  session_date: string | null;
  next_event_label: string | null;
  next_event_at: string | null;
}

export interface CockpitHomePortfolioContract extends CockpitHomeDeterministicState {
  source_label: CockpitHomeBackendSourceLabel;
  total_value: number | null;
  currency: string | null;
  day_change: number | null;
  day_change_percent: number | null;
  coverage_percent: number | null;
  holdings_count: number;
  priced_holdings_count: number;
  day_change_priced_holdings_count: number;
}

export interface CockpitHomeMarketMoverContract extends CockpitHomeSourceBearingItem {
  ticker: string;
  price: number | null;
  change: number | null;
  change_percent: number | null;
  reason: string | null;
}

export interface CockpitHomeNewsItemContract extends CockpitHomeSourceBearingItem {
  ticker: string | null;
  headline: string;
  source_name: string | null;
  relevance: 'high' | 'medium' | 'low';
}

export interface CockpitHomeAttentionItemContract extends CockpitHomeSourceBearingItem {
  priority: 'high' | 'medium' | 'low';
  description: string;
  status: string;
  source_type: string;
  reason: string;
  created_at?: string | null;
  updated_at?: string | null;
  source_id?: string | null;
  target_route?: string | null;
}

export interface CockpitHomeDataHealthContract extends CockpitHomeDeterministicState {
  section: CockpitHomeSectionKey;
  label: string;
  value: string | null;
}

export interface CockpitHomeNarrativeContract extends CockpitHomeDeterministicState {
  session_summary: string | null;
  theme_candidates: ThemeCandidate[];
  tomorrow_prep: string[];
}

export interface CockpitHomeBffResponse extends CockpitHomeDeterministicState {
  ok: boolean;
  generated_at: string;
  source_label_taxonomy_version: CockpitHomeSourceLabelTaxonomyVersion;
  market_session: CockpitHomeMarketSessionContract;
  portfolio: CockpitHomePortfolioContract;
	  market_movers: CockpitHomeMarketMoverContract[];
	  news: CockpitHomeNewsItemContract[];
	  attention_queue_state: CockpitHomeDeterministicState;
	  attention_queue: CockpitHomeAttentionItemContract[];
	  data_health: CockpitHomeDataHealthContract[];
	  narrative: CockpitHomeNarrativeContract;
}

export interface CockpitHomeAttachedSource {
  source_id: string;
  source_kind: CockpitHomeSourceKind;
}

export interface CockpitHomeChatHandoff {
  route: '/full-chat';
  chat_screen: 'ChatScreen';
  ticker?: string | null;
  initial_prompt?: string;
  attached_sources: CockpitHomeAttachedSource[];
  blocked_reason?: 'DATA_MISSING' | 'DEGRADED' | 'UNRESOLVABLE_SOURCE';
}
