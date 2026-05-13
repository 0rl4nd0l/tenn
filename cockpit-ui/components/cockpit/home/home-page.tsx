'use client'

import Link from 'next/link';
import { ReactNode, useEffect, useMemo, useState } from 'react';
import { MarketStatusHeader } from './market-status-header';
import { DataHealthStrip } from './data-health-strip';
import { MarketPulseCard } from './cards/market-pulse-card';
import { PortfolioImpactCard } from './cards/portfolio-impact-card';
import { AttentionQueueCard } from './cards/attention-queue-card';
import { SourceDetailDrawer } from './source-detail-drawer';
import { ContextualAssistant } from './contextual-assistant';
import { SessionSummaryCard } from './cards/session-summary-card';
import { ThemeCandidatesCard } from './cards/theme-candidates-card';
import { EvidenceBadge } from './evidence-badge';
import { MOCK_MARKET_OPEN, MOCK_PRE_MARKET, MOCK_POST_MARKET, MOCK_DEGRADED_STATE } from '@/lib/mock/cockpit-home-fixtures';
import {
  buildCockpitHomeChatHandoff,
  cockpitHomeHasDataMissing,
  cockpitHomeSourceLabelToTrustLevel,
} from '@/lib/cockpit-home-contract';
import {
  CockpitHomeBffResponse,
  CockpitHomeDataMissingSignal,
  CockpitHomeDataState,
  CockpitHomeMarketMoverContract,
  CockpitHomeNewsItemContract,
  CockpitHomeState,
  DataHealthItem,
  MarketMover,
  MarketSessionState,
  NewsItem,
} from '@/types/cockpit-home';
import { cn } from '@/lib/utils';
import { AlertCircle, ArrowRight, Loader2, Newspaper, ShieldAlert, ShieldCheck, Wallet } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

type HomeLoadState =
  | { status: 'loading' }
  | { status: 'ready'; response: CockpitHomeBffResponse }
  | { status: 'error'; message: string };

const DEMO_STATES: Record<MarketSessionState, CockpitHomeState> = {
  OPEN: MOCK_MARKET_OPEN,
  PRE_MARKET: MOCK_PRE_MARKET,
  POST_MARKET: MOCK_POST_MARKET,
  DEGRADED: MOCK_DEGRADED_STATE,
};

const DEMO_MISSING_SIGNAL: CockpitHomeDataMissingSignal = {
  section: 'data_health',
  code: 'DEMO_FIXTURE_NOT_SOURCE_BACKED',
  message: 'Mock Home fixtures are explicit dev/demo state only and are not source-backed.',
  source_id: null,
  evidence_id: null,
  source_label: 'unknown_unclassified',
};

