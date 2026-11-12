import React from 'react'
import { Link } from 'react-router-dom'

function Navbar() {
  return (
    <nav className="bg-white shadow-sm border-b border-gray-200">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          <Link to="/" className="flex items-center gap-2">
            <span className="text-2xl">💊</span>
            <span className="text-xl font-bold text-primary-600">Thunai</span>
          </Link>
          <div className="text-sm text-gray-500">Your AI Health Companion</div>
        </div>
      </div>
    </nav>
  )
}

export default Navbar
