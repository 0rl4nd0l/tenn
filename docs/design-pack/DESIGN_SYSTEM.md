# Design System Reference

Complete design system specification for the Financial Cockpit UI.

---

## 1. Color System

All colors use **OKLch** (Oklch Lightness, Chroma, Hue) — a perceptually uniform color space. This means equal numeric steps produce equal perceived brightness changes, making it ideal for consistent status color ramps.

### Core Palette

#### Backgrounds & Surfaces

| Token | OKLch | Role | Tailwind Class |
|-------|-------|------|---------------|
| `--background` | `oklch(0.14 0.02 260)` | Page background | `bg-background` |
| `--card` | `oklch(0.19 0.02 260)` | Card surfaces | `bg-card` |
| `--popover` | `oklch(0.19 0.02 260)` | Popover surfaces | `bg-popover` |
| `--secondary` | `oklch(0.22 0.02 260)` | Secondary surfaces | `bg-secondary` |
| `--muted` | `oklch(0.25 0.02 260)` | Muted backgrounds | `bg-muted` |
| `--accent` | `oklch(0.25 0.03 260)` | Hover/focus bg | `bg-accent` |
| `--input` | `oklch(0.2 0.02 260)` | Input backgrounds | `bg-input` |
| `--sidebar` | `oklch(0.13 0.02 260)` | Sidebar (darkest) | `bg-sidebar` |
| Terminal BG | `oklch(0.08 0.01 260)` | Terminal container | `.terminal-container` |

**Surface lightness ramp** (L values): `0.08 → 0.13 → 0.14 → 0.19 → 0.20 → 0.22 → 0.25`

All surfaces share **hue 260** (deep blue-violet) with very low chroma (0.01–0.03), creating a cohesive navy palette.

#### Text & Foreground

| Token | OKLch | Role | Tailwind Class |
|-------|-------|------|---------------|
| `--foreground` | `oklch(0.93 0.01 260)` | Primary text | `text-foreground` |
| `--card-foreground` | `oklch(0.93 0.01 260)` | Card text | `text-card-foreground` |
| `--secondary-foreground` | `oklch(0.88 0.01 260)` | Secondary text | `text-secondary-foreground` |
| `--muted-foreground` | `oklch(0.67 0.02 260)` | Muted/label text | `text-muted-foreground` |
| `--sidebar-foreground` | `oklch(0.89 0.01 260)` | Sidebar text | `text-sidebar-foreground` |

**Text lightness ramp**: `0.67 (muted) → 0.88 (secondary) → 0.89 (sidebar) → 0.93 (primary)`

#### Accent & Interactive

| Token | OKLch | Role | Tailwind Class |
|-------|-------|------|---------------|
| `--primary` | `oklch(0.7 0.15 195)` | Primary accent (cyan) | `bg-primary`, `text-primary` |
| `--primary-foreground` | `oklch(0.15 0.02 260)` | Text on primary | `text-primary-foreground` |
| `--ring` | `oklch(0.7 0.15 195)` | Focus rings | `ring-ring` |
| `--sidebar-primary` | `oklch(0.7 0.15 195)` | Sidebar accent | `bg-sidebar-primary` |

#### Semantic Status Colors

| Token | OKLch | Hue | Role | Use Case |
|-------|-------|-----|------|----------|
| `--success` | `oklch(0.69 0.22 145)` | Green | Healthy, running | Backend up, job complete |
| `--warning` | `oklch(0.78 0.17 80)` | Amber | Degraded, caution | Abstain, partial |
| `--info` | `oklch(0.65 0.15 240)` | Purple | Informational | Insights, metrics |
| `--destructive` | `oklch(0.58 0.22 25)` | Red | Error, failure | Backend down, job failed |

#### Chart Colors

| Token | OKLch | Hue |
|-------|-------|-----|
| `--chart-1` | `oklch(0.7 0.15 195)` | Cyan |
| `--chart-2` | `oklch(0.69 0.22 145)` | Green |
| `--chart-3` | `oklch(0.78 0.17 80)` | Amber |
| `--chart-4` | `oklch(0.6 0.18 280)` | Purple |
| `--chart-5` | `oklch(0.55 0.2 25)` | Red |

#### Border & Divider

| Token | OKLch | Tailwind Class |
|-------|-------|---------------|
| `--border` | `oklch(0.33 0.02 260)` | `border-border` |
| `--sidebar-border` | `oklch(0.25 0.02 260)` | `border-sidebar-border` |

#### Inline Status Colors (used directly, not via CSS vars)

