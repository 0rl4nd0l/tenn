import { CockpitLayout } from '@/components/cockpit/cockpit-layout'
import { UpdaterScreen } from '@/components/cockpit/updater/updater-screen'

export default function UpdaterPage() {
  return (
    <CockpitLayout title="Updater">
      <UpdaterScreen />
    </CockpitLayout>
  )
}
