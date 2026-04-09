const backendUrl = (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000').replace(/\/$/, '')
const ACTION_TIMEOUT_MS = 15 * 60 * 1000

export const runtime = 'nodejs'
export const maxDuration = 900

function copyRequestHeaders(headers: Headers): Headers {
  const copied = new Headers()
  headers.forEach((value, key) => {
    if (key.toLowerCase() === 'host') {
      return
    }
    copied.set(key, value)
  })
  return copied
}

export async function POST(req: Request): Promise<Response> {
  const controller = new AbortController()
  const timeout = setTimeout(() => controller.abort(), ACTION_TIMEOUT_MS)

  try {
    const rawBody = await req.text()
    const upstream = await fetch(`${backendUrl}/api/cockpit/action/execute`, {
      method: 'POST',
      headers: copyRequestHeaders(req.headers),
      body: rawBody,
      signal: controller.signal,
      cache: 'no-store',
    })

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
