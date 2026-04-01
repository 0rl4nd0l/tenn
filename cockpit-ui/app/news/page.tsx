import { CockpitLayout } from '@/components/cockpit/cockpit-layout'
import { NewsScreen } from '@/components/cockpit/news/news-screen'

export default function NewsPage() {
  return (
    <CockpitLayout title="News">
      <NewsScreen />
    </CockpitLayout>
  )
}
