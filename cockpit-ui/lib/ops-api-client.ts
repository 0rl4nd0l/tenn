// API client for /api/ops/ endpoints

import { apiFetch } from './api-client'
import type {
  OpsJobListResponse,
  OpsJobRun,
  OpsJobEventListResponse,
  OpsJobArtifactListResponse,
} from './ops-types'

export async function listOpsJobs(params?: {
  status?: string
  job_type?: string
  ticker?: string
  limit?: number
  offset?: number
}): Promise<OpsJobListResponse> {
  const searchParams = new URLSearchParams()
  if (params?.status) searchParams.set('status', params.status)
  if (params?.job_type) searchParams.set('job_type', params.job_type)
  if (params?.ticker) searchParams.set('ticker', params.ticker)
  if (params?.limit) searchParams.set('limit', String(params.limit))
  if (params?.offset) searchParams.set('offset', String(params.offset))
  const qs = searchParams.toString()
  return apiFetch<OpsJobListResponse>(`/api/ops/jobs${qs ? `?${qs}` : ''}`)
}

export async function listActiveOpsJobs(): Promise<OpsJobListResponse> {
  return apiFetch<OpsJobListResponse>('/api/ops/jobs/active')
}

export async function getOpsJob(jobId: string): Promise<OpsJobRun> {
  return apiFetch<OpsJobRun>(`/api/ops/jobs/${jobId}`)
}

export async function getOpsJobEvents(
  jobId: string,
  limit?: number,
): Promise<OpsJobEventListResponse> {
  const qs = limit ? `?limit=${limit}` : ''
  return apiFetch<OpsJobEventListResponse>(`/api/ops/jobs/${jobId}/events${qs}`)
}

export async function getOpsJobArtifacts(
  jobId: string,
): Promise<OpsJobArtifactListResponse> {
  return apiFetch<OpsJobArtifactListResponse>(`/api/ops/jobs/${jobId}/artifacts`)
}
