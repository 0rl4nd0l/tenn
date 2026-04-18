import path from 'node:path'
import { fileURLToPath } from 'node:url'

import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'

const rootDir = path.dirname(fileURLToPath(import.meta.url))

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    setupFiles: ['./vitest.setup.ts'],
    globals: true,
    include: ['components/**/*.test.{ts,tsx}', 'lib/**/*.test.{ts,tsx}'],
  },
  resolve: {
    alias: {
      '@': path.resolve(rootDir),
    },
  },
})
