import { execFile } from 'node:child_process'
import { promisify } from 'node:util'

const backendUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
const execFileAsync = promisify(execFile)

export const runtime = 'nodejs'

type ServiceHealth = {
  name: string
  status: 'healthy' | 'degraded' | 'down' | 'unknown'
  endpoint?: string | null
  response_time_ms?: number | null
  error?: string | null
  details?: Record<string, unknown> | null
}

async function probeHostGpu(): Promise<ServiceHealth> {
  const start = Date.now()
  try {
    const { stdout } = await execFileAsync('nvidia-smi', [
      '--query-gpu=name,utilization.gpu,memory.used,memory.total',
      '--format=csv,noheader,nounits',
    ], { timeout: 3000 })

    const lines = stdout
      .split('\n')
      .map((line) => line.trim())
      .filter(Boolean)

    if (lines.length === 0) {
      return {
        name: 'gpu',
        status: 'unknown',
        response_time_ms: Date.now() - start,
        error: 'no GPU devices reported',
      }
    }

    const gpus = lines
      .map((line) => {
        const parts = line.split(',').map((part) => part.trim())
        if (parts.length < 4) return null
        const [name, utilRaw, usedRaw, totalRaw] = parts
        const util = Number(utilRaw)
        const used = Number(usedRaw)
        const total = Number(totalRaw)
        return {
          name: name || 'GPU',
          util_percent: Number.isFinite(util) ? util : null,
          mem_used_mib: Number.isFinite(used) ? used : null,
          mem_total_mib: Number.isFinite(total) ? total : null,
        }
      })
      .filter(Boolean)

    if (gpus.length === 0) {
      return {
        name: 'gpu',
        status: 'unknown',
        response_time_ms: Date.now() - start,
        error: 'unable to parse GPU status',
      }
    }

    return {
      name: 'gpu',
      status: 'healthy',
      response_time_ms: Date.now() - start,
      details: { gpus },
    }
  } catch (error) {
    const detail = error instanceof Error ? error.message : 'GPU probe failed'
    return {
      name: 'gpu',
      status: 'unknown',
      response_time_ms: Date.now() - start,
      error: detail,
    }
  }
}

export async function GET(): Promise<Response> {
  const upstream = await fetch(`${backendUrl}/api/cockpit/health`, {
    cache: 'no-store',
  })

  const contentType = upstream.headers.get('content-type') || 'application/json'
  const payload = await upstream.json()

  if (!upstream.ok) {
    return new Response(JSON.stringify(payload), {
      status: upstream.status,
      headers: { 'content-type': contentType },
    })
  }

  const gpu = await probeHostGpu()
  const services = Array.isArray(payload.services) ? payload.services : []
  const mergedServices = [
    ...services.filter((service: { name?: string }) => service?.name !== 'gpu'),
    gpu,
  ]

  return Response.json({
    ...payload,
    services: mergedServices,
  })
}
