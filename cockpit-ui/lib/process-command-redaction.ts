const REDACTED_VALUE = '<redacted>'

const TOKEN_PATTERN = /"[^"]*"|'[^']*'|\S+/g
const FLAG_VALUE_PATTERN = /(^|\s)(--[A-Za-z0-9][A-Za-z0-9_-]*=)(?:"[^"]*"|'[^']*'|\S+)/g
const ENV_ASSIGNMENT_PATTERN = /\b([A-Za-z_][A-Za-z0-9_]*=)(?:"[^"]*"|'[^']*'|\S+)/g
const AUTHORIZATION_VALUE_PATTERN = /\b(authorization\s*[:=]\s*)(?:bearer\s+)?(?:"[^"]*"|'[^']*'|\S+)/gi

const EXACT_SECRET_FLAGS = new Set([
  'api-key',
  'apikey',
  'authorization',
  'auth-token',
  'access-token',
  'refresh-token',
  'bearer-token',
  'password',
  'passwd',
  'secret',
  'token',
  'x-api-key',
])

function normalizeFlagName(flag: string): string {
  return flag.replace(/^--/, '').replace(/_/g, '-').toLowerCase()
}

function isSecretFlag(flag: string): boolean {
  const normalized = normalizeFlagName(flag)
  return EXACT_SECRET_FLAGS.has(normalized)
    || normalized.endsWith('-api-key')
    || normalized.endsWith('-token')
    || normalized.endsWith('-password')
    || normalized.endsWith('-passwd')
    || normalized.endsWith('-secret')
}

function isSecretFlagToken(token: string): boolean {
  return token.startsWith('--') && isSecretFlag(token)
}

function normalizeEnvName(name: string): string {
  return name.toUpperCase().replace(/[^A-Z0-9]/g, '_')
}

function isSecretEnvName(name: string): boolean {
  const normalized = normalizeEnvName(name)
  return normalized === 'AUTHORIZATION'
    || normalized === 'TOKEN'
    || normalized === 'PASSWORD'
    || normalized === 'SECRET'
    || normalized === 'API_KEY'
    || normalized.endsWith('_API_KEY')
    || normalized.endsWith('_TOKEN')
    || normalized.endsWith('_PASSWORD')
    || normalized.endsWith('_SECRET')
    || normalized.endsWith('_SECRET_KEY')
}

function redactEqualsForm(command: string): string {
  return command
    .replace(ENV_ASSIGNMENT_PATTERN, (match, prefix: string) => {
      const name = prefix.slice(0, -1)
      return isSecretEnvName(name) ? `${prefix}${REDACTED_VALUE}` : match
    })
    .replace(FLAG_VALUE_PATTERN, (match, leading: string, prefix: string) => {
      const flag = prefix.slice(0, -1)
      return isSecretFlag(flag) ? `${leading}${prefix}${REDACTED_VALUE}` : match
    })
    .replace(AUTHORIZATION_VALUE_PATTERN, `$1${REDACTED_VALUE}`)
}

function stripOuterQuotes(value: string): string {
  if ((value.startsWith('"') && value.endsWith('"')) || (value.startsWith("'") && value.endsWith("'"))) {
    return value.slice(1, -1)
  }
  return value
}

function isAuthorizationHeaderToken(token: string): boolean {
  return /^authorization:?$/i.test(stripOuterQuotes(token))
}

export function redactProcessCommand(command: string | null | undefined): string | null {
  if (command == null) return null

  const tokens = redactEqualsForm(command).match(TOKEN_PATTERN) ?? []
  const redacted: string[] = []

  for (let index = 0; index < tokens.length; index += 1) {
    const token = tokens[index]
    redacted.push(token)

    if (isSecretFlagToken(token) && tokens[index + 1] && !tokens[index + 1].startsWith('--')) {
      redacted.push(REDACTED_VALUE)
      index += 1
      continue
    }

    if (isAuthorizationHeaderToken(token) && tokens[index + 1]) {
      redacted.push(REDACTED_VALUE)
      if (/^bearer$/i.test(stripOuterQuotes(tokens[index + 1])) && tokens[index + 2]) {
        index += 2
      } else {
        index += 1
      }
    }
  }

  return redacted.join(' ')
}
