'use client'

import { useEffect, useState } from 'react'

import { CockpitLayout } from '@/components/cockpit/cockpit-layout'
import { MarketplaceMissionScreen } from '@/components/cockpit/marketplace/mission-screen'

export default function MarketplacePage() {
  const [apiKey, setApiKey] = useState(process.env.NEXT_PUBLIC_API_KEY ?? '')

  useEffect(() => {
    setApiKey(localStorage.getItem('cockpit.apiKey') ?? process.env.NEXT_PUBLIC_API_KEY ?? '')
  }, [])

  return (
    <CockpitLayout title="Marketplace">
      <MarketplaceMissionScreen apiKey={apiKey} />
    </CockpitLayout>
  )
}
