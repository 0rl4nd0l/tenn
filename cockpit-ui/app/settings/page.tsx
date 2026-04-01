import { CockpitLayout } from '@/components/cockpit/cockpit-layout'
import { SettingsScreen } from '@/components/cockpit/settings/settings-screen'

export default function SettingsPage() {
  return (
    <CockpitLayout title="Settings">
      <SettingsScreen />
    </CockpitLayout>
  )
}