| Purpose | OKLch | Context |
|---------|-------|---------|
| Backend healthy dot | `oklch(0.69 0.22 145)` | Sidebar, status bar |
| GPU healthy dot | `oklch(0.7 0.18 205)` | Sidebar |
| Backend down dot | `oklch(0.58 0.22 25)` | Sidebar |
| GPU unknown dot | `oklch(0.7 0.05 250)` | Sidebar |
| Warning background | `oklch(0.78 0.17 80 / 0.08)` | Notice banner |
| Warning border | `oklch(0.78 0.17 80 / 0.4)` | Notice banner |
| Warning text | `oklch(0.78 0.17 80)` | Notice text |
| API override pulse start | `oklch(0.68 0.18 245)` | Status bar |
| API override pulse mid | `oklch(0.74 0.19 150)` | Status bar |

### Terminal-Specific Colors

| Class | OKLch | Role |
|-------|-------|------|
| `.terminal-text` | `oklch(0.95 0 0)` | Standard terminal white |
| `.terminal-text-dim` | `oklch(0.65 0.15 240)` | Dim purple-blue |
| `.terminal-text-bright` | `oklch(1 0 0)` | Bright white |
| `.terminal-prompt` | `oklch(0.7 0.18 240)` | Prompt blue |
| `.terminal-cursor` | `oklch(0.95 0 0)` | Cursor white |
| `.terminal-input::placeholder` | `oklch(0.5 0.12 240)` | Input placeholder |

### Color Design Principles

1. **Low chroma backgrounds**: All surfaces use C ≤ 0.03 — they're nearly neutral, preventing visual fatigue
2. **High chroma accents**: Status/semantic colors use C = 0.15–0.22 — they pop against muted backgrounds
3. **Consistent hue families**: Backgrounds all on H=260, greens on H=145, ambers on H=80, reds on H=25
4. **Opacity mixing**: `color-mix(in oklch, ...)` for transparent overlays, maintaining perceptual consistency

---

## 2. Typography

### Font Stack

| Role | Family | CSS Variable | Tailwind Class |
|------|--------|-------------|---------------|
| **UI text** | Fira Sans | `--font-fira-sans` | `font-sans` (default) |
| **Code/data** | Fira Code | `--font-fira-code` | `font-mono` |

Both loaded from Google Fonts via `next/font` with weights: 400, 500, 600, 700.

### Size Scale

| Tailwind | Rem | Px | Use Case |
|----------|-----|-----|----------|
| `text-[9px]` | — | 9 | Micro badges, pipeline health % |
| `text-[10px]` | — | 10 | Keyboard shortcuts, process counts |
| `text-[11px]` | — | 11 | Config values, timestamps, metadata |
| `text-xs` | 0.75rem | 12 | Labels, badges, status text |
| `text-sm` | 0.875rem | 14 | Sidebar items, secondary text |
| `text-base` | 1rem | 16 | Body text, `.terminal-text-dim` |
| `text-lg` | 1.125rem | 18 | `.terminal-text`, `.terminal-prompt` |

### Weight Usage

| Weight | Tailwind | When |
|--------|----------|------|
| 400 | `font-normal` | Body text, terminal output |
| 500 | `font-medium` | Interactive labels, active nav items |
| 600 | `font-semibold` | Headings, card titles |
| 700 | `font-bold` | Emphasis (rarely used) |

### Typography Patterns

```tsx
{/* Card title */}
<CardTitle className="text-sm font-mono uppercase tracking-wider">
  Section Title
</CardTitle>

{/* Data label + value */}
<div className="text-[11px] text-muted-foreground font-mono">
  field_name: {value}
</div>

{/* Sidebar group label */}
<SidebarGroupLabel>Navigation</SidebarGroupLabel>

{/* Config box header */}
<div className="flex items-center gap-1 text-[11px] uppercase tracking-wide text-muted-foreground">
  <Icon className="h-3 w-3" />
  CONFIG SECTION
</div>
```

---

## 3. Spacing & Sizing

### Base Radius

```css
--radius: 0.5rem;         /* 8px */
--radius-sm: calc(--radius - 4px);  /* 4px */
--radius-md: calc(--radius - 2px);  /* 6px */
--radius-lg: var(--radius);          /* 8px */
--radius-xl: calc(--radius + 4px);  /* 12px */
```

| Tailwind | Px | Use Case |
|----------|-----|----------|
| `rounded-sm` | 4 | Small elements, badges |
| `rounded-md` | 6 | Inputs, buttons |
| `rounded-lg` | 8 | Cards, dialogs |
| `rounded-xl` | 12 | Large cards, panels |
| `rounded-full` | 50% | Status dots, avatars |

### Height Standards

