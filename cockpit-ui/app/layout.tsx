import type { Metadata, Viewport } from 'next'
import { Analytics } from '@vercel/analytics/next'
import { QueryProvider } from '@/components/query-provider'
import { OfflineIndicator } from '@/components/cockpit/offline-indicator'
import { ThemeProvider } from '@/components/theme-provider'
import { Toaster } from '@/components/ui/sonner'
import './globals.css'

export const metadata: Metadata = {
  title: 'Financial Cockpit',
  description: 'Financial analysis workstation - Chat, data operations, verification, news search, and strategy management',
  generator: 'v0.app',
  icons: {
    icon: [
      {
        url: '/icon-dark-32x32.png',
        media: '(prefers-color-scheme: light)',
      },
      {
        url: '/icon-dark-32x32.png',
        media: '(prefers-color-scheme: dark)',
      },
      {
        url: '/icon.svg',
        type: 'image/svg+xml',
      },
    ],
    apple: '/apple-icon.png',
  },
}

export const viewport: Viewport = {
  themeColor: '#1a1a2e',
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="en" className="dark" suppressHydrationWarning>
      <body className="font-sans antialiased">
        <ThemeProvider
          attribute="class"
          defaultTheme="dark"
          forcedTheme="dark"
          enableSystem={false}
          enableColorScheme={false}
        >
          <QueryProvider>
            {children}
            <OfflineIndicator />
            <Toaster />
          </QueryProvider>
        </ThemeProvider>
        <Analytics />
      </body>
    </html>
  )
}
