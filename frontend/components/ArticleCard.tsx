'use client'

import { useState } from 'react'
import { type Article, deleteArticle } from '@/lib/api'

interface Props {
  article: Article
  onTagClick?: (tag: string) => void
  selectedTag?: string | null
  onDelete?: (id: number) => void
}

function extractDomain(url: string): string {
  try {
    return new URL(url).hostname.replace('www.', '')
  } catch {
    return url
  }
}

const SITE_COLORS = [
  'bg-indigo-100 text-indigo-700',
  'bg-violet-100 text-violet-700',
  'bg-blue-100 text-blue-700',
  'bg-emerald-100 text-emerald-700',
  'bg-amber-100 text-amber-700',
  'bg-rose-100 text-rose-700',
  'bg-cyan-100 text-cyan-700',
  'bg-fuchsia-100 text-fuchsia-700',
]

function siteColor(name: string) {
  let hash = 0
  for (const c of name) hash = (hash * 31 + c.charCodeAt(0)) & 0xffff
  return SITE_COLORS[hash % SITE_COLORS.length]
}

export default function ArticleCard({ article, onTagClick, selectedTag, onDelete }: Props) {
  const [deleting, setDeleting] = useState(false)

  async function handleDelete(e: React.MouseEvent) {
    e.preventDefault()
    if (!confirm(`Delete "${article.title}"?`)) return
    setDeleting(true)
    try {
      await deleteArticle(article.id)
      onDelete?.(article.id)
    } catch {
      setDeleting(false)
    }
  }

  const date = new Date(article.created_at).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })

  const source = article.site_name || extractDomain(article.url)
  const initial = source.charAt(0).toUpperCase()
  const colorClass = siteColor(source)

  return (
    <div className={`bg-white border border-stone-200/80 rounded-2xl px-5 py-4 hover:shadow-md hover:border-indigo-200 transition-all ${deleting ? 'opacity-50 pointer-events-none' : ''}`}>
      <div className="flex items-start gap-4">
        {/* 站点首字母圆圈 */}
        <div className={`w-9 h-9 rounded-full flex items-center justify-center text-sm font-bold shrink-0 mt-0.5 ${colorClass}`}>
          {initial}
        </div>

        <div className="flex-1 min-w-0">
          {/* 来源 + 日期 */}
          <div className="flex items-center gap-1.5 text-xs text-stone-400 mb-1">
            <span className="font-medium text-stone-500">{source}</span>
            <span>·</span>
            <span>{date}</span>
          </div>

          {/* 标题 */}
          <a
            href={article.url}
            target="_blank"
            rel="noopener noreferrer"
            className="block text-base font-semibold text-stone-900 hover:text-indigo-600 transition-colors mb-2 leading-snug"
          >
            {article.title}
          </a>

          {/* AI 摘要 */}
          {article.ai_summary ? (
            <p className="text-sm text-stone-500 leading-relaxed mb-3 line-clamp-2">
              {article.ai_summary}
            </p>
          ) : (
            <p className="text-sm text-stone-400 italic mb-3">
              AI analysis in progress...
            </p>
          )}

          {/* 标签 */}
          {article.tags.length > 0 && (
            <div className="flex flex-wrap gap-1.5">
              {article.tags.map(tag => (
                <button
                  key={tag.id}
                  onClick={() => onTagClick?.(tag.name)}
                  className={`text-xs px-2.5 py-1 rounded-lg transition-colors ${
                selectedTag === tag.name
                  ? 'bg-indigo-200 text-indigo-800 font-semibold'
                  : 'bg-indigo-50 text-indigo-600 hover:bg-indigo-100'
              }`}
                >
                  {tag.name}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* 删除按钮，hover 时才显示 */}
        <button
          onClick={handleDelete}
          className="shrink-0 p-1 text-stone-400 hover:text-red-400 transition-colors mt-0.5"
          title="Delete article"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
          </svg>
        </button>
      </div>
    </div>
  )
}
