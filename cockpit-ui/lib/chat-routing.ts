export function applyApiDefaultOverride(message: string, enabled: boolean): string {
  const trimmed = message.trim()
  if (!enabled || !trimmed) {
    return message
  }
  // Preserve explicit slash commands and explicit routing directives as typed.
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
