import type { ExtractionMethod } from '@/lib/cockpit-types'

import type { VerificationTab } from './types'

export const EXTRACTION_METHOD_OPTIONS: Array<{ value: ExtractionMethod; label: string }> = [
  { value: 'auto', label: 'Auto' },
  { value: 'docling', label: 'Docling' },
  { value: 'pymupdf', label: 'PyMuPDF' },
  { value: 'anthropic', label: 'Anthropic' },
]

export const ACTIVE_RUNS_STORAGE_KEY = 'verification-active-runs-v1'

export const DEFAULT_VERIFICATION_TAB: VerificationTab = 'review'

export const VERIFICATION_TAB_ORDER: VerificationTab[] = ['review', 'runs', 'gold-eval', 'verify']
