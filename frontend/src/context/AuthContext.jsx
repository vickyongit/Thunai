import React, { createContext, useContext, useState, useEffect, useCallback } from 'react'

const AuthContext = createContext(null)

const TOKEN_KEY = 'thunai_token'

function getStoredToken() {
  try {
    return localStorage.getItem(TOKEN_KEY)
  } catch {
    return null
  }
}

function setStoredToken(token) {
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token)
    else localStorage.removeItem(TOKEN_KEY)
  } catch {
    // ignore storage errors
  }
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [token, setToken] = useState(getStoredToken)
  const [loading, setLoading] = useState(true)   // true while restoring session

  const logout = useCallback(() => {
    setUser(null)
    setToken(null)
    setStoredToken(null)
  }, [])

  // Restore session on mount
  useEffect(() => {
    const storedToken = getStoredToken()
    if (!storedToken) {
      setLoading(false)
      return
    }
    // Call /api/auth/me to verify token and load user
    fetch('/api/auth/me', {
      headers: { Authorization: `Bearer ${storedToken}` },
    })
      .then((res) => {
        if (res.status === 401) {
          // Token expired or invalid — clear it
          setStoredToken(null)
          setToken(null)
          return null
        }
        return res.json()
      })
      .then((json) => {
        if (json && json.success && json.data?.user) {
          setUser(json.data.user)
          setToken(storedToken)
        } else if (json !== null) {
          // Some other error — clear token
          setStoredToken(null)
          setToken(null)
        }
      })
      .catch(() => {
        // Network error — keep token, don't log out (server might be down)
      })
      .finally(() => {
        setLoading(false)
      })
  }, [])

  const login = useCallback(async (email, password) => {
    const res = await fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    })
    const json = await res.json()
    if (!json.success) {
      throw new Error(json.error?.message || 'Login failed.')
    }
    setStoredToken(json.data.token)
    setToken(json.data.token)
    setUser(json.data.user)
    return json.data
  }, [])

  const signup = useCallback(async (name, email, password) => {
    const res = await fetch('/api/auth/signup', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, email, password }),
    })
    const json = await res.json()
    if (!json.success) {
      throw new Error(json.error?.message || 'Signup failed.')
    }
    setStoredToken(json.data.token)
    setToken(json.data.token)
    setUser(json.data.user)
    return json.data
  }, [])

  return (
    <AuthContext.Provider value={{ user, token, loading, login, signup, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
