export function applyApiDefaultOverride(message: string, enabled: boolean): string {
  const trimmed = message.trim()
  if (!enabled || !trimmed) {
    return message
  }
  const localRoute = trimmed.match(/^\/(?:local|ops)\b\s*(.*)$/i)
  if (localRoute) {
    const rest = localRoute[1]?.trim()
    return rest ? `/cloud ${rest}` : '/cloud'
  }
  // Preserve non-routing slash commands and explicit API routing directives as typed.
  if (trimmed.startsWith('/')) {
    return message
  }
  return `/cloud ${trimmed}`
}

export function isApiRoutedMessage(message: string): boolean {
  const trimmed = message.trim().toLowerCase()
  return (
    trimmed === '/cloud'
    || trimmed.startsWith('/cloud ')
    || trimmed === '/advisor'
    || trimmed.startsWith('/advisor ')
  )
}
