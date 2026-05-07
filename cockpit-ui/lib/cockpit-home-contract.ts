import type {
  CockpitHomeAttachedSource,
  CockpitHomeBackendSourceLabel,
  CockpitHomeChatHandoff,
  CockpitHomeDataMissingSignal,
  CockpitHomeDeterministicState,
  CockpitHomeEvidenceIdentity,
  CockpitHomeSourceBearingItem,
  CockpitHomeSourceLabelTaxonomyVersion,
  TrustLevel,
} from '@/types/cockpit-home';

export const COCKPIT_HOME_SOURCE_LABEL_TAXONOMY_VERSION: CockpitHomeSourceLabelTaxonomyVersion =
  'source_label_semantics_v1';

export const COCKPIT_HOME_SOURCE_LABEL_DISPLAY = {
  claim_verified: 'CLAIM-VERIFIED',
  context_only: 'CONTEXT-ONLY',
  no_hit: 'NO-HIT',
  operational_trace: 'OPERATIONAL-TRACE',
  local_personal_data: 'LOCAL-PERSONAL-DATA',
  memory_context: 'MEMORY-CONTEXT',
  external_web_context: 'EXTERNAL-WEB-CONTEXT',
  local_news_context: 'LOCAL-NEWS-CONTEXT',
  financial_truth: 'FINANCIAL-TRUTH',
  degraded_runtime: 'DEGRADED-RUNTIME',
  missing_required_evidence: 'MISSING-EVIDENCE',
  unknown_unclassified: 'UNKNOWN-UNCLASSIFIED',
} as const satisfies Record<CockpitHomeBackendSourceLabel, TrustLevel>;

const VALID_SOURCE_LABELS = new Set<CockpitHomeBackendSourceLabel>(
  Object.keys(COCKPIT_HOME_SOURCE_LABEL_DISPLAY) as CockpitHomeBackendSourceLabel[],
);

const DATA_MISSING_LABELS = new Set<CockpitHomeBackendSourceLabel>([
  'missing_required_evidence',
  'no_hit',
]);

const ATTACHMENT_BLOCKING_LABELS = new Set<CockpitHomeBackendSourceLabel>([
  'degraded_runtime',
  'missing_required_evidence',
  'no_hit',
  'operational_trace',
  'unknown_unclassified',
]);

export function normalizeCockpitHomeSourceLabel(
  label: string | null | undefined,
): CockpitHomeBackendSourceLabel {
  const normalized = String(label || '').trim() as CockpitHomeBackendSourceLabel;
  return VALID_SOURCE_LABELS.has(normalized) ? normalized : 'unknown_unclassified';
}

export function cockpitHomeSourceLabelToTrustLevel(
  label: string | null | undefined,
): TrustLevel {
  return COCKPIT_HOME_SOURCE_LABEL_DISPLAY[normalizeCockpitHomeSourceLabel(label)];
}

export function cockpitHomeHasDataMissing(
  state: Pick<CockpitHomeDeterministicState, 'data_state' | 'data_missing'> & {
    evidence?: Pick<CockpitHomeEvidenceIdentity, 'evidence_labels' | 'source_label'> | null;
  },
): boolean {
  if (state.data_state === 'DATA_MISSING') {
    return true;
  }
  if (state.data_missing.length > 0) {
    return true;
  }
  const labels = normalizedEvidenceLabels(state.evidence);
  return labels.some((label) => DATA_MISSING_LABELS.has(label));
}

export function cockpitHomeIsDegraded(
  state: Pick<CockpitHomeDeterministicState, 'data_state' | 'degraded'> & {
    evidence?: Pick<CockpitHomeEvidenceIdentity, 'evidence_labels' | 'source_label'> | null;
  },
): boolean {
  if (state.degraded || state.data_state === 'DEGRADED') {
    return true;
  }
  return normalizedEvidenceLabels(state.evidence).includes('degraded_runtime');
}

export function buildCockpitHomeChatHandoff(
  item: CockpitHomeSourceBearingItem,
  options: {
    initialPrompt?: string;
  } = {},
): CockpitHomeChatHandoff {
  const blockedReason = attachmentBlockedReason(item);
  const attachedSource = blockedReason ? null : toAttachedSource(item.evidence);

  return {
    route: '/full-chat',
    chat_screen: 'ChatScreen',
    ticker: item.ticker ?? null,
    attached_sources: attachedSource ? [attachedSource] : [],
    ...(options.initialPrompt !== undefined ? { initial_prompt: options.initialPrompt } : {}),
    ...(blockedReason ? { blocked_reason: blockedReason } : {}),
  };
}

export function collectCockpitHomeStateIssues(
  state: CockpitHomeDeterministicState,
): CockpitHomeDataMissingSignal[] {
  if (state.data_state === 'DATA_MISSING' && state.data_missing.length === 0) {
    return [
      {
        section: 'data_health',
        code: 'DATA_MISSING_WITHOUT_REASON',
        message: 'DATA_MISSING state must carry at least one deterministic reason.',
      },
    ];
  }
  return [];
}

function attachmentBlockedReason(
  item: CockpitHomeSourceBearingItem,
): CockpitHomeChatHandoff['blocked_reason'] | null {
  if (cockpitHomeHasDataMissing({ ...item.state, evidence: item.evidence })) {
    return 'DATA_MISSING';
  }
  if (cockpitHomeIsDegraded({ ...item.state, evidence: item.evidence })) {
    return 'DEGRADED';
  }
  const labels = normalizedEvidenceLabels(item.evidence);
  if (labels.some((label) => ATTACHMENT_BLOCKING_LABELS.has(label))) {
    return 'UNRESOLVABLE_SOURCE';
  }
  if (!toAttachedSource(item.evidence)) {
    return 'UNRESOLVABLE_SOURCE';
  }
  return null;
}

function toAttachedSource(evidence: CockpitHomeEvidenceIdentity): CockpitHomeAttachedSource | null {
  const sourceId = String(evidence.source_id || '').trim();
  if (!sourceId || !evidence.resolvable || !evidence.source_kind) {
    return null;
  }
  return {
    source_id: sourceId,
    source_kind: evidence.source_kind,
  };
}

function normalizedEvidenceLabels(
  evidence:
    | Pick<CockpitHomeEvidenceIdentity, 'evidence_labels' | 'source_label'>
    | null
    | undefined,
): CockpitHomeBackendSourceLabel[] {
  if (!evidence) {
    return [];
  }
  return Array.from(
    new Set([
      normalizeCockpitHomeSourceLabel(evidence.source_label),
      ...evidence.evidence_labels.map((label) => normalizeCockpitHomeSourceLabel(label)),
    ]),
  );
}
