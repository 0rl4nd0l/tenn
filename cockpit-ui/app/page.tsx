import { CockpitLayout } from '@/components/cockpit/cockpit-layout'
import { CockpitHomePage } from '@/components/cockpit/home/home-page'

export default function Home() {
  return (
    <CockpitLayout title="Cockpit">
      <CockpitHomePage />
    </CockpitLayout>
  )
}
