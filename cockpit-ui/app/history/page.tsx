import { CockpitLayout } from '@/components/cockpit/cockpit-layout'
import { HistoryScreen } from '@/components/cockpit/history/history-screen'

export default function HistoryPage() {
  return (
    <CockpitLayout title="History">
      <HistoryScreen />
    </CockpitLayout>
  )
}
