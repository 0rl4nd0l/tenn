'use client'

import { useEffect, useMemo, useState } from 'react'
import { useParams } from 'next/navigation'

import { CockpitLayout } from '@/components/cockpit/cockpit-layout'
import { MarketplaceMatchDetailScreen } from '@/components/cockpit/marketplace/match-detail-screen'

export default function MarketplaceMatchDetailPage() {
  const params = useParams<{ matchId: string | string[] }>()
  const [apiKey, setApiKey] = useState(process.env.NEXT_PUBLIC_API_KEY ?? '')
  const matchId = useMemo(() => {
    const value = params?.matchId
    return Array.isArray(value) ? value[0] ?? '' : value ?? ''
  }, [params])

  useEffect(() => {
    setApiKey(localStorage.getItem('cockpit.apiKey') ?? process.env.NEXT_PUBLIC_API_KEY ?? '')
  }, [])

  return (
    <CockpitLayout title="Marketplace Match Detail">
      <MarketplaceMatchDetailScreen apiKey={apiKey} matchId={matchId} />
    </CockpitLayout>
  )
}
