'use client'

import { useEffect, useState } from 'react'
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
  const [searchQuery, setSearchQuery] = useState('')

  useEffect(() => {
    if (!isLoggedIn()) {
      router.replace('/login')
      return
    }
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

  const allTags = Array.from(
    new Set(articles.flatMap(a => a.tags.map(t => t.name)))
  )
    .map(tag => ({
      name: tag,
      count: articles.filter(a => a.tags.some(t => t.name === tag)).length,
    }))
    .filter(t => t.count >= 2)
    .sort((a, b) => b.count - a.count || a.name.localeCompare(b.name))
    .map(t => t.name)

  const visibleArticles = articles.filter(article => {
    const matchesTag = !selectedTag || article.tags.some(t => t.name === selectedTag)

    const q = searchQuery.trim().toLowerCase()
    const matchesSearch = !q ||
      article.title.toLowerCase().includes(q) ||
      article.ai_summary?.toLowerCase().includes(q) ||
      article.excerpt?.toLowerCase().includes(q) ||
      article.tags.some(t => t.name.toLowerCase().includes(q))

    return matchesTag && matchesSearch
  })

  return (
    <div className="min-h-screen bg-stone-50">
      {/* 顶部导航 */}
      <header className="bg-stone-900 text-white px-6 py-4 flex items-center justify-between">
        <h1 className="text-lg font-bold tracking-wide">Cairn</h1>
        <button
          onClick={handleLogout}
          className="text-sm text-stone-400 hover:text-white transition-colors"
        >
          Sign out
        </button>
      </header>

      <main className="max-w-3xl mx-auto px-6 py-10">
        {/* 页面标题 */}
        <div className="mb-6">
          <h2 className="text-2xl font-bold text-stone-900">My Library</h2>
          {!loading && !error && (
            <p className="text-stone-500 text-sm mt-1">
              {visibleArticles.length} {visibleArticles.length === 1 ? 'article' : 'articles'}
              {searchQuery && ` matching "${searchQuery}"`}
              {selectedTag && ` tagged "${selectedTag}"`}
            </p>
          )}
        </div>

        {/* 搜索框 */}
        {!loading && !error && (
          <div className="relative mb-4">
            <svg
              className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-stone-400"
              fill="none" stroke="currentColor" viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            <input
              type="text"
              placeholder="Search titles, summaries, tags..."
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-4 py-2.5 bg-white border border-stone-200 rounded-lg text-sm text-stone-900 placeholder:text-stone-400 focus:outline-none focus:ring-2 focus:ring-stone-900 focus:border-transparent"
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery('')}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-stone-400 hover:text-stone-600"
              >
                ✕
              </button>
            )}
          </div>
        )}

        {/* 标签筛选栏 */}
        {!loading && !error && allTags.length > 0 && (
          <div className="flex flex-wrap gap-2 mb-6">
            {allTags.map(tag => (
              <button
                key={tag}
                onClick={() => setSelectedTag(selectedTag === tag ? null : tag)}
                className={`text-xs px-3 py-1.5 rounded-full border transition-colors ${
                  selectedTag === tag
                    ? 'bg-stone-900 text-white border-stone-900'
                    : 'bg-white text-stone-600 border-stone-200 hover:border-stone-400'
                }`}
              >
                {tag}
              </button>
            ))}
          </div>
        )}

        {/* 加载中 */}
        {loading && (
          <div className="space-y-4">
            {[1, 2, 3].map(i => (
              <div key={i} className="bg-white border border-stone-200 rounded-xl p-6 animate-pulse">
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
            {error}
          </div>
        )}

        {/* 空状态 */}
        {!loading && !error && visibleArticles.length === 0 && (
          <div className="text-center py-20 text-stone-400">
            <p className="text-lg mb-2">
              {searchQuery || selectedTag ? 'No articles found' : 'No articles yet'}
            </p>
            <p className="text-sm">
              {searchQuery || selectedTag
                ? 'Try a different keyword or tag.'
                : 'Use the Chrome extension to save your first article.'}
            </p>
          </div>
        )}

        {/* 文章列表 */}
        {!loading && !error && visibleArticles.length > 0 && (
          <div className="space-y-4">
            {visibleArticles.map(article => (
              <ArticleCard
                key={article.id}
                article={article}
                onTagClick={tag => setSelectedTag(selectedTag === tag ? null : tag)}
              />
            ))}
          </div>
        )}
      </main>
    </div>
  )
}