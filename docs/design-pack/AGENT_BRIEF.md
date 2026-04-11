# Agent Brief: Building New Cockpit Screens

Read this before writing any UI code. It gives you the rules in 2 minutes.

---

## Identity

This is a **dark-mode financial analysis workstation** with a **terminal aesthetic**. Think Bloomberg Terminal meets modern web UI. Not playful, not minimal — dense, functional, data-first.

## Non-Negotiable Rules

1. **Dark mode only**. The `<html>` tag has `class="dark"` hardcoded. There is no light mode.
2. **OKLch colors only**. Never use hex or RGB for new colors. All colors use `oklch(L C H)` format. Match the existing palette — do not invent new hues.
3. **Fira Sans for UI, Fira Code for data**. Use `font-sans` (default) for labels, headings, prose. Use `font-mono` for numbers, code, terminal output, technical values.
4. **Radix + shadcn components**. Import from `@/components/ui/*`. Do not create custom primitives when a shadcn component exists.
5. **CockpitLayout wrapper**. Every new page wraps in `<CockpitLayout title="Page Name">`. This provides the sidebar, header, and status bar.
6. **Terminal classes for terminal-style areas**. Use `terminal-container`, `terminal-panel`, `terminal-text`, `terminal-text-dim` CSS classes.
7. **Lucide icons only**. Import from `lucide-react`. Size with `h-4 w-4` (standard) or `h-3 w-3` (compact).
8. **No inline styles**. Use Tailwind classes exclusively.

## Color Quick Reference

| Semantic | CSS Variable | OKLch Value | Use For |
|----------|-------------|-------------|---------|
| Background | `--background` | `oklch(0.14 0.02 260)` | Page background |
| Card | `--card` | `oklch(0.19 0.02 260)` | Card surfaces |
| Primary | `--primary` | `oklch(0.7 0.15 195)` | Accent, links, focus rings |
| Success | `--success` | `oklch(0.69 0.22 145)` | Healthy, running, positive |
| Warning | `--warning` | `oklch(0.78 0.17 80)` | Degraded, caution, abstain |
| Destructive | `--destructive` | `oklch(0.58 0.22 25)` | Errors, failures, critical |
| Info | `--info` | `oklch(0.65 0.15 240)` | Informational, insights |
| Muted FG | `--muted-foreground` | `oklch(0.67 0.02 260)` | Secondary text |
| Border | `--border` | `oklch(0.33 0.02 260)` | Borders, dividers |

## Layout Pattern

Every screen follows this skeleton:

```tsx
import { CockpitLayout } from '@/components/cockpit/cockpit-layout'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

export default function NewScreenPage() {
  return (
    <CockpitLayout title="Screen Name">
      <div className="flex flex-1 flex-col gap-4 p-4 overflow-auto">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-mono uppercase tracking-wider">
              Section Title
            </CardTitle>
          </CardHeader>
          <CardContent>
            {/* Content here */}
          </CardContent>
        </Card>
      </div>
    </CockpitLayout>
  )
}
```

## Component Patterns

### Status Indicators
```tsx
{/* Health dot — animated when running */}
<span className={`h-2 w-2 rounded-full ${
  healthy
    ? 'bg-[oklch(0.69_0.22_145)] status-dot-running'
    : 'bg-[oklch(0.58_0.22_25)]'
}`} />
```

### Data Labels (terminal style)
```tsx
<div className="text-[11px] text-muted-foreground font-mono">
  field_name: {value}
</div>
```

### Section Headers
```tsx
<div className="flex items-center gap-1 text-[11px] uppercase tracking-wide text-muted-foreground">
  <Icon className="h-3 w-3" />
  Section Label
</div>
```

### Badge Usage
```tsx
import { Badge } from '@/components/ui/badge'

<Badge variant="outline" className="text-xs font-mono">STATUS</Badge>
<Badge variant="destructive" className="text-xs font-mono">FAILED</Badge>
```

## Spacing Rules

- **Between cards**: `gap-4` or `gap-6`
- **Card padding**: `px-6 py-6` (via Card defaults)
- **Compact lists**: `space-y-1`
- **Standard lists**: `space-y-2` or `gap-2`
- **Page padding**: `p-4`
- **Border radius**: `rounded-md` (inputs), `rounded-lg` (cards), `rounded-xl` (large cards)

## What NOT to Do

- Do not add a light mode or theme toggle
- Do not use hex colors (`#1a1a2e`) — use oklch
- Do not import icons from any library other than lucide-react
- Do not create custom button/input/card components — use shadcn
- Do not use `console.log` in production code
- Do not add animations beyond what the system uses (subtle pulse, blink)
- Do not use `any` in TypeScript — use `unknown` and narrow
