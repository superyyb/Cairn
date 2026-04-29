const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export async function apiLogin(email: string, password: string) {
  const formData = new URLSearchParams()
  formData.append('username', email)
  formData.append('password', password)

  const res = await fetch(`${API_BASE}/api/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: formData,
  })

  if (!res.ok) {
    const err = await res.json()
    throw new Error(err.detail || 'Login failed')
  }

  return res.json() as Promise<{ access_token: string; token_type: string }>
}

export async function apiFetch(path: string, options: RequestInit = {}) {
  const { getToken } = await import('./auth')
  const token = getToken()

  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  })

  if (res.status === 401) {
    const { removeToken } = await import('./auth')
    removeToken()
    window.location.href = '/login'
    throw new Error('Session expired')
  }

  return res
}

// ===== 文章相关类型 =====

export interface Tag {
  id: number
  name: string
}

export interface Article {
  id: number
  url: string
  title: string
  excerpt: string | null
  byline: string | null
  site_name: string | null
  lang: string | null
  length: number | null
  ai_summary: string | null
  tags: Tag[]
  created_at: string
  updated_at: string
}

// ===== 文章相关 API =====

export async function fetchArticles(): Promise<Article[]> {
  const res = await apiFetch('/api/articles')
  if (!res.ok) throw new Error('Failed to fetch articles')
  return res.json()
}