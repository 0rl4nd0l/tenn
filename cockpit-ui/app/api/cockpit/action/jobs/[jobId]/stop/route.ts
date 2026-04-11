const backendUrl = (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000').replace(/\/$/, '')

export const runtime = 'nodejs'

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

export async function POST(
  req: Request,
  context: { params: Promise<{ jobId: string }> },
): Promise<Response> {
  try {
    const { jobId } = await context.params
    const requestHeaders = copyRequestHeaders(new Headers(req.headers))
    const upstream = await fetch(`${backendUrl}/api/cockpit/action/jobs/${encodeURIComponent(jobId)}/stop`, {
      method: 'POST',
      headers: requestHeaders,
      cache: 'no-store',
    })

    const responseText = await upstream.text()
    return new Response(responseText, {
      status: upstream.status,
      headers: { 'content-type': upstream.headers.get('content-type') || 'application/json' },
    })
  } catch (error) {
    const errorMsg = error instanceof Error ? error.message : 'Unknown error'
    return Response.json(
      {
        error: 'Failed to stop cockpit action job',
        detail: errorMsg,
        backend: backendUrl,
      },
      { status: 502 },
    )
  }
}
