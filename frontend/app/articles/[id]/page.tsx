'use client'

import { useEffect, useState } from 'react'
import { useRouter, useParams } from 'next/navigation'
import useSWR from 'swr'
import { isLoggedIn } from '@/lib/auth'
import { fetchArticle, fetchArticles, tryRestoreSession, type Article } from '@/lib/api'
import Sidebar from '@/components/Sidebar'

function extractDomain(url: string): string {
  try {
    return new URL(url).hostname.replace('www.', '')
  } catch {
    return url
  }
}

export default function ArticleDetailPage() {
  const router = useRouter()
  const params = useParams()
  const [article, setArticle] = useState<Article | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [authChecked, setAuthChecked] = useState(false)

  useEffect(() => {
    async function load() {
      if (!isLoggedIn() && !await tryRestoreSession()) {
        router.replace('/login')
        return
      }
      setAuthChecked(true)
      fetchArticle(Number(params.id))
        .then(setArticle)
        .catch(err => setError(err instanceof Error ? err.message : 'Something went wrong'))
        .finally(() => setLoading(false))
    }
    load()
  }, [params.id, router])

  const { data: articles = [] } = useSWR(authChecked ? '/api/articles' : null, fetchArticles)

  return (
    <div className="flex min-h-screen bg-gradient-to-b from-indigo-50/40 via-white to-white">
      <Sidebar
        articles={articles}
        activePage="library"
        onStarredToggle={() => router.push('/articles?starred=true')}
      />

      <div className="flex-1 flex flex-col min-w-0">
        <main className="max-w-2xl mx-auto px-4 py-10 w-full">
          {/* Back */}
          <a href="/articles" className="inline-flex items-center gap-1.5 text-sm text-stone-400 hover:text-stone-700 transition-colors mb-8">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
            Back to Library
          </a>

          {loading && (
            <div className="bg-white border border-stone-200 rounded-2xl p-8 animate-pulse space-y-4">
              <div className="h-3 bg-stone-100 rounded w-1/4" />
              <div className="h-6 bg-stone-100 rounded w-3/4" />
              <div className="h-3 bg-stone-100 rounded w-full" />
              <div className="h-3 bg-stone-100 rounded w-5/6" />
            </div>
          )}

          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 rounded-xl p-4 text-sm">{error}</div>
          )}

          {article && (
            <div className="bg-white border border-stone-200 rounded-2xl p-8 space-y-6">
              {/* 来源 + 日期 */}
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-1.5 text-xs text-stone-400">
                  <span className="font-medium text-stone-500">
                    {article.site_name || extractDomain(article.url)}
                  </span>
                  <span>·</span>
                  <span>{new Date(article.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}</span>
                  {article.byline && (
                    <>
                      <span>·</span>
                      <span>{article.byline}</span>
                    </>
                  )}
                </div>
                <a
                  href={article.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-1 text-xs text-indigo-600 hover:text-indigo-700 font-medium"
                >
                  Open original
                  <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                  </svg>
                </a>
              </div>

              {/* 标题 */}
              <h1 className="text-2xl font-bold text-stone-900 leading-snug">{article.title}</h1>

              {/* Tags */}
              {article.tags.length > 0 && (
                <div className="flex flex-wrap gap-1.5">
                  {article.tags.map(tag => (
                    <span key={tag.id} className="text-xs px-2.5 py-1 rounded-lg bg-indigo-50 text-indigo-600">
                      {tag.name}
                    </span>
                  ))}
                </div>
              )}

              {/* AI 摘要 */}
              <div>
                <h2 className="text-xs font-semibold text-stone-400 uppercase tracking-wide mb-2">AI Summary</h2>
                {article.ai_summary ? (
                  <p className="text-stone-700 leading-relaxed">{article.ai_summary}</p>
                ) : (
                  <p className="text-stone-400 italic text-sm">AI analysis in progress...</p>
                )}
              </div>

              {/* Excerpt */}
              {article.excerpt && (
                <div>
                  <h2 className="text-xs font-semibold text-stone-400 uppercase tracking-wide mb-2">Excerpt</h2>
                  <p className="text-stone-600 leading-relaxed text-sm border-l-2 border-indigo-200 pl-4">
                    {article.excerpt}
                  </p>
                </div>
              )}
            </div>
          )}
        </main>
      </div>
    </div>
  )
}
