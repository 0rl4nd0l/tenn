'use client'

import { useEffect, useState } from 'react'

import { CockpitLayout } from '@/components/cockpit/cockpit-layout'
import { MarketplaceMatchesScreen } from '@/components/cockpit/marketplace/matches-screen'

export default function MarketplaceMatchesPage() {
  const [apiKey, setApiKey] = useState(process.env.NEXT_PUBLIC_API_KEY ?? '')

  useEffect(() => {
    setApiKey(localStorage.getItem('cockpit.apiKey') ?? process.env.NEXT_PUBLIC_API_KEY ?? '')
  }, [])

  return (
    <CockpitLayout title="Marketplace Matches">
      <MarketplaceMatchesScreen apiKey={apiKey} />
    </CockpitLayout>
  )
}
