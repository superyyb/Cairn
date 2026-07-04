'use client'

import { useState, useEffect } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { GoogleLogin } from '@react-oauth/google'
import { tryRestoreSession } from '@/lib/api'
import { saveToken, isLoggedIn } from '@/lib/auth'

export default function LoginPage() {
  const router = useRouter()
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const searchParams = useSearchParams()
  const isSwitching = searchParams.get('switch') === 'true'

  useEffect(() => {
    if (isLoggedIn()) {
      router.replace('/articles')
      return
    }
    if (!isSwitching) {
      tryRestoreSession().then(ok => { if (ok) router.replace('/articles') })
    }
  }, [router, isSwitching])

  async function handleGoogleSuccess(credentialResponse: { credential?: string }) {
    if (!credentialResponse.credential) return
    setError('')
    setLoading(true)
    try {
      const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const res = await fetch(`${API_BASE}/api/auth/google?client_type=web`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ credential: credentialResponse.credential }),
      })
      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || 'Google login failed')
      }
      const data = await res.json()
      saveToken(data.access_token)
      router.push('/articles')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Google login failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex min-h-screen">

      {/* ── Left panel ── */}
      <div
        className="hidden lg:flex flex-col w-1/2 relative overflow-hidden px-14 py-12 gap-10"
        style={{ backgroundImage: "url('/Cairn_backend.png')", backgroundSize: 'cover', backgroundPosition: 'center' }}
      >
        {/* Logo */}
        <div className="flex items-center gap-3 z-10">
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none">
            <ellipse cx="12" cy="20" rx="7" ry="2.5" fill="#818cf8" opacity="0.9"/>
            <ellipse cx="12" cy="14.5" rx="5" ry="2" fill="#818cf8" opacity="0.8"/>
            <ellipse cx="12" cy="9.5" rx="3.5" ry="1.8" fill="#818cf8" opacity="0.7"/>
            <ellipse cx="12" cy="5.5" rx="2" ry="1.5" fill="#818cf8" opacity="0.6"/>
          </svg>
          <span className="text-white font-semibold text-lg tracking-wide">Cairn</span>
        </div>

        {/* Hero text + feature cards */}
        <div className="z-10 flex flex-col gap-8 mt-auto mb-auto">
          <div>
            <h1 className="text-5xl font-bold text-white leading-tight mb-6">
              Save what<br />you read<span className="text-indigo-400">.</span>
            </h1>
            <div className="border-l-2 border-indigo-400 pl-4">
              <p className="text-indigo-200 text-base leading-relaxed max-w-sm">
                A personal library that grows with you. Save articles with one click,
                get AI summaries and smart tags, then ask questions across everything you&apos;ve read.
              </p>
            </div>
          </div>

        {/* Feature cards */}
        <div className="grid grid-cols-4 gap-3 z-10">
          {[
            { icon: (
                <svg className="w-7 h-7" fill="none" stroke="#a78bfa" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z"/>
                </svg>
              ), label: 'One-click save' },
            { icon: (
                <svg className="w-7 h-7" fill="none" stroke="#a78bfa" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z"/>
                </svg>
              ), label: 'AI summaries' },
            { icon: (
                <svg className="w-7 h-7" fill="none" stroke="#a78bfa" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z"/>
                </svg>
              ), label: 'Smart tags' },
            { icon: (
                <svg className="w-7 h-7" fill="none" stroke="#a78bfa" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"/>
                </svg>
              ), label: 'Ask AI what you read' },
          ].map(({ icon, label }) => (
            <div key={label} className="flex flex-col items-center justify-center gap-3 bg-white/[0.07] backdrop-blur-sm rounded-2xl py-5 px-3 text-center aspect-[6/4]">
              {icon}
              <span className="text-white text-base leading-snug">{label}</span>
            </div>
          ))}
        </div>
        </div>
      </div>

      {/* ── Right panel ── */}
      <div className="flex-1 flex flex-col bg-stone-50">
        {/* Top-right logo */}
        <div className="flex justify-end p-6">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-full bg-indigo-600 flex items-center justify-center">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
                <ellipse cx="12" cy="20" rx="7" ry="2.5" fill="white" opacity="0.9"/>
                <ellipse cx="12" cy="14.5" rx="5" ry="2" fill="white" opacity="0.8"/>
                <ellipse cx="12" cy="9.5" rx="3.5" ry="1.8" fill="white" opacity="0.7"/>
                <ellipse cx="12" cy="5.5" rx="2" ry="1.5" fill="white" opacity="0.6"/>
              </svg>
            </div>
            <span className="text-sm font-semibold text-stone-800">Cairn</span>
          </div>
        </div>

        {/* Center form */}
        <div className="flex-1 flex flex-col items-center justify-center px-8 -mt-12">
          {/* Logo circle */}
          <div className="relative mb-8">
            <div className="w-20 h-20 rounded-full bg-indigo-50 border border-indigo-100 flex items-center justify-center">
              <svg width="36" height="36" viewBox="0 0 24 24" fill="none">
                <ellipse cx="12" cy="20" rx="7" ry="2.5" fill="#4f46e5" opacity="0.9"/>
                <ellipse cx="12" cy="14.5" rx="5" ry="2" fill="#4f46e5" opacity="0.8"/>
                <ellipse cx="12" cy="9.5" rx="3.5" ry="1.8" fill="#4f46e5" opacity="0.7"/>
                <ellipse cx="12" cy="5.5" rx="2" ry="1.5" fill="#4f46e5" opacity="0.6"/>
              </svg>
            </div>
            {/* Decorative dots */}
            <span className="absolute -top-1 -right-1 w-2 h-2 rounded-full bg-indigo-200" />
            <span className="absolute top-3 -right-3 w-1.5 h-1.5 rounded-full bg-indigo-100" />
            <span className="absolute -bottom-1 -left-2 w-1.5 h-1.5 rounded-full bg-indigo-200" />
          </div>

          <h2 className="text-2xl font-bold text-stone-900 mb-2 text-center">
            {isSwitching ? 'Sign in with a different account' : 'Welcome back'}
          </h2>
          <p className="text-stone-400 text-sm mb-8 text-center">
            {isSwitching ? 'Choose a Google account to continue.' : 'Sign in to your library.'}
          </p>

          <div className="w-full max-w-xs bg-white border border-stone-200 rounded-2xl p-6 shadow-sm flex flex-col items-center gap-3">
            <GoogleLogin
              onSuccess={handleGoogleSuccess}
              onError={() => setError('Google login failed')}
              useOneTap={!isSwitching}
              shape="rectangular"
              size="large"
              width="260"
            />
            {error && <p className="text-red-500 text-xs text-center">{error}</p>}
            {loading && <p className="text-stone-400 text-xs text-center">Signing in...</p>}
          </div>
        </div>

        {/* Bottom security note */}
        <div className="flex items-center justify-center gap-3 pb-8 text-stone-400">
          <svg className="w-4 h-4 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"/>
          </svg>
          <div className="text-xs">
            <p className="font-medium text-stone-500">Your data is private and secure</p>
            <p>We never sell your data. Ever.</p>
          </div>
        </div>
      </div>

    </div>
  )
}