export function CockpitHomePage() {
  const [loadState, setLoadState] = useState<HomeLoadState>({ status: 'loading' });
  const [demoSession, setDemoSession] = useState<MarketSessionState | null>(null);
  const [selectedItem, setSelectedItem] = useState<NewsItem | null>(null);
  const [assistantContext, setAssistantContext] = useState<NewsItem | null>(null);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);

  const demoState = useMemo(
    () => (demoSession ? toDemoCockpitHomeState(DEMO_STATES[demoSession]) : null),
    [demoSession],
  );

  useEffect(() => {
    const controller = new AbortController();

    async function loadHome() {
      setLoadState({ status: 'loading' });
      try {
        const response = await fetch('/api/cockpit/home', {
          cache: 'no-store',
          signal: controller.signal,
        });
        const payload = (await response.json()) as CockpitHomeBffResponse;
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }
        setLoadState({ status: 'ready', response: payload });
      } catch (error) {
        if (controller.signal.aborted) {
          return;
        }
        setLoadState({
          status: 'error',
          message: error instanceof Error ? error.message : 'Cockpit Home BFF request failed',
        });
      }
    }

    void loadHome();

    return () => controller.abort();
  }, []);

  const handleSelectItem = (item: NewsItem) => {
    setSelectedItem(item);
    setIsDrawerOpen(true);
  };

  const handleAnalyze = (item: NewsItem) => {
    if (!item.resolvable || item.chatBlockedReason || item.isDemo) {
      return;
    }
    setAssistantContext(item);
    setIsDrawerOpen(false);
  };

  const setLiveMode = () => {
    setDemoSession(null);
    setAssistantContext(null);
    setSelectedItem(null);
    setIsDrawerOpen(false);
  };

  const setDemoMode = (session: MarketSessionState) => {
    setDemoSession(session);
    setAssistantContext(null);
    setSelectedItem(null);
    setIsDrawerOpen(false);
  };

  if (demoState) {
    return (
      <HomeShell
        mode="demo"
        status="data_missing"
        session={demoState.session}
        melbourneTime={demoState.melbourneTime}
        nextEvent={demoState.nextEvent}
        dataHealth={demoState.dataHealth}
        onSetLiveMode={setLiveMode}
        onSetDemoMode={setDemoMode}
        activeDemoSession={demoSession}
        selectedItem={selectedItem}
        assistantContext={assistantContext}
        isDrawerOpen={isDrawerOpen}
        onCloseDrawer={() => setIsDrawerOpen(false)}
        onAnalyze={handleAnalyze}
        onClearContext={() => setAssistantContext(null)}
        banner={
          <HomeStateBanner
            state="DATA_MISSING"
            title="DEMO FIXTURE"
            message="Mock Home session states are visible only as explicit demo state. They are not source-backed and cannot upgrade evidence trust."
            signals={[DEMO_MISSING_SIGNAL]}
          />
        }
      >
        <DemoWorkspace state={demoState} onSelectItem={handleSelectItem} />
      </HomeShell>
    );
  }

  if (loadState.status === 'loading') {
    return (
      <HomeShell
        mode="live"
        status="degraded"
        session="DEGRADED"
        melbourneTime="LOADING"
        nextEvent="GET /api/cockpit/home"
        dataHealth={[{ label: 'Home BFF', status: 'degraded', value: 'LOADING' }]}
        onSetLiveMode={setLiveMode}
        onSetDemoMode={setDemoMode}
        selectedItem={selectedItem}
        assistantContext={assistantContext}
        isDrawerOpen={isDrawerOpen}
        onCloseDrawer={() => setIsDrawerOpen(false)}
        onAnalyze={handleAnalyze}
        onClearContext={() => setAssistantContext(null)}
        banner={null}
      >
        <LoadingWorkspace />
      </HomeShell>
    );
  }

  if (loadState.status === 'error') {
    const missingSignal: CockpitHomeDataMissingSignal = {
      section: 'data_health',
      code: 'HOME_BFF_FETCH_FAILED',
      message: `GET /api/cockpit/home failed: ${loadState.message}.`,
      source_id: null,
      evidence_id: null,
      source_label: 'missing_required_evidence',
    };

    return (
      <HomeShell
        mode="live"
        status="data_missing"
        session="DEGRADED"
        melbourneTime="DATA_MISSING"
        nextEvent="Home BFF unavailable"
        dataHealth={[{ label: 'Home BFF', status: 'failed', value: 'DATA_MISSING' }]}
        onSetLiveMode={setLiveMode}
        onSetDemoMode={setDemoMode}
        selectedItem={selectedItem}
        assistantContext={assistantContext}
        isDrawerOpen={isDrawerOpen}
        onCloseDrawer={() => setIsDrawerOpen(false)}
        onAnalyze={handleAnalyze}
        onClearContext={() => setAssistantContext(null)}
        banner={
          <HomeStateBanner
            state="DATA_MISSING"
            title="Cockpit Home BFF unavailable"
            message="Home is not falling back to mock data. Mock fixtures are available only through explicit demo controls in non-production mode."
            signals={[missingSignal]}
          />
        }
      >
        <MissingWorkspace signals={[missingSignal]} />
      </HomeShell>
    );
  }

  const response = loadState.response;
  const headerTime = formatMelbourneTime(response.generated_at);
  const nextEvent = response.market_session.next_event_label ?? response.market_session.next_event_at ?? response.data_state;
  const liveNews = response.news.map(mapNewsItem);

  return (
    <HomeShell
      mode="live"
      status={systemStatusFromResponse(response)}
      session={response.market_session.session}
      melbourneTime={headerTime}
      nextEvent={nextEvent}
      dataHealth={response.data_health.map(mapDataHealthItem)}
      onSetLiveMode={setLiveMode}
      onSetDemoMode={setDemoMode}
      selectedItem={selectedItem}
      assistantContext={assistantContext}
      isDrawerOpen={isDrawerOpen}
      onCloseDrawer={() => setIsDrawerOpen(false)}
      onAnalyze={handleAnalyze}
      onClearContext={() => setAssistantContext(null)}
      banner={
        response.data_state === 'READY' ? null : (
          <HomeStateBanner
            state={response.data_state}
            title={`Home state: ${response.data_state}`}
            message="The UI is rendering backend-provided degraded, partial, and DATA_MISSING signals without mock substitution."
            signals={response.data_missing}
          />
        )
      }
    >
      <LiveWorkspace response={response} news={liveNews} onSelectItem={handleSelectItem} />
    </HomeShell>
  );
}

