import { Suspense } from 'react'

import { CockpitLayout } from '@/components/cockpit/cockpit-layout'
import { ChatScreen } from '@/components/cockpit/chat/chat-screen'

export default function FullChatPage() {
  return (
    <CockpitLayout title="Chat">
      <Suspense fallback={null}>
        <ChatScreen />
      </Suspense>
    </CockpitLayout>
  )
}
