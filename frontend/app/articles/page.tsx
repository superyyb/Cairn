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
        <div className="mb-8">
          <h2 className="text-2xl font-bold text-stone-900">My Library</h2>
          {!loading && !error && (
            <p className="text-stone-500 text-sm mt-1">
              {articles.length} {articles.length === 1 ? 'article' : 'articles'} saved
            </p>
          )}
        </div>

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
        {!loading && !error && articles.length === 0 && (
          <div className="text-center py-20 text-stone-400">
            <p className="text-lg mb-2">No articles yet</p>
            <p className="text-sm">Use the Chrome extension to save your first article.</p>
          </div>
        )}

        {/* 文章列表 */}
        {!loading && !error && articles.length > 0 && (
          <div className="space-y-4">
            {articles.map(article => (
              <ArticleCard key={article.id} article={article} />
            ))}
          </div>
        )}
      </main>
    </div>
  )
}