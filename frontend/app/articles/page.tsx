'use client'

import { useEffect, useMemo, useState } from 'react'
import { useRouter } from 'next/navigation'
import useSWR from 'swr'
import { isLoggedIn, getToken } from '@/lib/auth'
import { fetchArticles, type Article } from '@/lib/api'
import ArticleCard from '@/components/ArticleCard'
import Sidebar from '@/components/Sidebar'

function getUserInitial(): string {
  const token = getToken()
  if (!token) return 'A'
  try {
    const payload = JSON.parse(atob(token.split('.')[1]))
    const email: string = payload.sub || payload.email || ''
    return email.charAt(0).toUpperCase() || 'A'
  } catch {
    return 'A'
  }
}

export default function ArticlesPage() {
  const router = useRouter()
  const [selectedTag, setSelectedTag] = useState<string | null>(null)
  const [search, setSearch] = useState('')

  useEffect(() => {
    if (!isLoggedIn()) router.replace('/login')
  }, [router])

  const { data: articles = [], error, isLoading, mutate } = useSWR(
    isLoggedIn() ? '/api/articles' : null,
    fetchArticles,
  )

  function handleTagClick(tag: string) {
    setSelectedTag(prev => prev === tag ? null : tag)
  }

  function handleDelete(id: number) {
    mutate(articles.filter((a: Article) => a.id !== id), false)
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
    return articles.filter((a: Article) => {
      const matchTag = !selectedTag || a.tags.some(t => t.name === selectedTag)
      const q = search.toLowerCase()
      const matchSearch = !q ||
        a.title.toLowerCase().includes(q) ||
        (a.ai_summary?.toLowerCase().includes(q) ?? false) ||
        a.tags.some(t => t.name.toLowerCase().includes(q))
      return matchTag && matchSearch
    })
  }, [articles, selectedTag, search])

  const initial = getUserInitial()

  return (
    <div className="flex min-h-screen bg-white">
      <Sidebar articles={articles} activePage="library" />

      <div className="flex-1 flex flex-col min-w-0">
        {/* 顶部栏 */}
        <div className="sticky top-0 z-10 bg-white border-b border-stone-100 px-8 py-3 flex items-center gap-4">
          <div className="flex-1 relative max-w-md">
            <svg className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-stone-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            <input
              type="text"
              value={search}
              onChange={e => setSearch(e.target.value)}
              placeholder="Search your library..."
              className="w-full pl-9 pr-12 py-2 bg-stone-50 border border-stone-200 rounded-xl text-sm text-stone-900 placeholder:text-stone-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
            />
            <span className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-stone-300 font-mono">⌘K</span>
          </div>
          <div className="ml-auto">
            <div className="w-8 h-8 rounded-full bg-indigo-600 text-white text-sm font-semibold flex items-center justify-center">
              {initial}
            </div>
          </div>
        </div>

        {/* 主内容 */}
        <main className="flex-1 py-8 px-8">
          <div className="max-w-2xl mx-auto">

            {/* 标题 */}
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-lg font-semibold text-stone-900">Recently saved</h2>
              {!isLoading && !error && articles.length > 0 && (
                <span className="text-sm text-stone-400">{articles.length} articles</span>
              )}
            </div>

            {/* 标签过滤 */}
            {!isLoading && !error && allTags.length > 0 && (
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

            {/* 加载中 */}
            {isLoading && (
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
              <div className="bg-red-50 border border-red-200 text-red-700 rounded-xl p-4 text-sm">
                {error instanceof Error ? error.message : 'Something went wrong'}
              </div>
            )}

            {/* 空状态 */}
            {!isLoading && !error && articles.length === 0 && (
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
            {!isLoading && !error && articles.length > 0 && (
              <div className="space-y-3">
                {filtered.length === 0 ? (
                  <p className="text-center text-stone-400 text-sm py-12">No articles match your search.</p>
                ) : (
                  filtered.map((article: Article) => (
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

          </div>
        </main>
      </div>
    </div>
  )
}
