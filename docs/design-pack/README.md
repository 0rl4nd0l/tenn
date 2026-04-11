# Financial Cockpit UI Design Pack

**Purpose**: Self-contained reference for agents building new screens and features in the cockpit-ui. Contains the complete design system, screen catalog, color swatches, and screenshot automation scripts.

## Contents

| File | Description |
|------|-------------|
| [DESIGN_SYSTEM.md](DESIGN_SYSTEM.md) | Colors, typography, spacing, components, patterns |
| [SCREEN_CATALOG.md](SCREEN_CATALOG.md) | Every screen documented with layout, interactions, code patterns |
| [AGENT_BRIEF.md](AGENT_BRIEF.md) | Quick-start summary for agents — read this first |
| [scripts/capture-screenshots.sh](scripts/capture-screenshots.sh) | Playwright-based screenshot capture for all routes |
| [scripts/color-swatch.html](scripts/color-swatch.html) | Visual HTML color reference — open in browser |
| `screenshots/` | Captured screenshots (populated by running the script) |

## How to Use This Pack

### For an agent building a new screen:

1. Read `AGENT_BRIEF.md` for the 2-minute orientation
2. Reference `DESIGN_SYSTEM.md` for exact color values, spacing rules, component APIs
3. Study `SCREEN_CATALOG.md` for layout patterns used in existing screens
4. Open `scripts/color-swatch.html` in a browser to see the palette visually
5. Run `scripts/capture-screenshots.sh` to generate current screenshots

### For a human reviewing agent output:

Compare agent-produced screens against the screenshots and design system to verify visual consistency.

## Stack Summary

- **Framework**: Next.js 16 (App Router)
- **Styling**: Tailwind CSS 4 (inline theme, no separate config)
- **Components**: Radix UI primitives + shadcn/ui + custom CVA variants
- **Icons**: Lucide React
- **Fonts**: Fira Sans (UI) + Fira Code (terminal/data)
- **State**: Zustand (client) + React Query (server)
- **Color Space**: OKLch (perceptually uniform)
- **Theme**: Dark mode only — hardcoded `dark` class on `<html>`
