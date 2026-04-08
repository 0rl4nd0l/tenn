# SKILL: textual-developer

Specialized guidance for building and debugging **Textual** (Python TUI) applications within the Tenn/Cockpit architecture.

## Workflow

1. **Architecture Check**: Ensure the new widget or screen inherits from the correct Textual base classes (`Widget`, `Screen`, `Static`, etc.).
2. **Composition**: Use the `compose()` method to define the layout. Prefer `Horizontal` and `Vertical` containers for alignment.
3. **Reactive State**: Use `@reactive` for attributes that should trigger a UI update when changed.
4. **Styling**: All styling must be defined in the `.tcss` files or via the `styles` attribute in Python. Adhere to the project's dark-theme palette.
5. **Event Handling**: Implement `on_mount`, `on_click`, and custom message handlers (`on_my_custom_message`).
6. **Web Delivery**: When testing for the browser, use `textual serve` to verify responsiveness and layout in a web context.

## Design Standards (Tenn/Cockpit)
- **Background**: `#0a0a0f`
- **Surface**: `#13131a`
- **Accent**: `#6366f1`
- **Text**: `#e4e4e7`
- **Icons**: Use Lucide icons where possible.

## Tools
- `textual run --dev`: Run in development mode with live reloading.
- `textual console`: Use in a separate terminal to see logs and DOM inspection.

## Common Patterns
- **Async Handling**: Use `self.run_worker()` for long-running tasks to prevent UI blocking.
- **Deep Context**: Link widgets to `cockpit.core.tools` for data-fetching.
