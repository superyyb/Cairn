'use client'

import { useEffect, useState, useMemo } from 'react'
import { useRouter } from 'next/navigation'
import { isLoggedIn, removeToken } from '@/lib/auth'
import { fetchArticles, type Article } from '@/lib/api'
import ArticleCard from '@/components/ArticleCard'

export default function ArticlesPage() {
  const router = useRouter()
  const [articles, setArticles] = useState<Article[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [selectedTag, setSelectedTag] = useState<string | null>(null)
  const [search, setSearch] = useState('')

  useEffect(() => {
    if (!isLoggedIn()) { router.replace('/login'); return }
    loadArticles()
  }, [router])

  async function loadArticles() {
    try {
      const data = await fetchArticles()
      setArticles(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong')
    } finally {
      setLoading(false)
    }
  }

  function handleLogout() {
    removeToken()
    router.push('/login')
  }

  function handleTagClick(tag: string) {
    setSelectedTag(prev => prev === tag ? null : tag)
  }

  function handleDelete(id: number) {
    setArticles(prev => prev.filter(a => a.id !== id))
  }

  const allTags = useMemo(() => {
    const count: Record<string, number> = {}
    for (const a of articles) {
      for (const t of a.tags) {
        count[t.name] = (count[t.name] ?? 0) + 1
      }
    }
    return Object.entries(count)
      .filter(([, n]) => n >= 2)
      .sort((a, b) => b[1] - a[1])
      .map(([name]) => name)
  }, [articles])

  const filtered = useMemo(() => {
    return articles.filter(a => {
      const matchTag = !selectedTag || a.tags.some(t => t.name === selectedTag)
      const q = search.toLowerCase()
      const matchSearch = !q ||
        a.title.toLowerCase().includes(q) ||
        (a.ai_summary?.toLowerCase().includes(q) ?? false) ||
        a.tags.some(t => t.name.toLowerCase().includes(q))
      return matchTag && matchSearch
    })
  }, [articles, selectedTag, search])

  return (
    <div className="min-h-screen bg-indigo-50/40">
      {/* Header */}
      <header className="bg-white/80 backdrop-blur border-b border-stone-200 px-6 py-3 flex items-center justify-between sticky top-0 z-10">
        <div className="flex items-center gap-2">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" className="text-indigo-600">
            <ellipse cx="12" cy="20" rx="7" ry="2.5" fill="currentColor" opacity="0.9"/>
            <ellipse cx="12" cy="14.5" rx="5" ry="2" fill="currentColor" opacity="0.8"/>
            <ellipse cx="12" cy="9.5" rx="3.5" ry="1.8" fill="currentColor" opacity="0.7"/>
            <ellipse cx="12" cy="5.5" rx="2" ry="1.5" fill="currentColor" opacity="0.6"/>
          </svg>
          <span className="font-semibold text-stone-900">Cairn</span>
        </div>
        <nav className="flex items-center gap-1">
          <a href="/articles" className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-indigo-600 bg-indigo-50 rounded-lg font-medium">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
            </svg>
            Library
          </a>
          <a href="/chat" className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-stone-500 hover:text-stone-900 hover:bg-stone-100 rounded-lg transition-colors">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z" />
            </svg>
            Ask AI
          </a>
          <button onClick={handleLogout} className="ml-2 px-3 py-1.5 text-sm text-stone-500 hover:text-stone-900 hover:bg-stone-100 rounded-lg transition-colors">
            Sign out
          </button>
        </nav>
      </header>

      <main className="max-w-2xl mx-auto px-4 py-10">
        {/* 页面标题 */}
        <div className="flex items-center gap-4 mb-6">
          <div className="w-12 h-12 bg-indigo-100 rounded-2xl flex items-center justify-center">
            <svg className="w-6 h-6 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
            </svg>
          </div>
          <div>
            <h2 className="text-2xl font-bold text-stone-900">My Library</h2>
            {!loading && !error && (
              <p className="text-indigo-600 text-sm font-medium">{articles.length} articles</p>
            )}
          </div>
        </div>

        {/* 搜索框 */}
        {!loading && !error && articles.length > 0 && (
          <>
            <div className="relative mb-4">
              <svg className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-stone-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
              <input
                type="text"
                value={search}
                onChange={e => setSearch(e.target.value)}
                placeholder="Search titles, summaries, tags..."
                className="w-full pl-9 pr-10 py-2.5 bg-white border border-stone-200 rounded-xl text-sm text-stone-900 placeholder:text-stone-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent shadow-sm"
              />
              <span className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-stone-300 font-mono">⌘K</span>
            </div>

            {/* 标签过滤 */}
            {allTags.length > 0 && (
              <div className="flex flex-wrap gap-1.5 mb-6">
                {allTags.map(tag => (
                  <button
                    key={tag}
                    onClick={() => handleTagClick(tag)}
                    className={`text-xs px-3 py-1.5 rounded-full border transition-colors ${
                      selectedTag === tag
                        ? 'bg-indigo-600 text-white border-indigo-600'
                        : 'bg-white text-stone-600 border-stone-200 hover:border-indigo-300 hover:text-indigo-600'
                    }`}
                  >
                    {tag}
                  </button>
                ))}
              </div>
            )}
          </>
        )}

        {/* 加载中 */}
        {loading && (
          <div className="space-y-4">
            {[1, 2, 3].map(i => (
              <div key={i} className="bg-white border border-stone-200 rounded-2xl p-6 animate-pulse">
                <div className="h-3 bg-stone-100 rounded w-1/4 mb-4" />
                <div className="h-5 bg-stone-100 rounded w-3/4 mb-3" />
                <div className="h-3 bg-stone-100 rounded w-full mb-2" />
                <div className="h-3 bg-stone-100 rounded w-2/3" />
              </div>
            ))}
          </div>
        )}

        {/* 报错 */}
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 rounded-xl p-4 text-sm">{error}</div>
        )}

        {/* 空状态 onboarding */}
        {!loading && !error && articles.length === 0 && (
          <div className="max-w-lg mx-auto py-12">
            <div className="text-center mb-8">
              <div className="flex justify-center mb-4">
                <div className="w-16 h-16 bg-indigo-50 rounded-2xl flex items-center justify-center">
                  <svg width="32" height="32" viewBox="0 0 24 24" fill="none" className="text-indigo-500">
                    <ellipse cx="12" cy="20" rx="7" ry="2.5" fill="currentColor" opacity="0.9"/>
                    <ellipse cx="12" cy="14.5" rx="5" ry="2" fill="currentColor" opacity="0.8"/>
                    <ellipse cx="12" cy="9.5" rx="3.5" ry="1.8" fill="currentColor" opacity="0.7"/>
                    <ellipse cx="12" cy="5.5" rx="2" ry="1.5" fill="currentColor" opacity="0.6"/>
                  </svg>
                </div>
              </div>
              <h3 className="text-xl font-bold text-stone-900">Welcome to Cairn</h3>
              <p className="text-stone-500 text-sm mt-1">Save articles, ask AI questions about what you&apos;ve read.</p>
            </div>
            <div className="space-y-3">
              {[
                { step: '1', title: 'Install the Chrome Extension', desc: 'Add Cairn to Chrome to save articles with one click.', cta: { label: 'Get Extension →', href: '#' } },
                { step: '2', title: 'Browse any article', desc: 'Find anything interesting — a blog post, a paper, a doc.' },
                { step: '3', title: 'Click the Cairn icon to save', desc: 'Cairn reads the page, generates a summary, and stores it in your library.' },
                { step: '4', title: 'Ask AI anything', desc: 'Come back and ask questions about everything you\'ve saved.', cta: { label: 'Go to Ask AI →', href: '/chat' } },
              ].map(item => (
                <div key={item.step} className="flex items-start gap-4 p-4 bg-white border border-stone-200 rounded-xl">
                  <span className="flex-shrink-0 w-7 h-7 rounded-full bg-indigo-100 text-indigo-600 text-xs font-bold flex items-center justify-center mt-0.5">{item.step}</span>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-semibold text-stone-900">{item.title}</p>
                    <p className="text-xs text-stone-500 mt-0.5">{item.desc}</p>
                  </div>
                  {item.cta && (
                    <a href={item.cta.href} className="flex-shrink-0 text-xs font-medium text-indigo-600 hover:text-indigo-700 whitespace-nowrap mt-0.5">{item.cta.label}</a>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* 文章列表 */}
        {!loading && !error && articles.length > 0 && (
          <div className="space-y-3">
            {filtered.length === 0 ? (
              <p className="text-center text-stone-400 text-sm py-12">No articles match your search.</p>
            ) : (
              filtered.map(article => (
                <ArticleCard
                  key={article.id}
                  article={article}
                  onTagClick={handleTagClick}
                  selectedTag={selectedTag}
                  onDelete={handleDelete}
                />
              ))
            )}
          </div>
        )}
      </main>
    </div>
  )
}
