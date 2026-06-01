import { describe, expect, it } from 'vitest'

import { prioritizeGpusForDisplay, selectPrimaryLlamaGpuUuid } from './gpu-display'

describe('GPU display ordering', () => {
  const gpus = [
    { uuid: 'GPU-0', name: 'NVIDIA GeForce GT 1030' },
    { uuid: 'GPU-1', name: 'Tesla M40' },
  ]

  it('selects the GPU running llama-server as the primary display GPU', () => {
    const ordered = prioritizeGpusForDisplay(gpus, [
      {
        gpu_uuid: 'GPU-1',
        process_name: 'llama-server',
        command: '/usr/local/bin/llama-server --port 8001',
      },
    ])

    expect(ordered.map((gpu) => gpu.uuid)).toEqual(['GPU-1', 'GPU-0'])
    expect(gpus.map((gpu) => gpu.uuid)).toEqual(['GPU-0', 'GPU-1'])
  })

  it('prefers the chat/router llama-server when multiple llama runtimes are visible', () => {
    expect(selectPrimaryLlamaGpuUuid([
      {
        gpu_uuid: 'GPU-0',
        process_name: 'llama-server',
        command: 'llama-server --port 8002',
      },
      {
        gpu_uuid: 'GPU-1',
        process_name: 'llama-server',
        command: 'llama-server --port=8001',
      },
    ])).toBe('GPU-1')
  })

  it('preserves host order when no llama-server process maps to a GPU', () => {
    const ordered = prioritizeGpusForDisplay(gpus, [
      {
        gpu_uuid: 'GPU-1',
        process_name: 'python',
        command: 'python scripts/example.py',
      },
    ])

    expect(ordered).toBe(gpus)
  })

  it('uses task labels when commands are unavailable', () => {
    expect(selectPrimaryLlamaGpuUuid([
      {
        gpu_uuid: 'GPU-1',
        process_name: 'process',
        task_label: 'llama.cpp runtime',
      },
    ])).toBe('GPU-1')
  })
})
