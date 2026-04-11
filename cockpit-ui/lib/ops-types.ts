// Operational job-status types — mirrors backend /api/ops/ response models

export type OpsJobStatus = 'pending' | 'running' | 'succeeded' | 'failed' | 'cancelled'

export type OpsJobType = 'extraction' | 'backfill' | 'download' | 'embedding'

export interface OpsJobRun {
  job_id: string
  job_type: string
  job_family: string
  status: OpsJobStatus
  phase: string | null
  title: string
  summary: string | null
  trigger_source: string | null
  entity_scope: string | null
  ticker: string | null
  total_items: number
  succeeded_items: number
  failed_items: number
  skipped_items: number
  warning_count: number
  error_count: number
  current_item_label: string | null
  queued_at: string
  started_at: string | null
  updated_at: string
  completed_at: string | null
  elapsed_ms: number
  metadata: Record<string, unknown> | null
}

export interface OpsJobEvent {
  event_id: string
  job_id: string
  event_type: string
  phase: string | null
  message: string
  progress_current: number | null
  progress_total: number | null
  progress_pct: number | null
  timestamp: string
  payload: Record<string, unknown> | null
}

export interface OpsJobArtifact {
  artifact_id: string
  job_id: string
  artifact_type: string
  artifact_path: string | null
  artifact_label: string
  metadata: Record<string, unknown> | null
  created_at: string
}

export interface OpsJobListResponse {
  items: OpsJobRun[]
  total: number
}

export interface OpsJobEventListResponse {
  items: OpsJobEvent[]
}

export interface OpsJobArtifactListResponse {
  items: OpsJobArtifact[]
}

export interface OpsSSEEvent {
  event_type: string
  job_id: string
  timestamp: string
  data: {
    message: string
    phase?: string | null
    progress_current?: number | null
    progress_total?: number | null
    progress_pct?: number | null
    [key: string]: unknown
  }
}
