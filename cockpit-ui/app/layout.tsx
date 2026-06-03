import './globals.css'
import type { ReactNode } from 'react'

export const metadata = { title: 'TENN Cockpit', description: 'Local TENN cockpit shell' }

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  )
}
