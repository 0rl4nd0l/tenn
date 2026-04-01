'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import {
  MessageSquare,
  Settings2,
  RefreshCw,
  CheckCircle2,
  History,
  Newspaper,
  Gauge,
  Activity,
  Zap,
} from 'lucide-react'
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarSeparator,
} from '@/components/ui/sidebar'
import { Badge } from '@/components/ui/badge'

interface CockpitSidebarProps {
  backendHealthy: boolean
  sessionCost: number
}

const navItems = [
  { href: '/', icon: MessageSquare, label: 'Chat', shortcut: '1' },
  { href: '/operations', icon: Settings2, label: 'Operations', shortcut: '2' },
  { href: '/updater', icon: RefreshCw, label: 'Updater', shortcut: '3' },
  { href: '/verification', icon: CheckCircle2, label: 'Verification', shortcut: '4' },
  { href: '/history', icon: History, label: 'History', shortcut: '5' },
  { href: '/settings', icon: Gauge, label: 'Settings', shortcut: '6' },
  { href: '/news', icon: Newspaper, label: 'News', shortcut: '7' },
]

export function CockpitSidebar({ backendHealthy, sessionCost }: CockpitSidebarProps) {
  const pathname = usePathname()

  return (
    <Sidebar collapsible="icon">
      <SidebarHeader className="border-b border-sidebar-border">
        <div className="flex items-center gap-2 px-2 py-1">
          <div className="flex h-8 w-8 items-center justify-center rounded-md bg-primary">
            <Zap className="h-4 w-4 text-primary-foreground" />
          </div>
          <div className="flex flex-col group-data-[collapsible=icon]:hidden">
            <span className="text-sm font-semibold">Financial Cockpit</span>
            <span className="text-xs text-muted-foreground">Analysis Workstation</span>
          </div>
        </div>
      </SidebarHeader>
      
      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel>Navigation</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {navItems.map((item) => (
                <SidebarMenuItem key={item.href}>
                  <SidebarMenuButton 
                    asChild 
                    isActive={pathname === item.href}
                    tooltip={item.label}
                  >
                    <Link href={item.href}>
                      <item.icon className="h-4 w-4" />
                      <span>{item.label}</span>
                      <kbd className="ml-auto text-[10px] text-muted-foreground opacity-60 group-data-[collapsible=icon]:hidden">
                        {item.shortcut}
                      </kbd>
                    </Link>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>

        <SidebarSeparator />

        <SidebarGroup>
          <SidebarGroupLabel>Services</SidebarGroupLabel>
          <SidebarGroupContent>
            <div className="space-y-1 px-2 group-data-[collapsible=icon]:hidden">
              <div className="flex items-center justify-between text-xs py-1">
                <div className="flex items-center gap-2">
                  <span className={`h-2 w-2 rounded-full ${
                    backendHealthy
                      ? 'bg-[oklch(0.65_0.2_145)]'
                      : 'bg-[oklch(0.55_0.2_25)]'
                  }`} />
                  <span className="text-muted-foreground">Backend API</span>
                </div>
              </div>
            </div>
            <div className="px-2 group-data-[collapsible=icon]:block hidden">
              <div className="flex items-center justify-center">
                <Activity className="h-4 w-4 text-muted-foreground" />
              </div>
            </div>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>

      <SidebarFooter className="border-t border-sidebar-border">
        <div className="flex items-center justify-between px-2 py-2 group-data-[collapsible=icon]:hidden">
          <div className="flex items-center gap-2">
            <Badge variant="outline" className="text-xs font-mono">
              {backendHealthy ? '1/1' : '0/1'} Services
            </Badge>
          </div>
          <div className="text-xs text-muted-foreground font-mono">
            ${sessionCost.toFixed(4)}
          </div>
        </div>
        <div className="px-2 py-2 group-data-[collapsible=icon]:block hidden">
          <Badge variant="outline" className="text-[10px] font-mono w-full justify-center">
            {backendHealthy ? '1/1' : '0/1'}
          </Badge>
        </div>
      </SidebarFooter>
    </Sidebar>
  )
}
