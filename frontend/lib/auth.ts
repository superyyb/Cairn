const TOKEN_KEY = 'cairn_token'

export function getToken(): string | null {
  if (typeof window === 'undefined') return null  // SSR 环境没有 window
  return localStorage.getItem(TOKEN_KEY)
}

export function saveToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token)
}

export function removeToken(): void {
  localStorage.removeItem(TOKEN_KEY)
}

export function isLoggedIn(): boolean {
  return !!getToken()
}