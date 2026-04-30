import { execFile } from 'node:child_process'
import os from 'node:os'
import { promisify } from 'node:util'

const execFileAsync = promisify(execFile)

export const runtime = 'nodejs'

type HostDiskSnapshot = {
  mount: string
  used_gib: number | null
  total_gib: number | null
  used_percent: number | null
}

type HostProcessSnapshot = {
  pid: number
  command_name: string
  cpu_percent: number | null
  mem_percent: number | null
  rss_mib: number | null
  command: string | null
}

function parseMetric(value: string): number | null {
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : null
}

function parsePercent(value: string): number | null {
  const parsed = Number(value.replace('%', '').trim())
  return Number.isFinite(parsed) ? parsed : null
}

async function probeDisks(): Promise<HostDiskSnapshot[]> {
  try {
    const { stdout } = await execFileAsync('df', ['-kP', '/', '/home'], { timeout: 3000 })
    return stdout
      .split('\n')
      .map((l) => l.trim())
      .filter(Boolean)
      .slice(1)
      .map((line) => {
        const parts = line.split(/\s+/)
        if (parts.length < 6) return null
        const totalKiB = Number(parts[1])
        const usedKiB = Number(parts[2])
        return {
          mount: parts[5],
          used_gib: Number.isFinite(usedKiB) ? Number((usedKiB / 1024 / 1024).toFixed(1)) : null,
          total_gib: Number.isFinite(totalKiB) ? Number((totalKiB / 1024 / 1024).toFixed(1)) : null,
          used_percent: parsePercent(parts[4] ?? ''),
        }
      })
      .filter((d): d is HostDiskSnapshot => d !== null)
  } catch {
    return []
  }
}

async function probeTopProcesses(): Promise<HostProcessSnapshot[]> {
  try {
    const { stdout } = await execFileAsync(
      'ps',
      ['-eo', 'pid=,comm=,%cpu=,%mem=,rss=,args=', '--sort=-rss'],
      { timeout: 3000 },
    )

    return stdout
      .split('\n')
      .map((l) => l.trim())
      .filter(Boolean)
      .slice(0, 10)
      .map((line) => {
        const match = line.match(/^(\d+)\s+(\S+)\s+([\d.]+)\s+([\d.]+)\s+(\d+)\s+(.*)$/)
        if (!match) return null
        const pid = Number(match[1])
        if (!Number.isFinite(pid)) return null
        const rssKiB = Number(match[5])
        return {
          pid,
          command_name: match[2],
          cpu_percent: parseMetric(match[3]),
          mem_percent: parseMetric(match[4]),
          rss_mib: Number.isFinite(rssKiB) ? Number((rssKiB / 1024).toFixed(1)) : null,
          command: match[6].trim() || null,
        }
      })
      .filter((p): p is HostProcessSnapshot => p !== null)
  } catch {
    return []
  }
}

export async function GET(): Promise<Response> {
  try {
    const [disks, top_processes] = await Promise.all([probeDisks(), probeTopProcesses()])

    const totalMem = os.totalmem()
    const freeMem = os.freemem()
    const usedMem = Math.max(totalMem - freeMem, 0)
    const cpuCount = os.cpus().length
    const load = os.loadavg()

    return Response.json({
      details: {
        cpu: {
          core_count: cpuCount,
          model: os.cpus()[0]?.model ?? null,
          load_1m: Number(load[0]?.toFixed(2) ?? 0),
          load_5m: Number(load[1]?.toFixed(2) ?? 0),
          load_15m: Number(load[2]?.toFixed(2) ?? 0),
          normalized_load_percent: cpuCount > 0 ? Number(((load[0] / cpuCount) * 100).toFixed(1)) : null,
        },
        memory: {
          used_gib: Number((usedMem / 1024 / 1024 / 1024).toFixed(1)),
          total_gib: Number((totalMem / 1024 / 1024 / 1024).toFixed(1)),
          free_gib: Number((freeMem / 1024 / 1024 / 1024).toFixed(1)),
          used_percent: totalMem > 0 ? Number(((usedMem / totalMem) * 100).toFixed(1)) : null,
        },
        disks,
        top_processes,
        hostname: os.hostname(),
        platform: `${os.platform()} ${os.release()}`,
        uptime_seconds: os.uptime(),
      },
    })
  } catch (error) {
    const detail = error instanceof Error ? error.message : 'Host probe failed'
    return Response.json({ details: null, error: detail }, { status: 200 })
  }
}
