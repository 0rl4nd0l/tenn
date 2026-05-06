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

export type RealGoldEvalTaskProgressEvent = {
  stage?: string
  status?: string
  message?: string
  timestamp?: number
  document_id?: string
  completed?: number
  total?: number
  trust_outcome?: string | null
  failed_metric_count?: number | null
  total_accuracy?: number | null
  context_accuracy?: number | null
}

export type RealGoldEvalTaskResponse = {
  task_id: string
  status: 'pending' | 'running' | 'completed' | 'failed' | string
  created_at?: number
  updated_at?: number
  result?: RealGoldEvalResponse | null
  error?: string | null
  progress?: RealGoldEvalTaskProgressEvent[]
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

export type MetricCoverageClassification =
  | 'CONFIRMED_SOURCE_EVIDENCED'
  | 'CANDIDATE_REVIEW_REQUIRED'
  | 'AMBIGUOUS_OR_DERIVED'
  | 'UNSUPPORTED'

export type MetricCoverageReviewDecision =
  | 'CONFIRM_SOURCE_EVIDENCE'
  | 'REPAIR_SOURCE_MAPPING'
  | 'REJECT_BAD_SOURCE_MAPPING'
  | 'MARK_AMBIGUOUS_OR_DERIVED'
  | 'KEEP_CANDIDATE_PENDING_REVIEW'
  | 'DATA_MISSING'

export type ConfirmedMetricCoverageRow = {
  fixture_id: string
  document_id: string
  fixture: string
  ticker?: string | null
  period: {
    period_type?: string | null
    period_end?: string | null
  }
  metric_name: string
  canonical_field?: string | null
  expectation_type: string
  expected_value: number | null
  expected_null: boolean
  currency?: string | null
  scale?: string | null
  source_pdf_path?: string | null
  source_pdf_exists?: boolean | null
  source_pdf_status: 'present' | 'missing' | 'not_declared' | string
  source_pdf_present?: boolean
  source_page?: number | null
  source_page_present?: boolean
  source_table?: string | null
  source_table_present?: boolean
  source_row?: string | null
  source_row_present?: boolean
  precise_source_evidence?: boolean
  broad_or_suspect_source_evidence?: boolean
  human_review_required?: boolean
  blocked_ambiguous?: boolean
  source_evidence_status: string
  classification: MetricCoverageClassification | string
  schema_support: {
    schema_supported: boolean
    extractor_output_supported: boolean
    evaluator_supported: boolean
  }
  ambiguity_reason?: string | null
  recommended_action: string
  production_metric_tier: string
  review_status: string
  evaluation_status?: string | null
  actual_value?: number | null
  score?: number | null
  reason?: string | null
}

export type GitStatusShortSummary = {
  line_count: number
  entries: string[]
  truncated: boolean
}

export type AppRuntimeContext = {
  cwd?: string | null
  workspace_root?: string | null
  project_root?: string | null
  backend_root?: string | null
  running_in_docker?: boolean | null
  [key: string]: string | boolean | number | null | undefined
}

export type ConfirmedMetricCoverageSummary = {
  profile: string
  fixture_count: number
  total_expectations: number
  scored_count: number
  candidate_review_required_count: number
  ambiguous_count: number
  unsupported_count: number
  missing_source_evidence_count: number
  missing_source_pdf_count: number
  classification_counts: Record<string, number>
  review_status_counts: Record<string, number>
  generated_at?: string | null
  head?: string | null
  branch?: string | null
  git_available?: boolean | null
  git_head?: string | null
  git_head_short?: string | null
  git_branch?: string | null
  git_dirty?: boolean | null
  git_status_short_summary?: GitStatusShortSummary | null
  git_unavailable_reason?: string | null
  fixture_dir?: string | null
  artifact_path?: string | null
  app_runtime_context?: AppRuntimeContext | null
  canonical_core_unchanged: boolean
  expanded_required_unchanged: boolean
  canonical_labels_mutated: boolean
}

export type ConfirmedMetricCoverageArtifacts = {
  artifact_dir?: string | null
  json_path?: string | null
  markdown_path?: string | null
}

export type ConfirmedMetricCoveragePacket = {
  status: string
  profile: string
  generated_at?: string | null
  head?: string | null
  branch?: string | null
  git_available?: boolean | null
  git_head?: string | null
  git_head_short?: string | null
  git_branch?: string | null
  git_dirty?: boolean | null
  git_status_short_summary?: GitStatusShortSummary | null
  git_unavailable_reason?: string | null
  fixtures_dir?: string | null
  fixture_dir?: string | null
  artifact_path?: string | null
  app_runtime_context?: AppRuntimeContext | null
  summary: ConfirmedMetricCoverageSummary | null
  rows: ConfirmedMetricCoverageRow[]
  count?: number
  artifacts?: ConfirmedMetricCoverageArtifacts | null
  errors?: string[]
  warnings?: string[]
  scorecard?: Record<string, unknown>
  copy?: Record<string, string>
}

export type VerificationTab = 'review' | 'gold-eval' | 'metric-coverage' | 'runs' | 'verify'

export type VerificationProgressLevel = 'info' | 'success' | 'warning' | 'error'

export type VerificationProgressEntry = {
  id: string
  timestamp: string
  level: VerificationProgressLevel
  scope: string
  message: string
  detail?: string
}
