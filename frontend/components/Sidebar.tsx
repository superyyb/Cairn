'use client'

import { useMemo } from 'react'
import { type Article } from '@/lib/api'

interface Props {
  articles: Article[]
  activePage: 'library' | 'chat'
  showStarred?: boolean
  onStarredToggle?: () => void
  children?: React.ReactNode
}

export default function Sidebar({ articles, activePage, showStarred, onStarredToggle, children }: Props) {
  const thisWeek = useMemo(() => {
    const cutoff = Date.now() - 7 * 86400000
    return articles.filter(a => new Date(a.created_at).getTime() > cutoff).length
  }, [articles])

  const sparkData = useMemo(() => {
    const days = 14
    const counts = Array(days).fill(0)
    const now = Date.now()
    for (const a of articles) {
      const daysAgo = Math.floor((now - new Date(a.created_at).getTime()) / 86400000)
      if (daysAgo >= 0 && daysAgo < days) counts[days - 1 - daysAgo]++
    }
    return counts
  }, [articles])

  const max = Math.max(...sparkData, 1)
  const W = 160, H = 36
  const points = sparkData.map((v, i) => {
    const x = (i / (sparkData.length - 1)) * W
    const y = H - (v / max) * (H - 4)
    return `${x},${y}`
  }).join(' ')

  const navItems = [
    {
      href: '/',
      active: false,
      icon: (
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
        </svg>
      ),
      label: 'Home',
    },
    {
      href: '/articles',
      active: activePage === 'library',
      icon: (
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
        </svg>
      ),
      label: 'Library',
    },
    {
      href: '/chat',
      active: activePage === 'chat',
      icon: (
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z" />
        </svg>
      ),
      label: 'Ask AI',
    },
  ]

  return (
    <aside className="w-72 shrink-0 sticky top-0 h-screen flex flex-col border-r border-stone-200/60 bg-white px-4 py-4">
      {/* Logo */}
      <a href="/" className="flex items-center gap-3 px-3 py-3 mb-4">
        <svg width="32" height="32" viewBox="0 0 24 24" fill="none">
          <ellipse cx="12" cy="20" rx="7" ry="2.5" fill="#4f46e5" opacity="0.9"/>
          <ellipse cx="12" cy="14.5" rx="5" ry="2" fill="#4f46e5" opacity="0.8"/>
          <ellipse cx="12" cy="9.5" rx="3.5" ry="1.8" fill="#4f46e5" opacity="0.7"/>
          <ellipse cx="12" cy="5.5" rx="2" ry="1.5" fill="#4f46e5" opacity="0.6"/>
        </svg>
        <span className="font-bold text-stone-900 text-xl">Cairn</span>
      </a>

      {/* Nav */}
      <nav className="space-y-0.5">
        {navItems.map(item => (
          <a
            key={item.href}
            href={item.href}
            className={`flex items-center gap-2.5 px-3 py-2.5 rounded-lg text-base transition-colors ${
              item.active
                ? 'bg-indigo-50 text-indigo-600 font-medium'
                : 'text-stone-500 hover:text-stone-900 hover:bg-stone-50'
            }`}
          >
            {item.icon}
            {item.label}
          </a>
        ))}
        <button
          onClick={onStarredToggle}
          className={`w-full flex items-center gap-2.5 px-3 py-2.5 rounded-lg text-base transition-colors ${
            showStarred
              ? 'bg-indigo-50 text-indigo-600 font-medium'
              : 'text-stone-500 hover:text-stone-900 hover:bg-stone-50'
          }`}
        >
          <svg className={`w-4 h-4 ${showStarred ? 'fill-indigo-400 text-indigo-400' : 'fill-none'}`} stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z" />
          </svg>
          Starred
        </button>
      </nav>

      {/* Middle: chat history slot or spacer */}
      {children ? (
        <div className="flex-1 overflow-y-auto mt-3 min-h-0">{children}</div>
      ) : (
        <div className="flex-1" />
      )}

      {/* Stats card — library only */}
      {!children && articles.length > 0 && (
        <div className="border border-stone-200/80 rounded-xl p-3">
          <p className="text-xs text-stone-400 mb-1">Total saved</p>
          <p className="text-2xl font-semibold text-stone-900 leading-none mb-1">{articles.length}</p>
          {thisWeek > 0 && (
            <p className="text-xs text-emerald-600 font-medium mb-2">+{thisWeek} this week</p>
          )}
          <svg width="100%" height={H} viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none">
            <polyline
              points={points}
              fill="none"
              stroke="#818cf8"
              strokeWidth="1.5"
              strokeLinejoin="round"
              strokeLinecap="round"
            />
          </svg>
        </div>
      )}
    </aside>
  )
}
