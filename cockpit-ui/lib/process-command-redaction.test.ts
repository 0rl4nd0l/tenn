import { describe, expect, it } from 'vitest'

import { redactProcessCommand } from './process-command-redaction'

describe('process command redaction', () => {
  it('redacts spaced secret CLI flags while preserving useful command context', () => {
    const command = '/usr/local/bin/llama-server --port 8001 --api-key local-openai-key --model /models/qwen.gguf'

    const redacted = redactProcessCommand(command)

    expect(redacted).toContain('llama-server')
    expect(redacted).toContain('--port 8001')
    expect(redacted).toContain('--model /models/qwen.gguf')
    expect(redacted).toContain('--api-key <redacted>')
    expect(redacted).not.toContain('local-openai-key')
  })

  it('redacts equals-form secret flags without hiding non-secret tokenizer arguments', () => {
    const command = 'python worker.py --openai-api-key=sk-live --auth-token=token-123 --tokenizer tokenizer.json'

    const redacted = redactProcessCommand(command)

    expect(redacted).toContain('--openai-api-key=<redacted>')
    expect(redacted).toContain('--auth-token=<redacted>')
    expect(redacted).toContain('--tokenizer tokenizer.json')
    expect(redacted).not.toContain('sk-live')
    expect(redacted).not.toContain('token-123')
  })

  it('redacts secret environment assignments and preserves non-secret assignments', () => {
    const command = "LLM_API_KEY=local-key OPENAI_API_KEY='sk quoted' TOKENIZERS_PARALLELISM=false PATH=/bin python app.py"

    const redacted = redactProcessCommand(command)

    expect(redacted).toContain('LLM_API_KEY=<redacted>')
    expect(redacted).toContain('OPENAI_API_KEY=<redacted>')
    expect(redacted).toContain('TOKENIZERS_PARALLELISM=false')
    expect(redacted).toContain('PATH=/bin')
    expect(redacted).not.toContain('local-key')
    expect(redacted).not.toContain('sk quoted')
  })

  it('redacts authorization header values', () => {
    const command = 'curl -H Authorization: Bearer bearer-secret http://localhost:8000/api/health'

    const redacted = redactProcessCommand(command)

    expect(redacted).toContain('Authorization: <redacted>')
    expect(redacted).toContain('http://localhost:8000/api/health')
    expect(redacted).not.toContain('bearer-secret')
  })

  it('does not treat non-flag words ending in token as secret flags', () => {
    const command = 'python script.py refresh-token report.json'

    expect(redactProcessCommand(command)).toBe(command)
  })

  it('keeps null command values null', () => {
    expect(redactProcessCommand(null)).toBeNull()
  })
})
