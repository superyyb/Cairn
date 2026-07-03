// Access token 只存内存，页面关闭自动清除，JS 无法通过 XSS 读取 cookie 里的 refresh token
let _token: string | null = null

export function getToken(): string | null {
  return _token
}

export function saveToken(token: string): void {
  _token = token
}

export function removeToken(): void {
  _token = null
}

export function isLoggedIn(): boolean {
  return _token !== null
}
