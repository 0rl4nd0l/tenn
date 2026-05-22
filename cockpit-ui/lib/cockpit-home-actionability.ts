import type {
  CockpitHomeBffResponse,
  CockpitHomeChatHandoff,
  CockpitHomeDataMissingSignal,
  CockpitHomeDataState,
  CockpitHomeSectionKey,
  CockpitHomeState,
  NewsItem,
} from '@/types/cockpit-home';

export type CockpitHomeShellStatus = 'operational' | 'partial' | 'degraded' | 'data_missing';

export type HomeSourceActionabilityReason =
  | 'SOURCE_READY'
  | 'DATA_MISSING'
  | 'DEGRADED'
  | 'DEMO_ONLY'
  | 'UNRESOLVABLE_SOURCE';

export interface HomeSourceActionability {
  reason: HomeSourceActionabilityReason;
  label: string;
  detail: string;
  tone: 'ready' | 'warning' | 'error';
  canInspect: boolean;
  canAttachToChat: boolean;
  blockedReason?: CockpitHomeChatHandoff['blocked_reason'];
}

export type UsefulNowAction = {
  id: string;
  kind: 'attention' | 'source' | 'blocker' | 'ready';
  title: string;
  detail: string;
  state: CockpitHomeDataState;
  meta: string[];
  href?: string | null;
  newsItem?: NewsItem;
  actionability?: HomeSourceActionability;
};

export function getHomeSourceActionability(item: Pick<
  NewsItem,
  | 'chatBlockedReason'
  | 'dataMissing'
  | 'dataState'
  | 'degraded'
  | 'isDemo'
  | 'resolvable'
  | 'sourceId'
  | 'sourceKind'
>): HomeSourceActionability {
  const canInspect = Boolean(item.resolvable && item.sourceId && !item.isDemo);

  if (item.isDemo) {
    return {
      reason: 'DEMO_ONLY',
      label: 'DEMO ONLY',
      detail: 'Demo fixture only. This item is not source-backed and cannot be attached as evidence.',
      tone: 'warning',
      canInspect: false,
      canAttachToChat: false,
      blockedReason: 'UNRESOLVABLE_SOURCE',
    };
  }

  if (item.chatBlockedReason === 'DATA_MISSING' || item.dataState === 'DATA_MISSING' || (item.dataMissing?.length ?? 0) > 0) {
    return {
      reason: 'DATA_MISSING',
      label: 'DATA_MISSING',
      detail: 'Chat handoff blocked because deterministic Home evidence is missing.',
      tone: 'error',
      canInspect,
      canAttachToChat: false,
      blockedReason: 'DATA_MISSING',
    };
  }

  if (item.chatBlockedReason === 'DEGRADED' || item.dataState === 'DEGRADED' || item.degraded) {
    return {
      reason: 'DEGRADED',
      label: 'DEGRADED',
      detail: 'Chat handoff blocked while this Home source is degraded.',
      tone: 'error',
      canInspect,
      canAttachToChat: false,
      blockedReason: 'DEGRADED',
    };
  }

  if (item.chatBlockedReason || !item.resolvable || !item.sourceId || !item.sourceKind) {
    return {
      reason: 'UNRESOLVABLE_SOURCE',
      label: item.chatBlockedReason ?? 'UNRESOLVABLE',
      detail: 'Chat handoff blocked because the backend did not provide a resolvable source identity.',
      tone: 'warning',
      canInspect,
      canAttachToChat: false,
      blockedReason: item.chatBlockedReason ?? 'UNRESOLVABLE_SOURCE',
    };
  }

  return {
    reason: 'SOURCE_READY',
    label: 'SOURCE',
    detail: 'Backend-resolvable Home source is available for a draft Chat handoff.',
    tone: 'ready',
    canInspect,
    canAttachToChat: true,
  };
}

export function buildHomeChatDraftHref(prompt: string, attachedItem: NewsItem | null): string {
  const params = new URLSearchParams({ prompt });
  if (attachedItem && getHomeSourceActionability(attachedItem).canAttachToChat) {
    params.set('source_id', String(attachedItem.sourceId));
    params.set('source_kind', String(attachedItem.sourceKind));
    params.set('source_title', attachedItem.headline);
  }
  return `/full-chat?${params.toString()}`;
}

export function getHomeAssistantContext(
  mode: 'live' | 'demo',
  status: CockpitHomeShellStatus,
) {
  if (mode === 'demo') {
    return {
      label: 'Home context',
      stateLabel: 'DEMO',
      toneClass: 'text-amber-500',
      message: 'Demo Home is visible but not source-backed. Full Chat opens a draft without attaching Home evidence.',
      defaultPrompt: 'Summarize visible demo-state limitations.',
      secondaryPrompt: 'What evidence would be required for live analysis?',
    };
  }

  if (status === 'data_missing') {
    return {
      label: 'Home context',
      stateLabel: 'DATA_MISSING',
      toneClass: 'text-amber-500',
      message: 'Home context is currently DATA_MISSING. Full Chat opens a draft without Home-side evidence attachment.',
      defaultPrompt: 'What Home evidence is currently missing?',
      secondaryPrompt: 'List the checks needed before analysis.',
    };
  }

  if (status === 'degraded') {
    return {
      label: 'Home context',
      stateLabel: 'DEGRADED',
      toneClass: 'text-red-500',
      message: 'Home context is degraded. Use Full Chat for a draft and verify source coverage before acting.',
      defaultPrompt: 'Summarize visible Home gaps before analysis.',
      secondaryPrompt: 'What source coverage should I verify next?',
    };
  }

  if (status === 'partial') {
    return {
      label: 'Home context',
      stateLabel: 'PARTIAL',
      toneClass: 'text-cyan-500',
      message: 'Home has partial context available. Full Chat opens a draft for the visible, source-labeled Home state.',
      defaultPrompt: "Summarize today's available Home context.",
      secondaryPrompt: 'Show the main gaps before acting.',
    };
  }

  return {
    label: 'Home context',
    stateLabel: 'READY',
    toneClass: 'text-cyan-500',
    message: 'Home context is available. You can ask for a draft summary, portfolio impact, or source review.',
    defaultPrompt: "Summarize today's Home context.",
    secondaryPrompt: 'Show my top portfolio risks.',
  };
}

