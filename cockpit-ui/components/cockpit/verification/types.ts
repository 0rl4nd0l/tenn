import type { ExtractionMethod } from '@/lib/cockpit-types'

export type RealGoldEvalMetricResult = {
  status: string
  expected: number | null
  actual: number | null
  reason: string
}

export type RealGoldEvalDocument = {
  document_id: string
  ticker?: string
  extraction_status: string
  extraction_error?: string | null
  context_correct: boolean
  trust_outcome: 'trusted' | 'abstain' | 'quarantine'
  expected_trust: string
  mismatch_reasons: string[]
  review_session_id?: string | null
  review_item_count?: number
  review_reason?: string | null
  metric_results: Record<string, RealGoldEvalMetricResult>
  method_provenance?: {
    requested_method?: ExtractionMethod
    actual_method?: string | null
    strict_method?: boolean
    parser_id?: string | null
    model_id?: string | null
    runtime_id?: string | null
    fallback_used?: boolean
    error_stage?: string | null
  }
}

export type RealGoldEvalResponse = {
  dataset_dir: string
  requested_method?: ExtractionMethod
  strict_method?: boolean
  summary: {
    total_documents: number
    total_accuracy: number
    context_accuracy: number
    trust_matches_expected: number
    metric_status_counts: Record<string, number>
    trust_distribution: Record<string, number>
  }
  documents: RealGoldEvalDocument[]
}

export type ProcessDocumentResponse = {
  mode?: string
  document_id?: string
  run_id?: string
  extraction_status?: string
  method_provenance?: {
    requested_method?: ExtractionMethod
    actual_method?: string | null
    strict_method?: boolean
    parser_id?: string | null
    model_id?: string | null
    runtime_id?: string | null
    fallback_used?: boolean
    error_stage?: string | null
    warnings?: string[]
  }
}

export type SnippetImageState = {
  key: string | null
  status: 'idle' | 'loading' | 'ready' | 'retrying' | 'failed'
  retryAttempted: boolean
  message: string | null
}

export type ActiveExtractionMonitorRun = {
  runId: string
  documentId: string
  requestedMethod: string | null
  strictMethod: boolean | null
  ticker: string | null
  title: string | null
  expiresInSeconds: number | null
}

export type VerificationTab = 'review' | 'gold-eval' | 'runs' | 'verify'
