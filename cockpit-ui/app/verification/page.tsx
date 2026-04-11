import { Suspense } from 'react'

import { CockpitLayout } from '@/components/cockpit/cockpit-layout'
import { VerificationScreen } from '@/components/cockpit/verification/verification-screen'

export default function VerificationPage() {
  return (
    <CockpitLayout title="Verification">
      <Suspense fallback={null}>
        <VerificationScreen />
      </Suspense>
    </CockpitLayout>
  )
}