function HomeShell({
  mode,
  status,
  session,
  melbourneTime,
  nextEvent,
  dataHealth,
  activeDemoSession,
  selectedItem,
  assistantContext,
  isDrawerOpen,
  onSetLiveMode,
  onSetDemoMode,
  onCloseDrawer,
  onAnalyze,
  onClearContext,
  banner,
  children,
}: {
  mode: 'live' | 'demo';
  status: 'operational' | 'partial' | 'degraded' | 'data_missing';
  session: MarketSessionState;
  melbourneTime: string;
  nextEvent: string;
  dataHealth: DataHealthItem[];
  activeDemoSession?: MarketSessionState | null;
  selectedItem: NewsItem | null;
  assistantContext: NewsItem | null;
  isDrawerOpen: boolean;
  onSetLiveMode: () => void;
  onSetDemoMode: (session: MarketSessionState) => void;
  onCloseDrawer: () => void;
  onAnalyze: (item: NewsItem) => void;
  onClearContext: () => void;
  banner: React.ReactNode;
  children: ReactNode;
}) {
  return (
    <div className="flex flex-col h-full bg-background overflow-hidden">
      {banner}

      <MarketStatusHeader
        session={session}
        melbourneTime={melbourneTime}
        nextEvent={nextEvent}
        systemStatus={status}
      />

      <DataHealthStrip items={dataHealth} />

      <main className="flex-1 flex min-h-0 relative">
        {process.env.NODE_ENV !== 'production' && (
          <DemoToolbar
            mode={mode}
            activeDemoSession={activeDemoSession ?? null}
            onSetLiveMode={onSetLiveMode}
            onSetDemoMode={onSetDemoMode}
          />
        )}

        <div className="flex-1 overflow-y-auto p-6 pt-14 scroll-smooth">
          {children}
        </div>

        <aside className="w-[380px] border-l border-border shrink-0 hidden xl:block">
          <ContextualAssistant
            attachedItem={assistantContext}
            onClearContext={onClearContext}
          />
        </aside>
      </main>

      <SourceDetailDrawer
        item={selectedItem}
        isOpen={isDrawerOpen}
        onClose={onCloseDrawer}
        onAnalyze={onAnalyze}
      />
    </div>
  );
}

function DemoToolbar({
  mode,
  activeDemoSession,
  onSetLiveMode,
  onSetDemoMode,
}: {
  mode: 'live' | 'demo';
  activeDemoSession: MarketSessionState | null;
  onSetLiveMode: () => void;
  onSetDemoMode: (session: MarketSessionState) => void;
}) {
  return (
    <div className="absolute top-4 left-6 z-20 flex items-center gap-2" aria-label="Home view mode">
      <button
        onClick={onSetLiveMode}
        className={cn(
          "px-3 py-1 rounded-full text-[9px] font-mono border transition-all uppercase tracking-tighter",
          mode === 'live'
            ? "bg-cyan-500/20 border-cyan-500/40 text-cyan-400"
            : "bg-accent/40 border-border/60 text-muted-foreground hover:bg-accent/60",
        )}
      >
        LIVE BFF
      </button>
      {(['PRE_MARKET', 'OPEN', 'POST_MARKET', 'DEGRADED'] as MarketSessionState[]).map((session) => (
        <button
          key={session}
          onClick={() => onSetDemoMode(session)}
          className={cn(
            "px-3 py-1 rounded-full text-[9px] font-mono border transition-all uppercase tracking-tighter",
            activeDemoSession === session
              ? "bg-amber-500/20 border-amber-500/40 text-amber-400"
              : "bg-accent/40 border-border/60 text-muted-foreground hover:bg-accent/60",
          )}
        >
          DEMO {session.replace('_', ' ')}
        </button>
      ))}
    </div>
  );
}

