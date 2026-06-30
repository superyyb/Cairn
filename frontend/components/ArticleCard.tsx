'use client'

import { useState } from 'react'
import { type Article, deleteArticle, toggleStar } from '@/lib/api'

interface Props {
  article: Article
  onTagClick?: (tag: string) => void
  selectedTag?: string | null
  onDelete?: (id: number) => void
  onStar?: (id: number, starred: boolean) => void
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

export default function ArticleCard({ article, onTagClick, selectedTag, onDelete, onStar }: Props) {
  const [deleting, setDeleting] = useState(false)
  const [expanded, setExpanded] = useState(false)
  const [starred, setStarred] = useState(article.is_starred)

  async function handleStar(e: React.MouseEvent) {
    e.preventDefault()
    const next = !starred
    setStarred(next)
    try {
      await toggleStar(article.id)
      onStar?.(article.id, next)
    } catch {
      setStarred(!next)
    }
  }

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
          <div className="flex items-center gap-1.5 text-sm text-stone-400 mb-1">
            <span className="font-medium text-stone-500">{source}</span>
            <span>·</span>
            <span>{date}</span>
          </div>

          {/* 标题 */}
          <button
            onClick={() => setExpanded(e => !e)}
            className="block text-left text-lg font-semibold text-stone-900 hover:text-indigo-600 transition-colors mb-2 leading-snug w-full"
          >
            {article.title}
          </button>

          {/* AI 摘要（收起时截断，展开时完整） */}
          {article.ai_summary ? (
            <p className={`text-base text-stone-500 leading-relaxed mb-3 ${expanded ? '' : 'line-clamp-2'}`}>
              {article.ai_summary}
            </p>
          ) : (
            <p className="text-base text-stone-400 italic mb-3">
              AI analysis in progress...
            </p>
          )}

          {/* 展开内容 */}
          {expanded && (
            <div className="mt-1 mb-3">
              <a
                href={article.url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 text-xs text-indigo-600 hover:text-indigo-700 font-medium"
              >
                Open original
                <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                </svg>
              </a>
            </div>
          )}

          {/* 标签 */}
          {article.tags.length > 0 && (
            <div className="flex flex-wrap gap-1.5">
              {article.tags.map(tag => (
                <button
                  key={tag.id}
                  onClick={() => onTagClick?.(tag.name)}
                  className={`text-sm px-2.5 py-1 rounded-lg transition-colors ${
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

        {/* 操作按钮 */}
        <div className="flex flex-col gap-1 shrink-0 mt-0.5">
          <button onClick={handleStar} title={starred ? 'Unstar' : 'Star'} className="p-1 transition-colors">
            <svg className={`w-4 h-4 ${starred ? 'text-amber-400 fill-amber-400' : 'fill-none text-stone-300 hover:text-amber-400'}`} stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z" />
            </svg>
          </button>
          <button onClick={handleDelete} title="Delete article" className="p-1 text-stone-300 hover:text-red-400 transition-colors">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
            </svg>
          </button>
        </div>
      </div>
    </div>
  )
}
