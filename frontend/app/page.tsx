'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { isLoggedIn } from '@/lib/auth'
import { tryRestoreSession } from '@/lib/api'

export default function Home() {
  const [loggedIn, setLoggedIn] = useState(false)

  useEffect(() => {
    if (isLoggedIn()) {
      setLoggedIn(true)
      return
    }
    tryRestoreSession().then(setLoggedIn)
  }, [])

  return (
    <div className="min-h-screen bg-white">
      {/* Nav */}
      <header className="flex items-center justify-between px-8 py-4 border-b border-stone-100">
        <div className="flex items-center gap-2">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
            <ellipse cx="12" cy="20" rx="7" ry="2.5" fill="#4f46e5" opacity="0.9"/>
            <ellipse cx="12" cy="14.5" rx="5" ry="2" fill="#4f46e5" opacity="0.8"/>
            <ellipse cx="12" cy="9.5" rx="3.5" ry="1.8" fill="#4f46e5" opacity="0.7"/>
            <ellipse cx="12" cy="5.5" rx="2" ry="1.5" fill="#4f46e5" opacity="0.6"/>
          </svg>
          <span className="font-semibold text-stone-900">Cairn</span>
        </div>
        <div className="flex items-center gap-2">
          {loggedIn ? (
            <Link href="/articles" className="px-4 py-2 text-sm text-stone-600 hover:text-stone-900 border border-stone-200 rounded-lg transition-colors">
              Go to Library
            </Link>
          ) : (
            <a href="/login" className="px-4 py-2 text-sm text-stone-600 hover:text-stone-900 border border-stone-200 rounded-lg transition-colors">
              Sign in
            </a>
          )}
          <a href="/login" className="px-4 py-2 text-sm text-white bg-indigo-600 hover:bg-indigo-700 rounded-lg transition-colors">
            Get extension
          </a>
        </div>
      </header>

      {/* Hero */}
      <section className="text-center px-8 pt-20 pb-16">
        <div className="inline-flex items-center gap-1.5 bg-indigo-50 text-indigo-600 text-xs font-medium px-3 py-1.5 rounded-full mb-8">
          <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z" />
          </svg>
          AI-powered knowledge base
        </div>
        <h1 className="text-5xl font-semibold text-stone-900 leading-tight tracking-tight mb-6">
          Save what you read.
        </h1>
        <p className="text-lg text-stone-500 leading-relaxed max-w-lg mx-auto mb-10">
          A personal library that grows with you. Save articles with one click, get AI summaries and smart tags, then ask questions across everything you've read.
        </p>
        <div className="flex items-center justify-center gap-3">
          <a href="/login" className="inline-flex items-center gap-2 px-5 py-2.5 text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 rounded-lg transition-colors">
            <svg className="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
              <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 14H9V8h2v8zm4 0h-2V8h2v8z"/>
            </svg>
            Get Chrome Extension
          </a>
          {loggedIn ? (
            <Link href="/articles" className="inline-flex items-center gap-2 px-5 py-2.5 text-sm font-medium text-stone-600 hover:text-stone-900 border border-stone-200 hover:border-stone-300 rounded-lg transition-colors">
              Go to Library
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
            </Link>
          ) : (
            <a href="/login" className="inline-flex items-center gap-2 px-5 py-2.5 text-sm font-medium text-stone-600 hover:text-stone-900 border border-stone-200 hover:border-stone-300 rounded-lg transition-colors">
              Sign in
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
            </a>
          )}
        </div>
      </section>

      {/* Features */}
      <section className="bg-stone-50 px-8 py-16">
        <p className="text-center text-xl font-semibold text-stone-900 mb-2">Everything you need</p>
        <p className="text-center text-sm text-stone-400 mb-10">Three things that make Cairn different</p>
        <div className="grid grid-cols-3 gap-4 max-w-2xl mx-auto">
          {[
            {
              icon: (
                <svg className="w-5 h-5 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
              ),
              title: 'One-click save',
              desc: 'Save any article from Chrome instantly. No copy-paste, no friction.',
            },
            {
              icon: (
                <svg className="w-5 h-5 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z" />
                </svg>
              ),
              title: 'Auto AI summaries',
              desc: 'Every article gets a summary and smart tags automatically.',
            },
            {
              icon: (
                <svg className="w-5 h-5 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                </svg>
              ),
              title: 'Ask your library',
              desc: 'Ask anything. Get cited answers from your saved articles.',
            },
          ].map(f => (
            <div key={f.title} className="bg-white border border-stone-200/80 rounded-2xl p-5">
              <div className="w-9 h-9 bg-indigo-50 rounded-xl flex items-center justify-center mb-3">
                {f.icon}
              </div>
              <p className="text-sm font-semibold text-stone-900 mb-1.5">{f.title}</p>
              <p className="text-xs text-stone-500 leading-relaxed">{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-stone-100 py-6 text-center text-xs text-stone-400">
        Built with love · Privacy-first · Your data stays yours
      </footer>
    </div>
  )
}
