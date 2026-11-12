import React, { useState, useEffect } from 'react'
import LoadingSpinner from '../components/LoadingSpinner.jsx'
import { getHealthStatus } from '../services/api.js'

function HomePage() {
  const [apiStatus, setApiStatus] = useState({ loading: true, data: null, error: null })

  useEffect(() => {
    let cancelled = false
    async function checkApi() {
      try {
        const data = await getHealthStatus()
        if (!cancelled) setApiStatus({ loading: false, data, error: null })
      } catch (err) {
        if (!cancelled) setApiStatus({ loading: false, data: null, error: err.message })
      }
    }
    checkApi()
    return () => { cancelled = true }
  }, [])

  return (
    <div className="space-y-8">
      <section className="text-center py-12">
        <div className="text-6xl mb-4">💊</div>
        <h1 className="text-4xl font-bold text-gray-900 mb-3">Welcome to Thunai</h1>
        <p className="text-lg text-gray-500 max-w-xl mx-auto">
          Your AI-powered health companion. Never miss a dose, stay connected with family, and track your health — all in one place.
        </p>
      </section>

      <section className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 max-w-sm mx-auto">
        <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">API Status</h2>
        {apiStatus.loading && <LoadingSpinner size="sm" message="Connecting to server..." />}
        {!apiStatus.loading && apiStatus.error && (
          <div className="flex items-center gap-2 text-red-600">
            <span className="w-2 h-2 rounded-full bg-red-500 inline-block" />
            <span className="text-sm">Backend offline — {apiStatus.error}</span>
          </div>
        )}
        {!apiStatus.loading && apiStatus.data && (
          <div className="flex items-center gap-2 text-green-600">
            <span className="w-2 h-2 rounded-full bg-green-500 inline-block animate-pulse" />
            <span className="text-sm font-medium">
              {apiStatus.data.data?.service} v{apiStatus.data.data?.version} — {apiStatus.data.data?.status}
            </span>
          </div>
        )}
      </section>
    </div>
  )
}

export default HomePage
