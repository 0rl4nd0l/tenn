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

type GpuSnapshot = {
  uuid: string | null
  name: string
  temp_c: number | null
  util_percent: number | null
  mem_used_mib: number | null
  mem_total_mib: number | null
}

type GpuProcessSnapshot = {
  gpu_uuid: string | null
  gpu_name: string | null
  pid: number
  process_name: string
  used_gpu_memory_mib: number | null
  task_label: string
  command: string | null
}

function parseMetric(value: string): number | null {
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : null
}

function readPort(command: string): string | null {
  const spaced = command.match(/--port\s+(\d+)/)
  if (spaced) return spaced[1]
  const equals = command.match(/--port=(\d+)/)
  if (equals) return equals[1]
  return null
}

function describeGpuTask(processName: string, command: string | null): string {
  const normalizedName = processName.trim() || 'process'
  const normalizedCommand = (command || '').trim()
  const lowered = normalizedCommand.toLowerCase()

  if (lowered.includes('llama-server')) {
    const port = readPort(normalizedCommand)
    if (port === '8002') return 'Extraction runtime'
    if (port === '8001') return 'Chat/router runtime'
    return 'llama.cpp runtime'
  }
  if (lowered.includes('ollama')) return 'Ollama runtime'
  if (lowered.includes('python') || lowered.includes('uv')) {
    if (lowered.includes('full_history_ticker_sync')) return 'Ticker sync task'
    if (lowered.includes('pipeline')) return 'Pipeline task'
    if (lowered.includes('extraction')) return 'Extraction task'
    return 'Python task'
  }

  return normalizedName
}

async function readProcessCommands(pids: number[]): Promise<Map<number, string>> {
  if (pids.length === 0) return new Map()

  try {
    const { stdout } = await execFileAsync(
      'ps',
      ['-o', 'pid=,args=', '-p', pids.join(',')],
      { timeout: 3000 },
    )
    const commands = new Map<number, string>()
    for (const rawLine of stdout.split('\n')) {
      const line = rawLine.trim()
      if (!line) continue
      const match = line.match(/^(\d+)\s+(.*)$/)
      if (!match) continue
      const pid = Number(match[1])
      if (!Number.isFinite(pid)) continue
      commands.set(pid, match[2].trim())
    }
    return commands
  } catch {
    return new Map()
  }
}

async function probeGpuProcesses(gpus: GpuSnapshot[]): Promise<GpuProcessSnapshot[]> {
  const gpuNameByUuid = new Map<string, string>()
  for (const gpu of gpus) {
    if (gpu.uuid) gpuNameByUuid.set(gpu.uuid, gpu.name)
  }

  try {
    const { stdout } = await execFileAsync('nvidia-smi', [
      '--query-compute-apps=gpu_uuid,pid,process_name,used_gpu_memory',
      '--format=csv,noheader,nounits',
    ], { timeout: 3000 })

    const rows = stdout
      .split('\n')
      .map((line) => line.trim())
      .filter(Boolean)

    const parsed = rows
      .map((line) => {
        const parts = line.split(',').map((part) => part.trim())
        if (parts.length < 4) return null
        const [gpuUuidRaw, pidRaw, processNameRaw, usedMemoryRaw] = parts
        const pid = Number(pidRaw)
        if (!Number.isFinite(pid)) return null
        return {
          gpu_uuid: gpuUuidRaw || null,
          pid,
          process_name: processNameRaw || 'process',
          used_gpu_memory_mib: parseMetric(usedMemoryRaw),
        }
      })
      .filter((row): row is { gpu_uuid: string | null; pid: number; process_name: string; used_gpu_memory_mib: number | null } => row !== null)

    const commands = await readProcessCommands(parsed.map((row) => row.pid))
    return parsed.map((row) => {
      const command = commands.get(row.pid) ?? null
      return {
        ...row,
        gpu_name: row.gpu_uuid ? (gpuNameByUuid.get(row.gpu_uuid) ?? null) : null,
        command,
        task_label: describeGpuTask(row.process_name, command),
      }
    })
  } catch {
    return []
  }
}

async function probeHostGpu(): Promise<ServiceHealth> {
  const start = Date.now()
  try {
    const { stdout } = await execFileAsync('nvidia-smi', [
      '--query-gpu=uuid,name,temperature.gpu,utilization.gpu,memory.used,memory.total',
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
        if (parts.length < 6) return null
        const [uuidRaw, name, tempRaw, utilRaw, usedRaw, totalRaw] = parts
        return {
          uuid: uuidRaw || null,
          name: name || 'GPU',
          temp_c: parseMetric(tempRaw),
          util_percent: parseMetric(utilRaw),
          mem_used_mib: parseMetric(usedRaw),
          mem_total_mib: parseMetric(totalRaw),
        }
      })
      .filter((gpu): gpu is GpuSnapshot => gpu !== null)

    if (gpus.length === 0) {
      return {
        name: 'gpu',
        status: 'unknown',
        response_time_ms: Date.now() - start,
        error: 'unable to parse GPU status',
      }
    }

    const processes = await probeGpuProcesses(gpus)

    return {
      name: 'gpu',
      status: 'healthy',
      response_time_ms: Date.now() - start,
      details: { gpus, processes },
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
