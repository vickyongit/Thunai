import React from 'react'
import { useAuth } from '../context/AuthContext.jsx'

function DashboardPage() {
  const { user } = useAuth()

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

      <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6 text-center text-gray-400">
        <div className="text-4xl mb-3">🚧</div>
        <p className="text-sm">Your health dashboard is coming soon. More features in the next step!</p>
      </div>
    </div>
  )
}

export default DashboardPage
