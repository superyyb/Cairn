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
  is_starred: boolean
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

export async function fetchArticle(id: number): Promise<Article> {
  const res = await apiFetch(`/api/articles/${id}`)
  if (!res.ok) throw new Error('Failed to fetch article')
  return res.json()
}

export async function deleteArticle(id: number): Promise<void> {
  const res = await apiFetch(`/api/articles/${id}`, { method: 'DELETE' })
  if (!res.ok) throw new Error('Failed to delete article')
}

export async function toggleStar(id: number): Promise<Article> {
  const res = await apiFetch(`/api/articles/${id}/star`, { method: 'PATCH' })
  if (!res.ok) throw new Error('Failed to toggle star')
  return res.json()
}

// ===== Chat / RAG 相关类型 =====

export interface ArticleSource {
  index: number
  id: number
  title: string
  url: string
  saved_at: string
  similarity: number
}

export interface AskResponse {
  question: string
  answer: string
  sources: ArticleSource[]
}

export interface ChatSession {
  id: number
  question: string
  answer: string
  sources: ArticleSource[]
  created_at: string
}

// ===== Chat / RAG 相关 API =====

export async function askQuestion(question: string, top_k = 5): Promise<AskResponse> {
  const res = await apiFetch('/api/chat/ask', {
    method: 'POST',
    body: JSON.stringify({ question, top_k }),
  })
  if (!res.ok) {
    const err = await res.json()
    throw new Error(err.detail || 'Failed to get answer')
  }
  return res.json()
}

export async function getHistory(limit = 20): Promise<ChatSession[]> {
  const res = await apiFetch(`/api/chat/history?limit=${limit}`)
  if (!res.ok) throw new Error('Failed to fetch history')
  return res.json()
}