export function buildHomeUsefulNowActions(
  response: CockpitHomeBffResponse,
  news: NewsItem[],
  attentionItems: CockpitHomeState['attentionQueue'],
): UsefulNowAction[] {
  const actions: UsefulNowAction[] = [];
  const attentionByPriority = [...attentionItems].sort(
    (left, right) => priorityRank(left.priority) - priorityRank(right.priority),
  );

  for (const item of attentionByPriority) {
    actions.push({
      id: `attention:${item.id}`,
      kind: 'attention',
      title: `Review ${item.label}`,
      detail: item.description,
      state: 'READY',
      meta: [item.priority, item.status, item.source].filter(Boolean) as string[],
      href: safeInternalHomeRoute(item.targetRoute),
    });
    if (actions.length >= 1) {
      break;
    }
  }

  const sourceAction = [...news]
    .map((item) => ({ item, actionability: getHomeSourceActionability(item) }))
    .filter(({ actionability }) => actionability.canAttachToChat)
    .sort((left, right) => relevanceRank(left.item.relevance) - relevanceRank(right.item.relevance))[0];
  if (sourceAction && actions.length < 3) {
    actions.push({
      id: `source:${sourceAction.item.id}`,
      kind: 'source',
      title: `Inspect source: ${sourceAction.item.headline}`,
      detail: sourceAction.item.source,
      state: sourceAction.item.dataState ?? 'READY',
      meta: [
        sourceAction.item.relevance,
        sourceAction.item.trustLevel,
        sourceAction.actionability.label,
      ],
      newsItem: sourceAction.item,
      actionability: sourceAction.actionability,
    });
  }

  for (const signal of prioritizedSignals(response)) {
    if (actions.length >= 3) {
      break;
    }
    actions.push({
      id: `blocker:${dataMissingSignalIdentity(signal)}`,
      kind: 'blocker',
      title: `${sectionDisplayName(signal.section)} gap`,
      detail: signal.message,
      state: homeSectionState(signal.section, response),
      meta: [signal.code, signal.source_label ?? 'missing_required_evidence'],
    });
  }

  if (actions.length === 0) {
    actions.push({
      id: 'home-ready:no-current-actions',
      kind: 'ready',
      title: 'No urgent Home action',
      detail: 'The current Home response has no queued attention items or missing-data blockers.',
      state: 'READY',
      meta: ['READY'],
    });
  }

  return actions.slice(0, 3);
}

export function homeSectionState(section: string, response: CockpitHomeBffResponse): CockpitHomeDataState {
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
  const directHealth = response.data_health.find((item) => item.section === section);
  if (directHealth) {
    return directHealth.data_state;
  }
  const directSignal = response.data_missing.find((signal) => signal.section === section);
  if (directSignal) {
    return response.data_state === 'READY' ? 'PARTIAL' : response.data_state;
  }
  return 'DATA_MISSING';
}

export function safeInternalHomeRoute(route: string | null | undefined): string | null {
  const value = String(route || '').trim();
  if (!value.startsWith('/') || value.startsWith('//')) {
    return null;
  }
  return value;
}

function prioritizedSignals(response: CockpitHomeBffResponse): CockpitHomeDataMissingSignal[] {
  const sectionOrder = new Map<CockpitHomeSectionKey, number>(
    [
      'portfolio',
      'news',
      'attention_queue',
      'market_movers',
      'session_summary',
      'theme_candidates',
      'tomorrow_prep',
      'market_session',
      'data_health',
    ].map((section, index) => [section as CockpitHomeSectionKey, index]),
  );

  return uniqueDataMissingSignals(response.data_missing)
    .filter((signal) => signal.code.trim())
    .sort((left, right) => {
      const leftRank = sectionOrder.get(left.section) ?? sectionOrder.size;
      const rightRank = sectionOrder.get(right.section) ?? sectionOrder.size;
      return leftRank - rightRank || left.code.localeCompare(right.code);
    });
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

function sectionDisplayName(section: CockpitHomeSectionKey): string {
  return section
    .split('_')
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ');
}

function priorityRank(priority: CockpitHomeState['attentionQueue'][number]['priority']): number {
  if (priority === 'high') {
    return 0;
  }
  if (priority === 'medium') {
    return 1;
  }
  return 2;
}

function relevanceRank(relevance: NewsItem['relevance']): number {
  if (relevance === 'high') {
    return 0;
  }
  if (relevance === 'medium') {
    return 1;
  }
  return 2;
}
