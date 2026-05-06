export type MarketSessionState = 'PRE_MARKET' | 'OPEN' | 'POST_MARKET' | 'DEGRADED';

export type TrustLevel = 'CLAIM-VERIFIED' | 'CONTEXT-ONLY' | 'NO-HIT' | 'OPERATIONAL-TRACE' | 'DEGRADED-RUNTIME' | 'MISSING-EVIDENCE' | 'STALE' | 'EVIDENCE-READY';

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
}

export interface ThemeCandidate {
  label: string;
  sentiment: 'positive' | 'negative' | 'neutral';
  evidenceCount: number;
  description: string;
}

export interface CockpitHomeState {
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
