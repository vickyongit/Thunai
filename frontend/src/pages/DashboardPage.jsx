import React, { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext.jsx'
import { getContacts } from '../services/contactService.js'
import LoadingSpinner from '../components/LoadingSpinner.jsx'

function DashboardPage() {
  const { user } = useAuth()
  const [contactsState, setContactsState] = useState({ loading: true, count: null, error: null })

  useEffect(() => {
    let cancelled = false
    async function fetchCount() {
      try {
        const res = await getContacts()
        if (!cancelled) setContactsState({ loading: false, count: res.data?.contacts?.length ?? 0, error: null })
      } catch (err) {
        if (!cancelled) setContactsState({ loading: false, count: null, error: err.message })
      }
    }
    fetchCount()
    return () => { cancelled = true }
  }, [])

  return (
    <div className="space-y-6">
      <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-8">
        <div className="flex items-center gap-4">
          <div className="w-14 h-14 rounded-full bg-primary-100 flex items-center justify-center text-2xl font-bold text-primary-600 select-none">
            {user?.name?.[0]?.toUpperCase() || '?'}
          </div>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">
              Welcome, {user?.name || 'there'}!
            </h1>
            <p className="text-gray-500 text-sm mt-0.5">{user?.email}</p>
          </div>
        </div>
      </div>

      {/* Trusted contacts banner */}
      {contactsState.loading && (
        <div className="flex justify-center py-4"><LoadingSpinner size="sm" /></div>
      )}
      {!contactsState.loading && contactsState.count === 0 && (
        <div className="bg-amber-50 border border-amber-200 rounded-2xl p-5 flex items-start gap-4">
          <span className="text-2xl">👥</span>
          <div>
            <p className="font-semibold text-amber-900 text-sm">Add a trusted contact</p>
            <p className="text-xs text-amber-700 mt-1">
              So that your family can be alerted if you miss a dose.
            </p>
            <Link to="/contacts"
              className="inline-block mt-3 text-xs font-medium text-primary-600 hover:underline">
              Add trusted contact →
            </Link>
          </div>
        </div>
      )}

      <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6 text-center text-gray-400">
        <div className="text-4xl mb-3">🚧</div>
        <p className="text-sm">Medicine reminders and health tracking coming soon!</p>
      </div>
    </div>
  )
}

export default DashboardPage