| Size | Px | Use Case |
|------|-----|----------|
| `h-2 w-2` | 8 | Status dots |
| `h-3 w-3` | 12 | Compact icons |
| `h-4 w-4` | 16 | Standard icons |
| `h-8` | 32 | Small buttons, logo container |
| `h-9` | 36 | Default button height |
| `h-10` | 40 | Large buttons |
| `h-12` | 48 | Header bar |

### Padding Scale

| Context | Classes |
|---------|---------|
| Tight (badges, compact) | `px-1 py-0.5` or `px-1.5 py-0.5` |
| Standard (buttons, inputs) | `px-3 py-2` or `px-4 py-2` |
| Card content | `px-6` (via Card default) |
| Page content | `p-4` |
| Spacious sections | `px-6 py-6` |

### Gap Scale

| Tailwind | Px | Use Case |
|----------|-----|----------|
| `gap-1` | 4 | Icon + text inline |
| `gap-2` | 8 | Button groups, compact lists |
| `gap-3` | 12 | Form fields |
| `gap-4` | 16 | Between cards |
| `gap-6` | 24 | Major sections |

---

## 4. Motion & Animation

### Timing

```css
--motion-fast: 150ms;
--motion-base: 200ms;
```

### Animations

| Name | Duration | Easing | Use |
|------|----------|--------|-----|
| `status-pulse` | 1.6s | ease-in-out, infinite | Health status dots when running |
| `terminal-blink` | 1s | step-end, infinite | Terminal cursor blinking |
| `api-default-override-pulse` | 1.4s | ease-in-out, infinite | API override indicator |

### Transitions

```tsx
{/* Standard color transition */}
<button className="transition-colors duration-150">

{/* All properties */}
<div className="transition-all">

{/* Hover effect */}
<div className="hover:border-primary/50 hover:bg-sidebar-accent/30 transition-colors">
```

### Reduced Motion

```css
@media (prefers-reduced-motion: reduce) {
  .terminal-cursor,
  .status-dot-running {
    animation: none;
  }
}
```

---

## 5. Terminal Visual Effects

The terminal container has two overlay pseudo-elements creating a CRT aesthetic:

### Scanlines (`::before`)
```css
background: repeating-linear-gradient(
  0deg,
  transparent,
  transparent 2px,
  oklch(0 0 0 / 0.03) 2px,
  oklch(0 0 0 / 0.03) 4px
);
```
Subtle horizontal lines every 4px.

### Vignette (`::after`)
```css
background: radial-gradient(
  ellipse at center,
  transparent 0%,
  oklch(0 0 0 / 0.15) 100%
);
```
Darkens edges for depth.

### Terminal Panel (glass effect)
```css
.terminal-panel {
  background: color-mix(in oklch, var(--sidebar) 92%, transparent);
  border: 1px solid color-mix(in oklch, var(--sidebar-border) 75%, transparent);
  backdrop-filter: blur(6px);
}
```

---

## 6. Component Library

### Source

All base components live in `cockpit-ui/components/ui/`. They are shadcn/ui components built on Radix UI primitives, styled with Tailwind and CVA (Class Variance Authority).

### Key Components & Variants

#### Button

Variants: `default`, `destructive`, `outline`, `secondary`, `ghost`, `link`
Sizes: `default` (h-9), `sm` (h-8), `lg` (h-10), `icon` (h-9 w-9), `icon-sm` (h-8 w-8), `icon-lg` (h-10 w-10)

```tsx
import { Button } from '@/components/ui/button'
<Button variant="outline" size="sm">Action</Button>
```

#### Badge

Variants: `default`, `secondary`, `destructive`, `critical`, `outline`

```tsx
import { Badge } from '@/components/ui/badge'
<Badge variant="outline" className="text-xs font-mono">STATUS</Badge>
```

#### Card

Sub-components: `Card`, `CardHeader`, `CardTitle`, `CardDescription`, `CardAction`, `CardContent`, `CardFooter`

```tsx
<Card>
  <CardHeader>
    <CardTitle>Title</CardTitle>
    <CardDescription>Description</CardDescription>
    <CardAction><Button size="sm">Act</Button></CardAction>
  </CardHeader>
  <CardContent>{/* ... */}</CardContent>
</Card>
```

#### Sidebar

Collapsible navigation sidebar with icon mode. Components: `Sidebar`, `SidebarProvider`, `SidebarInset`, `SidebarHeader`, `SidebarContent`, `SidebarFooter`, `SidebarGroup`, `SidebarGroupLabel`, `SidebarGroupContent`, `SidebarMenu`, `SidebarMenuItem`, `SidebarMenuButton`, `SidebarSeparator`, `SidebarTrigger`

#### Data Display

