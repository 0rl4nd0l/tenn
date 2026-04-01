const backendUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
const CHAT_TIMEOUT_MS = 120_000

export const runtime = 'nodejs'

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
  const timeout = setTimeout(() => controller.abort(), CHAT_TIMEOUT_MS)

  try {
    const rawBody = await req.text()
    const upstream = await fetch(`${backendUrl}/chat`, {
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
          type: 'analysis',
          content: {
            answer: 'Chat request timed out waiting for backend response.',
            insights: [],
            supporting_evidence: [],
            confidence: 0,
            sources: [],
            system_status: 'degraded',
          },
        },
        { status: 504 },
      )
    }
    return Response.json({ error: 'Failed to reach backend chat endpoint' }, { status: 502 })
  } finally {
    clearTimeout(timeout)
  }
}
