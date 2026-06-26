// API client for /api/ops/ endpoints

import { SSE } from 'sse.js'
import { apiFetch } from './api-client'
import type {
  OpsJobListResponse,
  OpsJobRun,
  OpsJobEventListResponse,
  OpsJobArtifactListResponse,
} from './ops-types'

const API_KEY = process.env.NEXT_PUBLIC_API_KEY || ''

function withOpsApiKey(headers?: Record<string, string>): Record<string, string> {
  const merged = {
    ...(headers ?? {}),
  }
  if (API_KEY) {
    merged['X-API-Key'] = API_KEY
  }
  return merged
}

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
  return apiFetch<OpsJobListResponse>(
    `/api/ops/jobs${qs ? `?${qs}` : ''}`,
    { headers: withOpsApiKey() },
  )
}

export async function listActiveOpsJobs(): Promise<OpsJobListResponse> {
  return apiFetch<OpsJobListResponse>(
    '/api/ops/jobs/active',
    { headers: withOpsApiKey() },
  )
}

export async function getOpsJob(jobId: string): Promise<OpsJobRun> {
  return apiFetch<OpsJobRun>(
    `/api/ops/jobs/${jobId}`,
    { headers: withOpsApiKey() },
  )
}

export async function getOpsJobEvents(
  jobId: string,
  limit?: number,
): Promise<OpsJobEventListResponse> {
  const qs = limit ? `?limit=${limit}` : ''
  return apiFetch<OpsJobEventListResponse>(
    `/api/ops/jobs/${jobId}/events${qs}`,
    { headers: withOpsApiKey() },
  )
}

export async function getOpsJobArtifacts(
  jobId: string,
): Promise<OpsJobArtifactListResponse> {
  return apiFetch<OpsJobArtifactListResponse>(
    `/api/ops/jobs/${jobId}/artifacts`,
    { headers: withOpsApiKey() },
  )
}

export function createOpsJobStream(jobId?: string): SSE {
  const url = jobId
    ? `/api/ops/stream?job_id=${encodeURIComponent(jobId)}`
    : '/api/ops/stream'
  return new SSE(url, {
    headers: withOpsApiKey(),
    start: false,
  })
}
