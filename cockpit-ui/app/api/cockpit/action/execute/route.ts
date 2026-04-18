const backendUrl = (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000').replace(/\/$/, '')
const ACTION_TIMEOUT_MS = 15 * 60 * 1000
const JOB_POLL_INTERVAL_MS = 1500
const NON_QUEUED_ACTION_IDS = new Set(['show_candlestick', 'launch_marketplace_browser'])

export const runtime = 'nodejs'
export const maxDuration = 900

function copyRequestHeaders(headers: Headers): Headers {
  const copied = new Headers()
  headers.forEach((value, key) => {
    const normalized = key.toLowerCase()
    if (normalized === 'host' || normalized === 'content-length') {
      return
    }
    copied.set(key, value)
  })
  return copied
}

function sleep(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms))
}

async function pollQueuedAction(jobId: string, headers: Headers, signal: AbortSignal): Promise<Response> {
  while (!signal.aborted) {
    const statusResponse = await fetch(`${backendUrl}/api/cockpit/action/jobs/${jobId}`, {
      method: 'GET',
      headers,
      signal,
      cache: 'no-store',
    })

    if (!statusResponse.ok) {
      const text = await statusResponse.text()
      return new Response(text, {
        status: statusResponse.status,
        headers: { 'content-type': statusResponse.headers.get('content-type') || 'application/json' },
      })
    }

    const statusPayload = await statusResponse.json() as {
      status?: string
      action_id?: string
      result?: string | null
      exit_code?: number | null
    }

    const jobStatus = String(statusPayload.status || '')
    if (jobStatus === 'success') {
      return Response.json({
        ok: true,
        action_id: statusPayload.action_id || '',
        result: statusPayload.result || '',
        exit_code: statusPayload.exit_code ?? 0,
      })
    }

    if (jobStatus === 'failed') {
      return Response.json({
        error: 'Cockpit action failed',
        detail: statusPayload.result || 'Action failed',
      }, { status: 500 })
    }

    await sleep(JOB_POLL_INTERVAL_MS)
  }

  return Response.json(
    {
      error: 'Cockpit action timed out waiting for backend response',
      detail: `Request exceeded ${Math.round(ACTION_TIMEOUT_MS / 1000)}s`,
    },
    { status: 504 },
  )
}

export async function POST(req: Request): Promise<Response> {
  const controller = new AbortController()
  const timeout = setTimeout(() => controller.abort(), ACTION_TIMEOUT_MS)

  try {
    const requestHeaders = copyRequestHeaders(req.headers)
    const rawBody = await req.text()
    const parsedBody = JSON.parse(rawBody || '{}') as {
      action_id?: string
      return_job_handle?: boolean
    }
    const shouldQueue = !NON_QUEUED_ACTION_IDS.has(String(parsedBody.action_id || ''))
    const backendBody = JSON.stringify({
      ...parsedBody,
      wait: !shouldQueue,
    })
    const upstream = await fetch(`${backendUrl}/api/cockpit/action/execute`, {
      method: 'POST',
      headers: requestHeaders,
      body: backendBody,
      signal: controller.signal,
      cache: 'no-store',
    })

    if (shouldQueue && upstream.ok) {
      const payload = await upstream.json().catch(() => null) as { queued?: boolean; job_id?: string } | null
      if (payload?.queued && payload.job_id) {
        if (parsedBody.return_job_handle) {
          return Response.json(payload)
        }
        return await pollQueuedAction(payload.job_id, requestHeaders, controller.signal)
      }
      return Response.json(
        {
          error: 'Backend did not return a queued job handle',
          detail: 'Missing job_id for queued cockpit action',
        },
        { status: 502 },
      )
    }

    const responseText = await upstream.text()
    const contentType = upstream.headers.get('content-type') || 'application/json'

    return new Response(responseText, {
      status: upstream.status,
      headers: { 'content-type': contentType },
    })
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') {
      return Response.json(
        {
          error: 'Cockpit action timed out waiting for backend response',
          detail: `Request exceeded ${Math.round(ACTION_TIMEOUT_MS / 1000)}s`,
        },
        { status: 504 },
      )
    }

    if (error instanceof SyntaxError) {
      return Response.json(
        {
          error: 'Invalid cockpit action payload',
          detail: error.message,
        },
        { status: 400 },
      )
    }

    const errorMsg = error instanceof Error ? error.message : 'Unknown error'
    return Response.json(
      {
        error: 'Failed to reach backend action endpoint',
        detail: errorMsg,
        backend: backendUrl,
      },
      { status: 502 },
    )
  } finally {
    clearTimeout(timeout)
  }
}
