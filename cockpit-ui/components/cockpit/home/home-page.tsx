'use client'

import { useState } from 'react';
import { MarketStatusHeader } from './market-status-header';
import { DataHealthStrip } from './data-health-strip';
import { MarketPulseCard } from './cards/market-pulse-card';
import { PortfolioImpactCard } from './cards/portfolio-impact-card';
import { NewsAnnouncementsCard } from './cards/news-announcements-card';
import { AttentionQueueCard } from './cards/attention-queue-card';
import { SourceDetailDrawer } from './source-detail-drawer';
import { ContextualAssistant } from './contextual-assistant';
import { SessionSummaryCard } from './cards/session-summary-card';
import { ThemeCandidatesCard } from './cards/theme-candidates-card';
import { MOCK_MARKET_OPEN, MOCK_PRE_MARKET, MOCK_POST_MARKET, MOCK_DEGRADED_STATE } from '@/lib/mock/cockpit-home-fixtures';
import { NewsItem, MarketSessionState } from '@/types/cockpit-home';
import { cn } from '@/lib/utils';
import { AlertCircle } from 'lucide-react';

export function CockpitHomePage() {
  const [activeState, setActiveState] = useState(MOCK_MARKET_OPEN);
  const [selectedItem, setSelectedItem] = useState<NewsItem | null>(null);
  const [assistantContext, setAssistantContext] = useState<NewsItem | null>(null);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);

  const handleSelectItem = (item: NewsItem) => {
    setSelectedItem(item);
    setIsDrawerOpen(true);
  };

  const handleAnalyze = (item: NewsItem) => {
    setAssistantContext(item);
    setIsDrawerOpen(false);
  };

  const setSession = (session: MarketSessionState) => {
    switch (session) {
      case 'OPEN': setActiveState(MOCK_MARKET_OPEN); break;
      case 'PRE_MARKET': setActiveState(MOCK_PRE_MARKET); break;
      case 'POST_MARKET': setActiveState(MOCK_POST_MARKET); break;
      case 'DEGRADED': setActiveState(MOCK_DEGRADED_STATE); break;
    }
  };

  return (
    <div className="flex flex-col h-full bg-background overflow-hidden">
      {activeState.session === 'DEGRADED' && (
        <div className="bg-red-500/20 border-b border-red-500/30 px-4 py-1.5 flex items-center justify-center gap-2 shrink-0">
          <AlertCircle className="w-4 h-4 text-red-500" />
          <span className="text-[11px] font-mono font-bold text-red-500 uppercase tracking-widest">
            Partial Trust State — Data Degraded — Exercise Caution
          </span>
        </div>
      )}

      <MarketStatusHeader
        session={activeState.session}
        melbourneTime={activeState.melbourneTime}
        nextEvent={activeState.nextEvent}
      />

      <DataHealthStrip items={activeState.dataHealth} />

      <main className="flex-1 flex min-h-0 relative">
        {/* Workspace Toolbar (Floating/Subtle) */}
        <div className="absolute top-4 left-6 z-20 flex items-center gap-2">
          {(['PRE_MARKET', 'OPEN', 'POST_MARKET', 'DEGRADED'] as MarketSessionState[]).map((s) => (
            <button
              key={s}
              onClick={() => setSession(s)}
              className={cn(
                "px-3 py-1 rounded-full text-[9px] font-mono border transition-all uppercase tracking-tighter",
                activeState.session === s
                  ? (s === 'DEGRADED' ? "bg-red-500/20 border-red-500/40 text-red-400" : "bg-cyan-500/20 border-cyan-500/40 text-cyan-400")
                  : "bg-accent/40 border-border/60 text-muted-foreground hover:bg-accent/60"
              )}
            >
              {s.replace('_', ' ')}
            </button>
          ))}
        </div>

        <div className="flex-1 overflow-y-auto p-6 pt-14 scroll-smooth">
          <div className="grid grid-cols-12 gap-6 max-w-[1600px] mx-auto">
            {/* Top Row: Market & Portfolio */}
            <div className="col-span-12 lg:col-span-4 min-h-[300px]">
              <MarketPulseCard 
                movers={activeState.marketMovers} 
                overnightLead={activeState.overnightLead}
              />
            </div>
            <div className="col-span-12 lg:col-span-8 min-h-[300px]">
              {activeState.session === 'POST_MARKET' && activeState.sessionSummary ? (
                <SessionSummaryCard 
                  summary={activeState.sessionSummary} 
                  tomorrowPrep={activeState.tomorrowPrep}
                />
              ) : (
                <PortfolioImpactCard portfolio={activeState.portfolio} />
              )}
            </div>

            {/* Middle Row: News & Attention / Themes */}
            <div className="col-span-12 lg:col-span-8">
              <NewsAnnouncementsCard
                news={activeState.news}
                onSelectItem={handleSelectItem}
              />
            </div>
            <div className="col-span-12 lg:col-span-4 flex flex-col gap-6">
              {activeState.session === 'POST_MARKET' && activeState.themeCandidates && (
                <div className="flex-1">
                  <ThemeCandidatesCard themes={activeState.themeCandidates} />
                </div>
              )}
              <div className="flex-1">
                <AttentionQueueCard items={activeState.attentionQueue} />
              </div>
            </div>
          </div>
        </div>

        {/* Right Sidebar: Contextual Assistant */}
        <aside className="w-[380px] border-l border-border shrink-0 hidden xl:block">
          <ContextualAssistant
            attachedItem={assistantContext}
            onClearContext={() => setAssistantContext(null)}
          />
        </aside>
      </main>

      <SourceDetailDrawer
        item={selectedItem}
        isOpen={isDrawerOpen}
        onClose={() => setIsDrawerOpen(false)}
        onAnalyze={handleAnalyze}
      />
    </div>
  );
}
