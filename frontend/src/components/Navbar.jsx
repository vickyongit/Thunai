import React from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext.jsx'

function Navbar() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  function handleLogout() {
    logout()
    navigate('/', { replace: true })
  }

  return (
    <nav className="bg-white shadow-sm border-b border-gray-200">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          <Link to="/" className="flex items-center gap-2">
            <span className="text-2xl">💊</span>
            <span className="text-xl font-bold text-primary-600">Thunai</span>
          </Link>

          <div className="flex items-center gap-3">
            {user ? (
              <>
                <Link
                  to="/dashboard"
                  className="text-sm text-gray-700 font-medium hover:text-primary-600 transition"
                >
                  Dashboard
                </Link>
                <Link
                  to="/contacts"
                  className="text-sm text-gray-700 font-medium hover:text-primary-600 transition"
                >
                  Contacts
                </Link>
                <Link
                  to="/profile"
                  className="text-sm text-gray-700 font-medium hover:text-primary-600 transition"
                >
                  {user.name}
                </Link>
                <button
                  onClick={handleLogout}
                  className="text-sm px-4 py-1.5 border border-gray-300 rounded-lg text-gray-600 hover:bg-gray-50 transition"
                >
                  Logout
                </button>
              </>
            ) : (
              <>
                <Link
                  to="/login"
                  className="text-sm text-gray-600 hover:text-primary-600 font-medium transition"
                >
                  Log in
                </Link>
                <Link
                  to="/signup"
                  className="text-sm px-4 py-1.5 bg-primary-600 hover:bg-primary-700 text-white rounded-lg font-medium transition"
                >
                  Sign up
                </Link>
              </>
            )}
          </div>
        </div>
      </div>
    </nav>
  )
}

export default Navbar
