'use client'

import { useEffect, useState, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import useSWR from 'swr'
import { isLoggedIn, removeToken } from '@/lib/auth'
import { askQuestion, getHistory, fetchUser, type AskResponse, type ChatSession } from '@/lib/api'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import Sidebar from '@/components/Sidebar'

function parseAnswer(raw: string) {
  const gapMarkers = ['## ⚠️ Coverage gaps', '## Coverage gaps', '⚠️ Coverage gaps']
  for (const marker of gapMarkers) {
    const idx = raw.indexOf(marker)
    if (idx !== -1) {
      return {
        main: raw.slice(0, idx).replace(/^##\s*Answer\s*/i, '').trim(),
        gaps: raw.slice(idx + marker.length).trim(),
      }
    }
  }
  return {
    main: raw.replace(/^##\s*Answer\s*/i, '').trim(),
    gaps: null,
  }
}

const PDT = 'America/Los_Angeles'

function parseUTC(dateStr: string) {
  return new Date(dateStr.endsWith('Z') || dateStr.includes('+') ? dateStr : dateStr + 'Z')
}

function formatItemTime(dateStr: string) {
  const date = parseUTC(dateStr)
  const tz = { timeZone: PDT }
  const todayStr = new Date().toLocaleDateString('en-US', tz)
  const itemDateStr = date.toLocaleDateString('en-US', tz)
  if (itemDateStr === todayStr) {
    return date.toLocaleTimeString('en-US', { ...tz, hour: 'numeric', minute: '2-digit' })
  }
  const yesterday = new Date()
  yesterday.setDate(yesterday.getDate() - 1)
  if (itemDateStr === yesterday.toLocaleDateString('en-US', tz)) return 'Yesterday'
  return date.toLocaleDateString('en-US', { ...tz, month: 'short', day: 'numeric' })
}

function getExcerpt(answer: string) {
  const clean = answer
    .replace(/#{1,6}\s/g, '')
    .replace(/\*\*/g, '')
    .replace(/\*/g, '')
    .replace(/\n+/g, ' ')
    .trim()
  return clean.length > 55 ? clean.slice(0, 55) + '…' : clean
}

function groupHistory(sessions: ChatSession[]) {
  const todayStart = new Date()
  todayStart.setHours(0, 0, 0, 0)
  const todayItems = sessions.filter(s => parseUTC(s.created_at) >= todayStart)
  const earlierItems = sessions.filter(s => parseUTC(s.created_at) < todayStart)
  const groups: { label: string; items: ChatSession[] }[] = []
  if (todayItems.length > 0) groups.push({ label: 'Today', items: todayItems })
  if (earlierItems.length > 0) groups.push({ label: 'Earlier', items: earlierItems })
  return groups
}

export default function ChatPage() {
  const router = useRouter()
  const [question, setQuestion] = useState('')
  const [result, setResult] = useState<AskResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [history, setHistory] = useState<ChatSession[]>([])
  const [activeHistoryId, setActiveHistoryId] = useState<number | null>(null)

  const { data: user } = useSWR(isLoggedIn() ? '/api/users/me' : null, fetchUser)
  const initial = user?.email?.charAt(0).toUpperCase() ?? 'A'

  const loadHistory = useCallback(async () => {
    try {
      const data = await getHistory()
      setHistory(data)
    } catch {
      // silently fail
    }
  }, [])

  useEffect(() => {
    if (!isLoggedIn()) { router.replace('/login'); return }
    loadHistory()
  }, [router, loadHistory])

  function handleLogout() {
    removeToken()
    router.push('/login')
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!question.trim()) return
    setLoading(true)
    setError('')
    setResult(null)
    setActiveHistoryId(null)
    try {
      const data = await askQuestion(question.trim())
      setResult(data)
      await loadHistory()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong')
    } finally {
      setLoading(false)
    }
  }

  function loadFromHistory(session: ChatSession) {
    setQuestion(session.question)
    setResult({ question: session.question, answer: session.answer, sources: session.sources })
    setActiveHistoryId(session.id)
    setError('')
  }

  const groups = groupHistory(history)

  const historySlot = (
    <div>
      <p className="text-sm font-semibold text-stone-500 px-3 py-2">Chat History</p>
      {history.length === 0 ? (
        <p className="text-xs text-stone-400 px-3">No history yet.</p>
      ) : (
        groups.map(group => (
          <div key={group.label} className="mb-2">
            <p className="text-xs font-semibold text-stone-400 px-3 py-1">{group.label}</p>
            <div className="space-y-0.5">
              {group.items.map(session => {
                const active = activeHistoryId === session.id
                return (
                  <button
                    key={session.id}
                    onClick={() => loadFromHistory(session)}
                    className={`w-full text-left rounded-xl transition-colors relative overflow-hidden ${
                      active ? 'bg-indigo-50' : 'hover:bg-stone-50'
                    }`}
                  >
                    {active && (
                      <span className="absolute left-0 top-2 bottom-2 w-0.5 rounded-full bg-indigo-500" />
                    )}
                    <div className="px-3 py-2">
                      <p className={`text-xs font-medium leading-snug line-clamp-2 ${
                        active ? 'text-indigo-900' : 'text-stone-700'
                      }`}>
                        {session.question}
                      </p>
                      {session.answer && session.sources.length > 0 && (
                        <p className="text-xs text-stone-400 mt-0.5 line-clamp-1">
                          {getExcerpt(session.answer)}
                        </p>
                      )}
                      <p className={`text-xs mt-0.5 ${active ? 'text-indigo-400' : 'text-stone-400'}`}>
                        {formatItemTime(session.created_at)}
                      </p>
                    </div>
                  </button>
                )
              })}
            </div>
          </div>
        ))
      )}
    </div>
  )

  return (
    <div className="flex min-h-screen bg-gradient-to-b from-indigo-50/40 via-white to-white">
      <Sidebar activePage="chat" articles={[]}>
        {historySlot}
      </Sidebar>

      <div className="flex-1 flex flex-col min-w-0">
        {/* Top bar */}
        <div className="sticky top-0 z-10 bg-indigo-50/40 backdrop-blur-sm border-b border-indigo-100/60 px-8 py-4 flex items-center justify-end">
          <div className="relative group">
            <div className="w-8 h-8 rounded-full bg-indigo-600 text-white text-sm font-semibold flex items-center justify-center cursor-pointer select-none">
              {initial}
            </div>
            <div className="absolute right-0 top-full mt-2 w-36 bg-white rounded-xl shadow-lg border border-stone-200 py-1 opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all z-50">
              <button
                onClick={handleLogout}
                className="w-full flex items-center gap-2.5 px-3 py-2 text-sm text-stone-600 hover:text-stone-900 hover:bg-stone-50 transition-colors"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
                </svg>
                Sign out
              </button>
            </div>
          </div>
        </div>

        {/* Main chat content */}
        <main className="flex-1 overflow-y-auto">
          <div className="max-w-2xl mx-auto px-4 py-12">
            {!result && !loading && (
              <div className="text-center mb-8">
                <div className="flex justify-center mb-3">
                  <svg className="w-8 h-8 text-indigo-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z" />
                  </svg>
                </div>
                <h2 className="text-3xl font-bold text-stone-900">Ask Your Library</h2>
                <p className="text-stone-500 text-sm mt-2">Get answers from what you&apos;ve read.</p>
              </div>
            )}

            <form onSubmit={handleSubmit} className="flex gap-2 mb-8">
              <div className="relative flex-1">
                <svg className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-stone-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
                <input
                  type="text"
                  value={question}
                  onChange={e => setQuestion(e.target.value)}
                  placeholder="e.g. How does Kubernetes handle rolling updates?"
                  disabled={loading}
                  className="w-full pl-9 pr-4 py-3 bg-white border border-stone-200 rounded-xl text-sm text-stone-900 placeholder:text-stone-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent shadow-sm disabled:opacity-50"
                />
              </div>
              <button
                type="submit"
                disabled={loading || !question.trim()}
                className="flex items-center gap-2 px-5 py-3 bg-indigo-600 text-white text-sm font-medium rounded-xl hover:bg-indigo-700 transition-colors disabled:opacity-40 disabled:cursor-not-allowed shadow-sm"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z" />
                </svg>
                {loading ? 'Thinking...' : 'Ask'}
              </button>
            </form>

            {error && (
              <div className="bg-red-50 border border-red-200 text-red-700 rounded-xl p-4 text-sm mb-6">
                {error}
              </div>
            )}

            {loading && (
              <div className="bg-white border border-stone-200 rounded-2xl p-6 shadow-sm animate-pulse space-y-3">
                <div className="h-3 bg-stone-100 rounded w-1/3" />
                <div className="h-3 bg-stone-100 rounded w-full" />
                <div className="h-3 bg-stone-100 rounded w-5/6" />
                <div className="h-3 bg-stone-100 rounded w-4/6" />
              </div>
            )}

            {result && !loading && result.sources.length > 0 && (
              <div className="bg-white border border-stone-200 rounded-2xl shadow-sm overflow-hidden">
                <div className="p-6 border-b border-stone-100">
                  <div className="flex items-center gap-2 mb-4">
                    <svg className="w-5 h-5 text-indigo-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
                    </svg>
                    <h3 className="text-sm font-semibold text-stone-700">What&apos;s in your library</h3>
                  </div>
                  <div className="space-y-2">
                    {result.sources.map(source => (
                      <a
                        key={source.id}
                        href={source.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-start gap-3 p-3 rounded-xl border border-indigo-100/60 bg-indigo-50/20 hover:border-indigo-200 hover:bg-indigo-50/40 transition-colors group"
                      >
                        <span className="flex-shrink-0 w-6 h-6 rounded-full bg-indigo-100 text-indigo-600 text-xs font-bold flex items-center justify-center mt-0.5">
                          {source.index}
                        </span>
                        <div className="flex-1 min-w-0">
                          <p className="text-base font-medium text-stone-900 group-hover:text-indigo-700 truncate">
                            {source.title}
                          </p>
                          <p className="text-xs text-stone-400 mt-0.5">
                            Saved {new Date(source.saved_at).toLocaleDateString()} · {Math.round(source.similarity * 100)}% match
                          </p>
                        </div>
                        <svg className="w-4 h-4 text-stone-300 group-hover:text-indigo-400 shrink-0 mt-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                        </svg>
                      </a>
                    ))}
                  </div>
                </div>

                {(() => {
                  const { main, gaps } = parseAnswer(result.answer)
                  return (
                    <div className="p-6 space-y-4">
                      <div className="flex items-center gap-2 mb-2">
                        <svg className="w-5 h-5 text-emerald-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                        </svg>
                        <h3 className="text-sm font-semibold text-stone-700">Answer</h3>
                      </div>
                      <div className="prose max-w-none text-stone-800">
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>{main}</ReactMarkdown>
                      </div>
                      {gaps && (
                        <div className="flex gap-3 bg-amber-50 border border-amber-200 rounded-xl p-4">
                          <span className="text-lg shrink-0">⚠️</span>
                          <div>
                            <p className="text-sm font-semibold text-amber-800 mb-1">Coverage gaps</p>
                            <p className="text-sm text-amber-700">{gaps}</p>
                          </div>
                        </div>
                      )}
                    </div>
                  )
                })()}
              </div>
            )}

            {result && !loading && result.sources.length === 0 && (
              <div className="flex gap-3 bg-amber-50 border border-amber-200 rounded-xl p-4">
                <span className="text-lg shrink-0">⚠️</span>
                <div>
                  <p className="text-sm font-semibold text-amber-800 mb-1">No relevant articles found</p>
                  <p className="text-sm text-amber-700">{result.answer}</p>
                </div>
              </div>
            )}
          </div>
        </main>
      </div>
    </div>
  )
}