function LoadingWorkspace() {
  return (
    <div className="grid grid-cols-12 gap-6 max-w-[1600px] mx-auto" data-testid="home-loading-state">
      <div className="col-span-12">
        <Card className="terminal-panel">
          <CardContent className="p-8 flex items-center gap-3">
            <Loader2 className="w-5 h-5 text-cyan-500 animate-spin" />
            <div>
              <div className="text-[13px] font-mono font-bold text-foreground uppercase">Loading Cockpit Home</div>
              <div className="text-[12px] text-muted-foreground">Fetching GET /api/cockpit/home from the Next.js BFF.</div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function MissingWorkspace({ signals }: { signals: CockpitHomeDataMissingSignal[] }) {
  return (
    <div className="grid grid-cols-12 gap-6 max-w-[1600px] mx-auto">
      <div className="col-span-12">
        <SectionStatePanel
          title="Cockpit Home"
          state="DATA_MISSING"
          message="The Home UI has no backend response to render."
          signals={signals}
        />
      </div>
    </div>
  );
}

function DemoWorkspace({
  state,
  onSelectItem,
}: {
  state: CockpitHomeState;
  onSelectItem: (item: NewsItem) => void;
}) {
  return (
    <div className="grid grid-cols-12 gap-6 max-w-[1600px] mx-auto">
      <div className="col-span-12 lg:col-span-4 min-h-[300px]">
        <MarketPulseCard movers={state.marketMovers} overnightLead={state.overnightLead} />
      </div>
      <div className="col-span-12 lg:col-span-8 min-h-[300px]">
        {state.session === 'POST_MARKET' && state.sessionSummary ? (
          <SessionSummaryCard summary={state.sessionSummary} tomorrowPrep={state.tomorrowPrep} />
        ) : (
          <PortfolioImpactCard portfolio={state.portfolio} />
        )}
      </div>
      <div className="col-span-12 lg:col-span-8">
        <LiveNewsPanel news={state.news} dataState="DATA_MISSING" dataMissing={[DEMO_MISSING_SIGNAL]} onSelectItem={onSelectItem} />
      </div>
      <div className="col-span-12 lg:col-span-4 flex flex-col gap-6">
        {state.session === 'POST_MARKET' && state.themeCandidates && (
          <div className="flex-1">
            <ThemeCandidatesCard themes={state.themeCandidates} />
          </div>
        )}
        <div className="flex-1">
          <AttentionQueueCard items={state.attentionQueue} />
        </div>
      </div>
    </div>
  );
}

function LiveWorkspace({
  response,
  news,
  onSelectItem,
}: {
  response: CockpitHomeBffResponse;
  news: NewsItem[];
  onSelectItem: (item: NewsItem) => void;
}) {
  const readyMovers = response.market_movers.filter(isRenderableMarketMover).map(mapMarketMover);
  const partialMovers = response.market_movers.filter(isPartialMarketMoverSignal);
  const attentionItems = response.attention_queue
    .filter((item) => !cockpitHomeHasDataMissing(item.state))
      .map((item) => ({
        id: item.id,
        label: item.title,
        priority: item.priority,
        description: item.description,
        status: item.status,
        source: item.source_type,
        updatedAt: item.updated_at ?? item.created_at ?? null,
        targetRoute: item.target_route,
      }));
  const attentionState = sectionState('attention_queue', response);

  return (
    <div className="grid grid-cols-12 gap-6 max-w-[1600px] mx-auto">
      <div className="col-span-12 lg:col-span-4 min-h-[300px]">
        {readyMovers.length > 0 ? (
          <MarketPulseCard movers={readyMovers} />
        ) : partialMovers.length > 0 ? (
          <MarketMoverSignalsPanel movers={partialMovers} />
        ) : (
          <SectionStatePanel
            title="Market Pulse"
            state={sectionState('market_movers', response)}
            message="No backend market-movers data is available for Cockpit Home v1."
            signals={sectionSignals('market_movers', response)}
          />
        )}
      </div>
      <div className="col-span-12 lg:col-span-8 min-h-[300px]">
        <LivePortfolioPanel response={response} />
      </div>

      <div className="col-span-12 lg:col-span-8">
        <LiveNewsPanel
          news={news}
          dataState={sectionState('news', response)}
          dataMissing={sectionSignals('news', response)}
          onSelectItem={onSelectItem}
        />
      </div>
      <div className="col-span-12 lg:col-span-4 flex flex-col gap-6">
        {response.narrative.theme_candidates.length > 0 && (
          <div className="flex-1">
            <ThemeCandidatesCard themes={response.narrative.theme_candidates} />
          </div>
        )}
        <div className="flex-1">
          {attentionItems.length > 0 ? (
            <AttentionQueueCard items={attentionItems} />
          ) : (
            <SectionStatePanel
              title="Attention Queue"
              state={attentionState}
              message={
                attentionState === 'READY'
                  ? 'No attention items are currently queued.'
                  : 'No backend attention-queue data is available for Cockpit Home v1.'
              }
              signals={sectionSignals('attention_queue', response)}
            />
          )}
        </div>
      </div>
    </div>
  );
}

function MarketMoverSignalsPanel({ movers }: { movers: CockpitHomeMarketMoverContract[] }) {
  return (
    <Card className="terminal-panel h-full">
      <CardHeader className="py-3 px-4 flex flex-row items-center justify-between space-y-0 border-b border-border/40">
        <CardTitle className="text-[12px] font-mono uppercase tracking-wider text-muted-foreground">
          Market Update Signals
        </CardTitle>
        <span className="text-[10px] font-mono uppercase text-amber-500">PARTIAL</span>
      </CardHeader>
      <CardContent className="p-0">
        <div className="divide-y divide-border/40">
          {movers.map((mover) => (
            <div key={mover.id} className="p-4 space-y-2">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-[11px] font-mono font-bold text-cyan-500 px-1.5 py-0.5 bg-cyan-500/10 border border-cyan-500/20 rounded uppercase">
                      {mover.ticker || 'NO_TICKER'}
                    </span>
                    <span className="text-[10px] font-mono text-muted-foreground truncate">
                      {formatMelbourneTime(mover.observed_at ?? mover.state.as_of)}
                    </span>
                  </div>
                  <h4 className="mt-2 text-[13px] font-sans font-medium leading-snug">{mover.title}</h4>
                </div>
                <EvidenceBadge level={cockpitHomeSourceLabelToTrustLevel(mover.evidence.source_label)} />
              </div>
              <p className="text-[11px] text-muted-foreground leading-relaxed">{mover.reason}</p>
              <StateSignalList
                signals={mover.state.data_missing}
                fallback="Market update signal is missing numeric market-mover fields."
              />
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

function LivePortfolioPanel({ response }: { response: CockpitHomeBffResponse }) {
  const portfolio = response.portfolio;
  const state = portfolio.data_state;
  const value = portfolio.total_value === null ? 'DATA_MISSING' : formatCurrency(portfolio.total_value, portfolio.currency);
  const dayChange = portfolio.day_change === null ? 'DATA_MISSING' : formatSignedCurrency(portfolio.day_change, portfolio.currency);
  const dayChangePercent = portfolio.day_change_percent === null ? 'DATA_MISSING' : formatSignedPercent(portfolio.day_change_percent);
  const coverage = portfolio.coverage_percent === null ? 'DATA_MISSING' : `${portfolio.coverage_percent}%`;

  return (
    <Card className="terminal-panel h-full border-l-2 border-l-cyan-500/50">
      <CardHeader className="py-3 px-4 flex flex-row items-center justify-between space-y-0">
        <CardTitle className="text-[12px] font-mono uppercase tracking-wider text-muted-foreground flex items-center gap-2">
          <Wallet className="w-3.5 h-3.5" />
          My Portfolio Impact
        </CardTitle>
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1.5 bg-cyan-500/10 px-2 py-0.5 rounded border border-cyan-500/20">
            <ShieldCheck className="w-3 h-3 text-cyan-400" />
            <span className="text-[10px] font-mono text-cyan-400 font-bold">LOCAL PERSONAL DATA</span>
          </div>
          <Link
            href="/holdings"
            className="h-7 w-7 inline-flex items-center justify-center rounded border border-border/60 bg-accent/30 text-muted-foreground hover:text-cyan-400 hover:border-cyan-500/40 transition-colors"
            aria-label="Open portfolio holdings"
            title="Open portfolio holdings"
          >
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>
      </CardHeader>
      <CardContent className="px-4 pb-4 space-y-4">
        <div className="text-[11px] font-sans text-muted-foreground">
          Local personal holdings data only. This panel is not canonical financial truth.
        </div>
        <div className="flex flex-col gap-1">
          <span className="text-[10px] font-mono uppercase text-muted-foreground/60">Total Value</span>
          <span className={cn("text-2xl font-mono font-bold tracking-tight", value === 'DATA_MISSING' ? 'text-amber-500' : 'text-foreground')}>
            {value}
          </span>
        </div>

        <div className="grid grid-cols-3 gap-4">
          <PortfolioMetric
            label="Day Change"
            value={dayChange}
            detail={`${portfolio.day_change_priced_holdings_count}/${portfolio.holdings_count} covered`}
          />
          <PortfolioMetric label="Change %" value={dayChangePercent} />
          <PortfolioMetric label="Coverage" value={coverage} detail={`${portfolio.priced_holdings_count}/${portfolio.holdings_count} priced`} />
        </div>

        {state !== 'READY' && (
          <StateSignalList signals={portfolio.data_missing} fallback={`${state} portfolio state from backend.`} />
        )}
      </CardContent>
    </Card>
  );
}

function PortfolioMetric({ label, value, detail }: { label: string; value: string; detail?: string }) {
  return (
    <div className="flex flex-col gap-0.5 min-w-0">
      <span className="text-[10px] font-mono uppercase text-muted-foreground/60">{label}</span>
      <span className={cn("text-[14px] font-mono font-bold break-words", value === 'DATA_MISSING' ? 'text-amber-500' : 'text-foreground')}>
        {value}
      </span>
      {detail && <span className="text-[10px] font-mono text-muted-foreground">{detail}</span>}
    </div>
  );
}

function LiveNewsPanel({
  news,
  dataState,
  dataMissing,
  onSelectItem,
}: {
  news: NewsItem[];
  dataState: CockpitHomeDataState;
  dataMissing: CockpitHomeDataMissingSignal[];
  onSelectItem: (item: NewsItem) => void;
}) {
  return (
    <Card className="terminal-panel h-full flex flex-col">
      <CardHeader className="py-3 px-4 flex flex-row items-center justify-between space-y-0 shrink-0 border-b border-border/40">
        <CardTitle className="text-[12px] font-mono uppercase tracking-wider text-muted-foreground flex items-center gap-2">
          <Newspaper className="w-3.5 h-3.5" />
          News & Announcements
        </CardTitle>
        <div className="flex items-center gap-2">
          <span className={cn("text-[10px] font-mono uppercase", stateTextColor(dataState))}>{dataState}</span>
          <Link
            href="/news"
            className="h-7 w-7 inline-flex items-center justify-center rounded border border-border/60 bg-accent/30 text-muted-foreground hover:text-cyan-400 hover:border-cyan-500/40 transition-colors"
            aria-label="Open news workspace"
            title="Open news workspace"
          >
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>
      </CardHeader>
      <CardContent className="p-0 flex-1 min-h-0">
        {news.length === 0 ? (
          <InlineStateNotice
            state={dataState}
            message="The backend did not provide resolvable Home news items."
            signals={dataMissing}
          />
        ) : (
          <div className="divide-y divide-border/40 max-h-[400px] overflow-y-auto">
            {news.map((item) => (
              <button
                key={item.id}
                type="button"
                className="w-full text-left p-4 hover:bg-accent/30 cursor-pointer transition-colors group"
                onClick={() => onSelectItem(item)}
              >
                <div className="flex items-start justify-between gap-4 mb-2">
                  <div className="flex items-center gap-2 min-w-0">
                    <span className="text-[11px] font-mono font-bold text-cyan-500 px-1.5 py-0.5 bg-cyan-500/10 border border-cyan-500/20 rounded uppercase">
                      {item.ticker || 'NO_TICKER'}
                    </span>
                    <span className="text-[10px] font-mono text-muted-foreground truncate">
                      {item.timestamp}
                    </span>
                  </div>
                  <EvidenceBadge level={item.trustLevel} />
                </div>
                <h4 className="text-[13px] font-sans font-medium leading-snug mb-3 group-hover:text-cyan-400 transition-colors">
                  {item.headline}
                </h4>
                <div className="flex items-center justify-between gap-3">
                  <span className="text-[10px] font-mono text-muted-foreground/70 uppercase truncate">
                    {item.source}
                  </span>
                  <span className={cn("text-[10px] font-mono uppercase", item.chatBlockedReason ? 'text-amber-500' : 'text-cyan-500')}>
                    {item.chatBlockedReason ? item.chatBlockedReason : 'SOURCE'}
                  </span>
                </div>
              </button>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function InlineStateNotice({
  state,
  message,
  signals,
}: {
  state: CockpitHomeDataState;
  message: string;
  signals: CockpitHomeDataMissingSignal[];
}) {
  return (
    <div className="p-4 space-y-3">
      <div className="flex items-start gap-3">
        <ShieldAlert className={cn("w-4 h-4 mt-0.5 shrink-0", stateTextColor(state))} />
        <p className="text-[12px] font-sans text-muted-foreground leading-relaxed">{message}</p>
      </div>
      <StateSignalList signals={signals} fallback={`${state} without section-specific signal.`} />
    </div>
  );
}

function SectionStatePanel({
  title,
  state,
  message,
  signals,
}: {
  title: string;
  state: CockpitHomeDataState;
  message: string;
  signals: CockpitHomeDataMissingSignal[];
}) {
  return (
    <Card className="terminal-panel h-full">
      <CardHeader className="py-3 px-4 flex flex-row items-center justify-between space-y-0 border-b border-border/40">
        <CardTitle className="text-[12px] font-mono uppercase tracking-wider text-muted-foreground">
          {title}
        </CardTitle>
        <span className={cn("text-[10px] font-mono uppercase", stateTextColor(state))}>{state}</span>
      </CardHeader>
      <CardContent className="p-4 space-y-3">
        <div className="flex items-start gap-3">
          <ShieldAlert className={cn("w-4 h-4 mt-0.5 shrink-0", stateTextColor(state))} />
          <p className="text-[12px] font-sans text-muted-foreground leading-relaxed">{message}</p>
        </div>
        <StateSignalList signals={signals} fallback={`${state} without section-specific signal.`} />
      </CardContent>
    </Card>
  );
}

function HomeStateBanner({
  state,
  title,
  message,
  signals,
}: {
  state: CockpitHomeDataState;
  title: string;
  message: string;
  signals: CockpitHomeDataMissingSignal[];
}) {
  return (
    <div
      className={cn(
        "border-b px-4 py-2 flex items-start justify-center gap-3 shrink-0",
        state === 'DATA_MISSING' || state === 'DEGRADED'
          ? 'bg-red-500/15 border-red-500/30'
          : 'bg-amber-500/15 border-amber-500/30',
      )}
    >
      <AlertCircle className={cn("w-4 h-4 mt-0.5", stateTextColor(state))} />
      <div className="max-w-[1200px]">
        <div className={cn("text-[11px] font-mono font-bold uppercase tracking-widest", stateTextColor(state))}>
          {title}
        </div>
        <div className="text-[12px] text-muted-foreground">{message}</div>
        {signals.length > 0 && (
          <div className="mt-1 text-[10px] font-mono text-muted-foreground">
            {signals.slice(0, 3).map((signal) => signal.code).join(' | ')}
          </div>
        )}
      </div>
    </div>
  );
}

function StateSignalList({
  signals,
  fallback,
}: {
  signals: CockpitHomeDataMissingSignal[];
  fallback: string;
}) {
  const uniqueSignals = uniqueDataMissingSignals(signals);

  if (uniqueSignals.length === 0) {
    return <div className="text-[11px] font-mono text-muted-foreground">{fallback}</div>;
  }

  return (
    <div className="space-y-1">
      {uniqueSignals.map((signal, index) => (
        <div key={dataMissingSignalKey(signal, index)} className="text-[11px] font-mono text-muted-foreground leading-relaxed">
          <span className="text-amber-500">{signal.code}</span>: {signal.message}
        </div>
      ))}
    </div>
  );
}

function toDemoCockpitHomeState(source: CockpitHomeState): CockpitHomeState {
  return {
    ...source,
    dataState: 'DATA_MISSING',
    degraded: true,
    dataMissing: [DEMO_MISSING_SIGNAL],
    asOf: null,
    isDemo: true,
    dataHealth: [
      { label: 'Demo fixture', status: 'degraded', value: 'NOT_SOURCE_BACKED' },
      ...source.dataHealth.map((item) => ({
        ...item,
        status: item.status === 'failed' ? 'failed' : 'degraded',
        value: item.value ? `DEMO ${item.value}` : 'DEMO',
      }) satisfies DataHealthItem),
    ],
    news: source.news.map((item) => ({
      ...item,
      trustLevel: 'UNKNOWN-UNCLASSIFIED',
      source: `DEMO FIXTURE: ${item.source}`,
      dataState: 'DATA_MISSING',
      degraded: true,
      dataMissing: [DEMO_MISSING_SIGNAL],
      sourceId: null,
      sourceKind: null,
      sourceLabel: 'unknown_unclassified',
      evidenceLabels: ['unknown_unclassified'],
      resolvable: false,
      resolver: 'none',
      sourceUrl: null,
      chatBlockedReason: 'UNRESOLVABLE_SOURCE',
      isDemo: true,
    })),
  };
}

function mapNewsItem(item: CockpitHomeNewsItemContract): NewsItem {
  const handoff = buildCockpitHomeChatHandoff(item, {
    initialPrompt: `Analyze Home source: ${item.headline}`,
  });

  return {
    id: item.id,
    ticker: item.ticker || 'SOURCE',
    headline: item.headline,
    timestamp: formatMelbourneTime(item.observed_at ?? item.state.as_of),
    source: item.source_name || item.evidence.title || 'Backend source',
    trustLevel: cockpitHomeSourceLabelToTrustLevel(item.evidence.source_label),
    relevance: item.relevance,
    dataState: item.state.data_state,
    degraded: item.state.degraded,
    dataMissing: item.state.data_missing,
    sourceId: item.evidence.source_id,
    sourceKind: item.evidence.source_kind,
    sourceLabel: item.evidence.source_label,
    evidenceLabels: item.evidence.evidence_labels,
    resolvable: item.evidence.resolvable,
    resolver: item.evidence.resolver,
    sourceUrl: item.evidence.url,
    chatBlockedReason: handoff.blocked_reason,
  };
}

function mapMarketMover(item: CockpitHomeMarketMoverContract): MarketMover {
  return {
    ticker: item.ticker,
    price: item.price ?? 0,
    change: item.change ?? 0,
    changePercent: item.change_percent ?? 0,
    reason: item.reason ?? item.title,
  };
}

function isRenderableMarketMover(item: CockpitHomeMarketMoverContract): boolean {
  return (
    !cockpitHomeHasDataMissing(item.state) &&
    Boolean(item.ticker) &&
    item.price !== null &&
    item.change !== null &&
    item.change_percent !== null
  );
}

function isPartialMarketMoverSignal(item: CockpitHomeMarketMoverContract): boolean {
  return item.evidence.source_label === 'operational_trace' && item.state.data_state === 'PARTIAL';
}

function mapDataHealthItem(item: {
  label: string;
  value: string | null;
  data_state: CockpitHomeDataState;
}): DataHealthItem {
  return {
    label: item.label,
    status:
      item.data_state === 'READY'
        ? 'healthy'
        : item.data_state === 'PARTIAL'
          ? 'degraded'
          : item.data_state === 'DEGRADED'
            ? 'degraded'
            : 'failed',
    value: item.value ?? item.data_state,
  };
}

function systemStatusFromResponse(response: CockpitHomeBffResponse): 'operational' | 'partial' | 'degraded' | 'data_missing' {
  if (response.data_state === 'READY') {
    return 'operational';
  }
  if (response.data_state === 'PARTIAL') {
    return 'partial';
  }
  if (response.data_state === 'DEGRADED') {
    return 'degraded';
  }
  return 'data_missing';
}

function sectionState(section: string, response: CockpitHomeBffResponse): CockpitHomeDataState {
  if (section === 'news') {
    if (response.news.length === 0) {
      return response.data_missing.some((signal) => signal.section === 'news') ? 'DATA_MISSING' : 'READY';
    }
    return response.news.some((item) => item.state.data_state !== 'READY') ? 'PARTIAL' : 'READY';
  }
  if (section === 'market_movers') {
    return response.market_movers.some((item) => item.state.data_state !== 'DATA_MISSING') ? 'PARTIAL' : 'DATA_MISSING';
  }
  if (section === 'attention_queue') {
    return response.attention_queue_state.data_state;
  }
  return 'DATA_MISSING';
}

function sectionSignals(section: string, response: CockpitHomeBffResponse): CockpitHomeDataMissingSignal[] {
  return uniqueDataMissingSignals([
    ...response.data_missing.filter((signal) => signal.section === section),
    ...(section === 'market_movers' ? response.market_movers.flatMap((item) => item.state.data_missing) : []),
    ...(section === 'attention_queue' ? response.attention_queue_state.data_missing : []),
    ...(section === 'attention_queue' ? response.attention_queue.flatMap((item) => item.state.data_missing) : []),
    ...(section === 'news' ? response.news.flatMap((item) => item.state.data_missing) : []),
  ]);
}

function stateTextColor(state: CockpitHomeDataState): string {
  if (state === 'READY') {
    return 'text-green-500';
  }
  if (state === 'PARTIAL') {
    return 'text-amber-500';
  }
  return 'text-red-500';
}

function uniqueDataMissingSignals(signals: CockpitHomeDataMissingSignal[]): CockpitHomeDataMissingSignal[] {
  const seen = new Set<string>();
  return signals.filter((signal) => {
    const identity = dataMissingSignalIdentity(signal);
    if (seen.has(identity)) {
      return false;
    }
    seen.add(identity);
    return true;
  });
}

function dataMissingSignalKey(signal: CockpitHomeDataMissingSignal, index: number): string {
  return `${dataMissingSignalIdentity(signal)}:${index}`;
}

function dataMissingSignalIdentity(signal: CockpitHomeDataMissingSignal): string {
  return [
    signal.section,
    signal.code,
    signal.message,
    signal.source_id ?? '',
    signal.evidence_id ?? '',
    signal.source_label ?? '',
  ].join('|');
}

function formatMelbourneTime(value: string | null | undefined): string {
  if (!value) {
    return 'DATA_MISSING';
  }
  const timestamp = Date.parse(value);
  if (!Number.isFinite(timestamp)) {
    return value;
  }
  return new Intl.DateTimeFormat('en-AU', {
    timeZone: 'Australia/Melbourne',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(timestamp));
}

function formatCurrency(value: number, currency: string | null): string {
  if (!currency) {
    return value.toLocaleString(undefined, {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    });
  }
  try {
    return value.toLocaleString(undefined, {
      style: 'currency',
      currency,
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    });
  } catch {
    return `${currency} ${value.toLocaleString(undefined, {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    })}`;
  }
}

function formatSignedCurrency(value: number, currency: string | null): string {
  const formatted = formatCurrency(Math.abs(value), currency);
  return `${value >= 0 ? '+' : '-'}${formatted}`;
}

function formatSignedPercent(value: number): string {
  return `${value >= 0 ? '+' : ''}${value}%`;
}
