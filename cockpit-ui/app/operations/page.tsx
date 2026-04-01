import { CockpitLayout } from '@/components/cockpit/cockpit-layout'
import { OperationsScreen } from '@/components/cockpit/operations/operations-screen'

export default function OperationsPage() {
  return (
    <CockpitLayout title="Operations">
      <OperationsScreen />
    </CockpitLayout>
  )
}
