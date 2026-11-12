import React from 'react'
import { Link } from 'react-router-dom'

function NotFoundPage() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] text-center">
      <div className="text-7xl mb-6">🔍</div>
      <h1 className="text-4xl font-bold text-gray-800 mb-3">404 — Page Not Found</h1>
      <p className="text-gray-500 mb-8 max-w-md">
        The page you are looking for does not exist or has been moved.
      </p>
      <Link
        to="/"
        className="px-6 py-3 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors font-medium"
      >
        Go Home
      </Link>
    </div>
  )
}

export default NotFoundPage
