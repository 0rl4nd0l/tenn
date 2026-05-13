'use client'

import { Suspense, useEffect, useState } from 'react'

import { CockpitLayout } from '@/components/cockpit/cockpit-layout'
import { MemoryScreen } from '@/components/cockpit/memory/memory-screen'

export default function MemoryPage() {
  const [apiKey, setApiKey] = useState(process.env.NEXT_PUBLIC_API_KEY ?? '')

  useEffect(() => {
    setApiKey(localStorage.getItem('cockpit.apiKey') ?? process.env.NEXT_PUBLIC_API_KEY ?? '')
  }, [])

  return (
    <CockpitLayout title="Memory">
      <Suspense fallback={null}>
        <MemoryScreen apiKey={apiKey} />
      </Suspense>
    </CockpitLayout>
  )
}
