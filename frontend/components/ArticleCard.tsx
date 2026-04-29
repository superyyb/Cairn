import { type Article } from '@/lib/api'

function extractDomain(url: string): string {
  try {
    return new URL(url).hostname.replace('www.', '')
  } catch {
    return url
  }
}

export default function ArticleCard({ article }: { article: Article }) {
  const date = new Date(article.created_at).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })

  const source = article.site_name || extractDomain(article.url)

  return (
    <div className="bg-white border border-stone-200 rounded-xl p-6 hover:shadow-sm transition-shadow">
      {/* 来源 + 日期 */}
      <div className="flex items-center gap-2 text-xs text-stone-400 mb-2">
        <span>{source}</span>
        <span>·</span>
        <span>{date}</span>
      </div>

      {/* 标题 */}
      <a
        href={article.url}
        target="_blank"
        rel="noopener noreferrer"
        className="block text-base font-semibold text-stone-900 hover:text-stone-600 transition-colors mb-3 leading-snug"
      >
        {article.title}
      </a>

      {/* AI 摘要 */}
      {article.ai_summary ? (
        <p className="text-sm text-stone-600 leading-relaxed mb-4">
          {article.ai_summary}
        </p>
      ) : (
        <p className="text-sm text-stone-400 italic mb-4">
          ⏳ AI analysis in progress...
        </p>
      )}

      {/* 标签 */}
      {article.tags.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {article.tags.map(tag => (
            <span
              key={tag.id}
              className="bg-stone-100 text-stone-600 text-xs px-2.5 py-1 rounded-full"
            >
              {tag.name}
            </span>
          ))}
        </div>
      )}
    </div>
  )
}