- `Table` (with `TableHeader`, `TableBody`, `TableRow`, `TableCell`, `TableHead`)
- `ScrollArea` — custom scrollbar styled for dark theme
- `Accordion` — collapsible sections
- `Tabs` (`TabsList`, `TabsTrigger`, `TabsContent`)
- `Progress` — progress bar
- `Skeleton` — loading placeholder
- `Separator` — horizontal/vertical dividers

#### Dialogs & Overlays

- `Dialog` — modal with backdrop
- `Popover` — positioned popup
- `Tooltip` — hover hints (wrap in `TooltipProvider`)
- `Drawer` — slide-in panel (via `vaul`)

#### Forms

- `Input` — text input with dark styling
- `Textarea` — multi-line
- `Select` — dropdown (Radix)
- `Checkbox`, `Switch`, `RadioGroup`
- `Form` + `Field` — react-hook-form integration with Zod validation

#### Charts

- `recharts` based charting via `Chart` component
- Uses `--chart-1` through `--chart-5` CSS variables

---

## 7. Icons

**Library**: Lucide React (`lucide-react` v0.564.0)

### Size Convention

| Size Class | Px | Context |
|-----------|-----|---------|
| `h-3 w-3` | 12 | Inline with small text, config labels |
| `h-4 w-4` | 16 | Standard — nav items, buttons, status |
| `h-5 w-5` | 20 | Emphasis icons |
| `h-6 w-6` | 24 | Large/hero icons |

### Commonly Used Icons

| Icon | Import | Usage |
|------|--------|-------|
| `MessageSquare` | Navigation: Chat |
| `Settings2` | Navigation: Operations |
| `RefreshCw` | Navigation: Updater |
| `CheckCircle2` | Navigation: Verification |
| `History` | Navigation: History |
| `Gauge` | Navigation: Settings |
| `Newspaper` | Navigation: News |
| `Activity` | Navigation: Intel Pulse, health status |
| `Zap` | Logo/branding |
| `Cpu` | GPU/config |
| `AlertTriangle` | Warnings, notices |
| `ExternalLink` | External links |
| `Play` | Execute/start actions |
| `Eye` | Preview/inspect |
| `Terminal` | Terminal/code contexts |
| `Copy`, `Check` | Copy-to-clipboard (toggle) |
| `ChevronRight`, `ChevronDown` | Expand/collapse |
| `Search`, `X` | Search input, close |
| `Database` | Data/storage |
| `Shield`, `ShieldX` | Security, evaluation reject |
| `Brain` | AI/insights |
| `FileX` | Extraction failure |
| `Monitor` | Monitoring scope |
| `Building2` | Company entity |

---

## 8. State Management

### Client State: Zustand

```tsx
import { useCockpitStore } from '@/lib/cockpit-store'

// Access state
const { chatModel, sessionStats } = useCockpitStore()
```

### Server State: React Query

```tsx
import { useQuery } from '@tanstack/react-query'

const { data, isLoading } = useQuery({
  queryKey: ['health'],
  queryFn: () => fetch('/api/cockpit/health').then(r => r.json()),
  refetchInterval: 3000,
})
```

### Real-Time: Server-Sent Events

Used for job streaming and chat responses via `sse.js` library.

---

## 9. File Structure

```
cockpit-ui/
├── app/
│   ├── globals.css          ← Theme, terminal styles, animations
│   ├── layout.tsx           ← Root: fonts, dark mode, providers
│   ├── page.tsx             ← Chat (home route)
│   ├── operations/page.tsx
│   ├── updater/page.tsx
│   ├── verification/page.tsx
│   ├── history/page.tsx
│   ├── settings/page.tsx
│   ├── news/page.tsx
│   ├── intel-ops/page.tsx
│   ├── boot/page.tsx
│   └── api/cockpit/         ← API proxy routes
├── components/
│   ├── ui/                  ← 80+ shadcn/Radix components
│   ├── cockpit/             ← App-specific: layout, sidebar, screens
│   │   ├── cockpit-layout.tsx
│   │   ├── cockpit-sidebar.tsx
│   │   ├── cockpit-status-bar.tsx
│   │   ├── chat/            ← Chat screen components
│   │   ├── operations/      ← Operations screen components
│   │   ├── updater/         ← Updater screen components
│   │   ├── verification/    ← Verification screen components
│   │   ├── history/
│   │   ├── news/
│   │   ├── settings/
│   │   └── boot/
│   └── intel-ops/           ← Intel Pulse components
├── lib/
│   ├── cockpit-store.ts     ← Zustand global state
│   ├── cockpit-types.ts     ← TypeScript types
│   ├── api-client.ts        ← API fetch helpers
│   ├── chat-session-store.ts
│   └── utils.ts             ← cn() helper
└── package.json
```
