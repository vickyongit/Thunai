import React, { useEffect } from 'react'
import { Routes, Route, useNavigate } from 'react-router-dom'
import { AppProvider } from './context/AppContext.jsx'
import { AuthProvider } from './context/AuthContext.jsx'
import { registerLogoutCallback } from './services/api.js'
import ErrorBoundary from './components/ErrorBoundary.jsx'
import ProtectedRoute from './components/ProtectedRoute.jsx'
import PublicOnlyRoute from './components/PublicOnlyRoute.jsx'
import Navbar from './components/Navbar.jsx'
import HomePage from './pages/HomePage.jsx'
import NotFoundPage from './pages/NotFoundPage.jsx'
import LoginPage from './pages/LoginPage.jsx'
import SignupPage from './pages/SignupPage.jsx'
import DashboardPage from './pages/DashboardPage.jsx'

function AppRoutes() {
  const navigate = useNavigate()

  useEffect(() => {
    // Wire up api.js to call logout + redirect on any 401
    registerLogoutCallback(() => {
      // The actual state clearing is in AuthContext logout;
      // we redirect here because navigate is available in this component.
      // AuthContext logout is triggered by the 401 flow in AuthContext itself.
      navigate('/login', { replace: true })
    })
  }, [navigate])

  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route
            path="/login"
            element={
              <PublicOnlyRoute>
                <LoginPage />
              </PublicOnlyRoute>
            }
          />
          <Route
            path="/signup"
            element={
              <PublicOnlyRoute>
                <SignupPage />
              </PublicOnlyRoute>
            }
          />
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute>
                <DashboardPage />
              </ProtectedRoute>
            }
          />
          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </main>
    </div>
  )
}

function App() {
  return (
    <ErrorBoundary>
      <AuthProvider>
        <AppProvider>
          <AppRoutes />
        </AppProvider>
      </AuthProvider>
    </ErrorBoundary>
  )
}

export default App
