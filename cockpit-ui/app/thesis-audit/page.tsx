'use client'

import { useEffect, useState } from 'react'

import { CockpitLayout } from '@/components/cockpit/cockpit-layout'
import { ThesisAuditScreen } from '@/components/cockpit/thesis-audit/thesis-audit-screen'

export default function ThesisAuditPage() {
  const [apiKey, setApiKey] = useState(process.env.NEXT_PUBLIC_API_KEY ?? '')

  useEffect(() => {
    setApiKey(localStorage.getItem('cockpit.apiKey') ?? process.env.NEXT_PUBLIC_API_KEY ?? '')
  }, [])

  return (
    <CockpitLayout title="Thesis Audit">
      <ThesisAuditScreen apiKey={apiKey} />
    </CockpitLayout>
  )
}
