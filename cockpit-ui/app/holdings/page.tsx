'use client'

import { useEffect, useState } from 'react'

import { CockpitLayout } from '@/components/cockpit/cockpit-layout'
import { HoldingsScreen } from '@/components/cockpit/holdings/holdings-screen'

export default function HoldingsPage() {
  const [apiKey, setApiKey] = useState(process.env.NEXT_PUBLIC_API_KEY ?? '')

  useEffect(() => {
    setApiKey(localStorage.getItem('cockpit.apiKey') ?? process.env.NEXT_PUBLIC_API_KEY ?? '')
  }, [])

  return (
    <CockpitLayout title="Portfolio Holdings">
      <HoldingsScreen apiKey={apiKey} />
    </CockpitLayout>
  )
}

