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
    <div className="flex items-center justify-center min-h-screen bg-stone-50 px-4">
      <div className="w-full max-w-sm">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="flex justify-center mb-3">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" className="text-indigo-600">
              <ellipse cx="12" cy="20" rx="7" ry="2.5" fill="currentColor" opacity="0.9"/>
              <ellipse cx="12" cy="14.5" rx="5" ry="2" fill="currentColor" opacity="0.8"/>
              <ellipse cx="12" cy="9.5" rx="3.5" ry="1.8" fill="currentColor" opacity="0.7"/>
              <ellipse cx="12" cy="5.5" rx="2" ry="1.5" fill="currentColor" opacity="0.6"/>
            </svg>
          </div>
          <h1 className="text-2xl font-bold text-stone-900">Cairn</h1>
          <p className="text-stone-500 text-sm mt-1">
            {isSwitching ? 'Sign in with a different account' : 'Sign in to your library'}
          </p>
        </div>

        <div className="bg-white border border-stone-200 rounded-xl p-8 shadow-sm">
          <div className="flex justify-center">
            <GoogleLogin
              onSuccess={handleGoogleSuccess}
              onError={() => setError('Google login failed')}
              useOneTap={!isSwitching}
              shape="rectangular"
              size="large"
              width="320"
            />
          </div>
          {error && <p className="text-red-500 text-sm text-center mt-4">{error}</p>}
          {loading && <p className="text-stone-400 text-sm text-center mt-4">Signing in...</p>}
        </div>
      </div>
    </div>
  )
}
