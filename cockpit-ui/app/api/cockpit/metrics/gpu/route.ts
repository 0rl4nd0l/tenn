import { execFile } from 'node:child_process'
import { promisify } from 'node:util'

const execFileAsync = promisify(execFile)

export const runtime = 'nodejs'

function parseFloat_(value: string): number | null {
  const cleaned = value.replace(/\[N\/A\]/g, '').trim()
  const parsed = Number(cleaned)
  return Number.isFinite(parsed) ? parsed : null
}

function describeGpuTask(processName: string, command: string | null): string {
  const normalizedName = processName.trim() || 'process'
  const normalizedCommand = (command || '').trim()
  const lowered = normalizedCommand.toLowerCase()

  if (lowered.includes('llama-server')) {
    const portSpaced = normalizedCommand.match(/--port\s+(\d+)/)
    const portEquals = normalizedCommand.match(/--port=(\d+)/)
    const port = portSpaced?.[1] ?? portEquals?.[1] ?? null
    if (port === '8002') return 'Extraction runtime'
    if (port === '8001') return 'Chat/router runtime'
    return 'llama.cpp runtime'
  }
  if (lowered.includes('ollama')) return 'Ollama runtime'
  if (lowered.includes('python') || lowered.includes('uv')) {
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

export async function GET(): Promise<Response> {
  try {
    const { stdout: gpuOut } = await execFileAsync('nvidia-smi', [
      '--query-gpu=uuid,name,temperature.gpu,utilization.gpu,memory.used,memory.total,power.draw,power.limit,fan.speed,utilization.memory,clocks.gr,clocks.mem,pstate',
      '--format=csv,noheader,nounits',
    ], { timeout: 5000 })

    const gpuLines = gpuOut.split('\n').map((l) => l.trim()).filter(Boolean)

    if (gpuLines.length === 0) {
      return Response.json({ details: { gpus: [], processes: [] }, error: 'no GPU devices reported' })
    }

    type GpuRow = {
      uuid: string | null
      name: string
      temp_c: number | null
      util_percent: number | null
      mem_used_mib: number | null
      mem_total_mib: number | null
      power_draw_w: number | null
      power_limit_w: number | null
      fan_speed_pct: number | null
      mem_util_percent: number | null
      clock_gr_mhz: number | null
      clock_mem_mhz: number | null
      pstate: string | null
    }

    const gpus: GpuRow[] = gpuLines.map((line) => {
      const parts = line.split(',').map((p) => p.trim())
      return {
        uuid: parts[0] || null,
        name: parts[1] || 'GPU',
        temp_c: parseFloat_(parts[2] ?? ''),
        util_percent: parseFloat_(parts[3] ?? ''),
        mem_used_mib: parseFloat_(parts[4] ?? ''),
        mem_total_mib: parseFloat_(parts[5] ?? ''),
        power_draw_w: parseFloat_(parts[6] ?? ''),
        power_limit_w: parseFloat_(parts[7] ?? ''),
        fan_speed_pct: parseFloat_(parts[8] ?? ''),
        mem_util_percent: parseFloat_(parts[9] ?? ''),
        clock_gr_mhz: parseFloat_(parts[10] ?? ''),
        clock_mem_mhz: parseFloat_(parts[11] ?? ''),
        pstate: parts[12] || null,
      }
    })

    const gpuNameByUuid = new Map<string, string>()
    for (const gpu of gpus) {
      if (gpu.uuid) gpuNameByUuid.set(gpu.uuid, gpu.name)
    }

    const { stdout: procOut } = await execFileAsync('nvidia-smi', [
      '--query-compute-apps=gpu_uuid,pid,process_name,used_gpu_memory',
      '--format=csv,noheader,nounits',
    ], { timeout: 3000 }).catch(() => ({ stdout: '' }))

    const procRows = procOut
      .split('\n')
      .map((l) => l.trim())
      .filter(Boolean)
      .map((line) => {
        const parts = line.split(',').map((p) => p.trim())
        if (parts.length < 4) return null
        const pid = Number(parts[1])
        if (!Number.isFinite(pid)) return null
        return {
          gpu_uuid: parts[0] || null,
          pid,
          process_name: parts[2] || 'process',
          used_gpu_memory_mib: parseFloat_(parts[3] ?? ''),
        }
      })
      .filter((r): r is NonNullable<typeof r> => r !== null)

    const commands = await readProcessCommands(procRows.map((r) => r.pid))
    const processes = procRows.map((r) => {
      const command = commands.get(r.pid) ?? null
      return {
        ...r,
        gpu_name: r.gpu_uuid ? (gpuNameByUuid.get(r.gpu_uuid) ?? null) : null,
        command,
        task_label: describeGpuTask(r.process_name, command),
      }
    })

    return Response.json({ details: { gpus, processes } })
  } catch (error) {
    const detail = error instanceof Error ? error.message : 'GPU probe failed'
    return Response.json({ details: { gpus: [], processes: [] }, error: detail }, { status: 200 })
  }
}
