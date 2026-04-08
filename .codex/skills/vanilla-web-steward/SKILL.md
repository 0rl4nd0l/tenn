# SKILL: vanilla-web-steward

Guidance for building "Framework-less" (Vanilla HTML/JS/CSS) dashboards for OpenClaw/Tenn.

## Workflow

1. **HTML Structure**: Use semantic HTML5. Stick to the `index.html` structure with an ID-based element hierarchy for JS targeting.
2. **CSS Variables**: ALWAYS use the project's standard CSS variables for styling. Do not hardcode colors.
   - `--bg-primary`: `#0a0a0f`
   - `--bg-secondary`: `#13131a`
   - `--bg-tertiary`: `#1a1a24`
   - `--bg-card`: `#1f1f2e`
   - `--border`: `#2a2a3a`
   - `--text-primary`: `#e4e4e7`
   - `--accent`: `#6366f1`
3. **Vanilla JS Modularization**: Use a singleton pattern or class-based structure for dashboard logic. Avoid global state pollution.
4. **API Integration**: Use `fetch()` with the standard `AbortController` pattern for safe, cancellable requests.
5. **Dynamic Updates**: Use `document.createElement` and `fragment.appendChild` for performance when updating large lists (e.g., agent session history).

## Design Standards
- **Responsive**: Use Flexbox and CSS Grid for layout. Dashboards must be responsive down to 1024px.
- **Dark Theme**: All UIs must follow the "Agent Dark" theme. No light-mode alternatives are required.
- **Icons**: Reference SVG icons directly or use the `Lucide` font-awesome-style pattern if available via CDN.

## Tools
- **Lighthouse**: Audit performance, accessibility, and best practices.
- **Chrome DevTools**: Use for live CSS tweaking and performance profiling.
