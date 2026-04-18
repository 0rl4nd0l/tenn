'use client'

import { useEffect, useState } from 'react'

import { CockpitLayout } from '@/components/cockpit/cockpit-layout'
import { MarketplaceAlertsScreen } from '@/components/cockpit/marketplace/alerts-screen'

export default function MarketplaceAlertsPage() {
  const [apiKey, setApiKey] = useState(process.env.NEXT_PUBLIC_API_KEY ?? '')

  useEffect(() => {
    setApiKey(localStorage.getItem('cockpit.apiKey') ?? process.env.NEXT_PUBLIC_API_KEY ?? '')
  }, [])

  return (
    <CockpitLayout title="Marketplace Alerts">
      <MarketplaceAlertsScreen apiKey={apiKey} />
    </CockpitLayout>
  )
}
