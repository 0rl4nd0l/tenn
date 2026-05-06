import { CockpitHomeState } from '@/types/cockpit-home';

export const MOCK_MARKET_OPEN: CockpitHomeState = {
  session: 'OPEN',
  melbourneTime: '10:42 AM',
  nextEvent: 'Market Close in 5h 18m',
  portfolio: {
    value: 1245000.42,
    dayChange: 12450.21,
    dayChangePercent: 1.01,
    coverage: 98.5,
  },
  marketMovers: [
    { ticker: 'WTC', price: 92.45, change: 4.12, changePercent: 4.67, reason: 'Acquisition Announcement' },
    { ticker: 'MQG', price: 184.20, change: -1.45, changePercent: -0.78, reason: 'Sector Weakness' },
  ],
  news: [
    {
      id: '1',
      ticker: 'WTC',
      headline: 'WiseTech Global to Acquire European Logistics Software Provider',
      timestamp: '10:31 AM',
      source: 'ASX Announcement',
      trustLevel: 'EVIDENCE-READY',
      relevance: 'high',
    },
    {
      id: '2',
      ticker: 'CBA',
      headline: 'RBA Minutes Indicate Hawkish Stance on Inflation',
      timestamp: '10:05 AM',
      source: 'RBA',
      trustLevel: 'CLAIM-VERIFIED',
      relevance: 'medium',
    },
  ],
  attentionQueue: [
    { id: 'aq1', label: 'WTC Acquisition', priority: 'high', description: 'Evaluate materiality of logistics deal.' },
    { id: 'aq2', label: 'Portfolio Coverage', priority: 'medium', description: '3 tickers missing fresh pricing.' },
  ],
  dataHealth: [
    { label: 'Prices', status: 'healthy', value: 'Live' },
    { label: 'News', status: 'healthy', value: 'Nominal' },
    { label: 'Linking', status: 'healthy', value: 'Active' },
    { label: 'Runtime', status: 'healthy', value: 'Optimal' },
  ],
};

export const MOCK_PRE_MARKET: CockpitHomeState = {
  ...MOCK_MARKET_OPEN,
  session: 'PRE_MARKET',
  melbourneTime: '08:15 AM',
  nextEvent: 'ASX Open in 1h 45m',
  portfolio: {
    value: 1232550.21,
    dayChange: 0,
    dayChangePercent: 0,
    coverage: 95.0,
  },
  overnightLead: {
    market: 'S&P 500',
    changePercent: 1.25,
    summary: 'Strong tech rally driven by earnings. US 10Y Yield steady.',
  },
  news: [
    {
      id: 'pre1',
      ticker: 'BHP',
      headline: 'Iron Ore Prices Surge on China Stimulus Hopes',
      timestamp: '07:45 AM',
      source: 'Reuters',
      trustLevel: 'EVIDENCE-READY',
      relevance: 'high',
    },
    {
      id: 'pre2',
      ticker: 'XJO',
      headline: 'SPI Futures Indicate +45 Point Open',
      timestamp: '08:00 AM',
      source: 'ASX',
      trustLevel: 'CLAIM-VERIFIED',
      relevance: 'medium',
    },
  ],
  attentionQueue: [
    { id: 'preaq1', label: 'Overnight Lead', priority: 'high', description: 'US tech rally likely to spill over into ASX components.' },
    { id: 'preaq2', label: 'BHP Morning News', priority: 'medium', description: 'Analyze stimulus impact on mining sector.' },
  ],
  dataHealth: [
    { label: 'Ingestion', status: 'healthy', value: 'Nominal' },
    { label: 'Morning Queue', status: 'healthy', value: 'Synced' },
    { label: 'Linking', status: 'healthy', value: 'Ready' },
    { label: 'Runtime', status: 'healthy', value: 'Ready' },
  ],
};

export const MOCK_POST_MARKET: CockpitHomeState = {
  ...MOCK_MARKET_OPEN,
  session: 'POST_MARKET',
  melbourneTime: '04:30 PM',
  nextEvent: 'US Market Open in 5h 30m',
  sessionSummary: 'ASX ended higher as mining giants rallied on stimulus news. Banking sector remained mixed.',
  themeCandidates: [
    {
      label: 'Resource Rally',
      sentiment: 'positive',
      evidenceCount: 12,
      description: 'Broad gains across BHP, RIO and FMG following iron ore price surge.',
    },
    {
      label: 'Rate Sensitivity',
      sentiment: 'neutral',
      evidenceCount: 8,
      description: 'Mixed banking performance as RBA expectations remain hawkish.',
    },
  ],
  tomorrowPrep: [
    'Watch WTC for acquisition follow-up.',
    'Monitor China stimulus updates for continued resource strength.',
    'Review banking sector portfolio weights.',
  ],
  dataHealth: [
    { label: 'Final Prices', status: 'healthy', value: 'Settled' },
    { label: 'News Recap', status: 'healthy', value: 'Complete' },
    { label: 'Entity Links', status: 'healthy', value: 'Nominal' },
    { label: 'Audit Log', status: 'healthy', value: 'Verified' },
  ],
};

export const MOCK_DEGRADED_STATE: CockpitHomeState = {
  ...MOCK_MARKET_OPEN,
  session: 'DEGRADED',
  dataHealth: [
    { label: 'Prices', status: 'stale', value: '15m lag' },
    { label: 'News', status: 'degraded', value: 'Partial' },
    { label: 'Linking', status: 'failed', value: 'Offline' },
    { label: 'Runtime', status: 'healthy', value: 'Optimal' },
  ],
};
