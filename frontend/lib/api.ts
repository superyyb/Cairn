import { getToken, saveToken, removeToken } from './auth'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

// ===== Refresh lock：多个请求同时 401 时只发一次 refresh =====

let _refreshPromise: Promise<string | null> | null = null

async function refreshAccessToken(): Promise<string | null> {
  if (_refreshPromise) return _refreshPromise

  _refreshPromise = fetch(`${API_BASE}/api/auth/refresh?client_type=web`, {
    method: 'POST',
    credentials: 'include', // 发送 httpOnly cookie 里的 refresh token
  })
    .then(async (res) => {
      if (!res.ok) return null
      const data = await res.json()
      saveToken(data.access_token)
      return data.access_token as string
    })
    .catch(() => null)
    .finally(() => { _refreshPromise = null })

  return _refreshPromise
}

// 页面加载时尝试用 cookie 里的 refresh token 恢复登录状态
export async function tryRestoreSession(): Promise<boolean> {
  const token = await refreshAccessToken()
  return token !== null
}

// ===== 核心请求函数 =====

export async function apiFetch(path: string, options: RequestInit = {}, _retry = true): Promise<Response> {
  const token = getToken()

  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  })

  if (res.status === 401 && _retry) {
    const newToken = await refreshAccessToken()
    if (newToken) {
      return apiFetch(path, options, false) // 用新 token 重试一次
    }
    removeToken()
    window.location.href = '/login'
    throw new Error('Session expired')
  }

  return res
}

// ===== Auth =====


export async function apiLogout(): Promise<void> {
  await fetch(`${API_BASE}/api/auth/logout?client_type=web`, {
    method: 'POST',
    credentials: 'include',
  }).catch(() => {}) // 即使失败也继续清除本地状态
  removeToken()
  window.location.href = '/login'
}

// ===== 用户相关类型 =====

export interface User {
  id: number
  email: string
  username: string
  created_at: string
}

export async function fetchUser(): Promise<User> {
  const res = await apiFetch('/api/users/me')
  if (!res.ok) throw new Error('Failed to fetch user')
  return res.json()
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

export async function setStar(id: number, is_starred: boolean): Promise<Article> {
  const res = await apiFetch(`/api/articles/${id}/star`, {
    method: 'PATCH',
    body: JSON.stringify({ is_starred }),
  })
  if (!res.ok) throw new Error('Failed to set star')
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
