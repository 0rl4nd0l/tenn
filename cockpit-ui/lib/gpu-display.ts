export interface GpuDisplayRecord {
  uuid?: string | null
  name?: string | null
}

export interface GpuProcessDisplayRecord {
  gpu_uuid?: string | null
  process_name?: string | null
  command?: string | null
  task_label?: string | null
}

function processText(process: GpuProcessDisplayRecord): string {
  return [
    process.process_name,
    process.command,
    process.task_label,
  ]
    .filter((value): value is string => typeof value === 'string')
    .join(' ')
    .toLowerCase()
}

function llamaProcessRank(process: GpuProcessDisplayRecord): number | null {
  const text = processText(process)
  if (!text.includes('llama-server') && !text.includes('llama.cpp runtime')) {
    return null
  }
  if (text.includes('--port 8001') || text.includes('--port=8001') || text.includes('chat/router runtime')) {
    return 0
  }
  return 1
}

export function selectPrimaryLlamaGpuUuid(processes: GpuProcessDisplayRecord[]): string | null {
  let selected: { gpuUuid: string; rank: number } | null = null

  for (const process of processes) {
    const gpuUuid = typeof process.gpu_uuid === 'string' && process.gpu_uuid.trim()
      ? process.gpu_uuid.trim()
      : null
    if (!gpuUuid) continue

    const rank = llamaProcessRank(process)
    if (rank === null) continue

    if (!selected || rank < selected.rank) {
      selected = { gpuUuid, rank }
    }
  }

  return selected?.gpuUuid ?? null
}

export function prioritizeGpusForDisplay<TGpu extends GpuDisplayRecord, TProcess extends GpuProcessDisplayRecord>(
  gpus: TGpu[],
  processes: TProcess[],
): TGpu[] {
  const llamaGpuUuid = selectPrimaryLlamaGpuUuid(processes)
  if (!llamaGpuUuid) return gpus

  const primaryIndex = gpus.findIndex((gpu) => gpu.uuid === llamaGpuUuid)
  if (primaryIndex <= 0) return gpus

  return [
    gpus[primaryIndex],
    ...gpus.slice(0, primaryIndex),
    ...gpus.slice(primaryIndex + 1),
  ]
}
