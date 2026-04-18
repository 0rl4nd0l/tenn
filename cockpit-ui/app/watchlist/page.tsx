'use client'

import { useEffect, useState } from 'react'

import { CockpitLayout } from '@/components/cockpit/cockpit-layout'
import { WatchlistScreen } from '@/components/cockpit/watchlist/watchlist-screen'

export default function WatchlistPage() {
  const [apiKey, setApiKey] = useState(process.env.NEXT_PUBLIC_API_KEY ?? '')

  useEffect(() => {
    setApiKey(localStorage.getItem('cockpit.apiKey') ?? process.env.NEXT_PUBLIC_API_KEY ?? '')
  }, [])

  return (
    <CockpitLayout title="Watchlist">
      <WatchlistScreen apiKey={apiKey} />
    </CockpitLayout>
  )
}
