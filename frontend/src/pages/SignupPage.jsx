import React, { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext.jsx'

function SignupPage() {
  const { signup } = useAuth()
  const navigate = useNavigate()

  const [form, setForm] = useState({ name: '', email: '', password: '' })
  const [errors, setErrors] = useState({})
  const [serverError, setServerError] = useState('')
  const [loading, setLoading] = useState(false)
  const [showPassword, setShowPassword] = useState(false)

  function validate() {
    const e = {}
    const name = form.name.trim()
    if (!name || name.length < 2 || name.length > 60) e.name = 'Name must be 2–60 characters.'
    if (!form.email.trim()) e.email = 'Email is required.'
    else if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(form.email)) e.email = 'Enter a valid email.'
    if (!form.password) e.password = 'Password is required.'
    else if (!/^(?=.*[A-Za-z])(?=.*\d).{8,}$/.test(form.password))
      e.password = 'Min 8 chars with at least 1 letter and 1 number.'
    return e
  }

  async function handleSubmit(evt) {
    evt.preventDefault()
    setServerError('')
    const e = validate()
    setErrors(e)
    if (Object.keys(e).length > 0) return

    setLoading(true)
    try {
      await signup(form.name, form.email, form.password)
      navigate('/dashboard', { replace: true })
    } catch (err) {
      setServerError(err.message || 'Signup failed. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  function handleChange(evt) {
    const { name, value } = evt.target
    setForm((f) => ({ ...f, [name]: value }))
    setErrors((e) => ({ ...e, [name]: '' }))
  }

  return (
    <div className="min-h-[80vh] flex items-center justify-center px-4">
      <div className="w-full max-w-md bg-white rounded-2xl shadow-md border border-gray-200 p-8">
        <div className="text-center mb-8">
          <div className="text-5xl mb-3">💊</div>
          <h1 className="text-2xl font-bold text-gray-900">Create your account</h1>
          <p className="text-gray-500 text-sm mt-1">Start your health journey with Thunai</p>
        </div>

        {serverError && (
          <div className="mb-5 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
            {serverError}
          </div>
        )}

        <form onSubmit={handleSubmit} noValidate className="space-y-5">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1" htmlFor="name">
              Full Name
            </label>
            <input
              id="name"
              name="name"
              type="text"
              autoComplete="name"
              value={form.name}
              onChange={handleChange}
              disabled={loading}
              className={`w-full px-4 py-2.5 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 transition ${
                errors.name ? 'border-red-400 bg-red-50' : 'border-gray-300'
              }`}
              placeholder="Jane Doe"
            />
            {errors.name && <p className="mt-1 text-xs text-red-600">{errors.name}</p>}
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1" htmlFor="email">
              Email
            </label>
            <input
              id="email"
              name="email"
              type="email"
              autoComplete="email"
              value={form.email}
              onChange={handleChange}
              disabled={loading}
              className={`w-full px-4 py-2.5 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 transition ${
                errors.email ? 'border-red-400 bg-red-50' : 'border-gray-300'
              }`}
              placeholder="you@example.com"
            />
            {errors.email && <p className="mt-1 text-xs text-red-600">{errors.email}</p>}
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1" htmlFor="password">
              Password
            </label>
            <div className="relative">
              <input
                id="password"
                name="password"
                type={showPassword ? 'text' : 'password'}
                autoComplete="new-password"
                value={form.password}
                onChange={handleChange}
                disabled={loading}
                className={`w-full px-4 py-2.5 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 transition pr-11 ${
                  errors.password ? 'border-red-400 bg-red-50' : 'border-gray-300'
                }`}
                placeholder="Min 8 chars, 1 letter, 1 number"
              />
              <button
                type="button"
                onClick={() => setShowPassword((s) => !s)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 text-sm select-none"
                tabIndex={-1}
              >
                {showPassword ? '🙈' : '👁️'}
              </button>
            </div>
            {errors.password && <p className="mt-1 text-xs text-red-600">{errors.password}</p>}
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-2.5 bg-primary-600 hover:bg-primary-700 disabled:bg-primary-300 text-white font-semibold rounded-lg transition text-sm"
          >
            {loading ? 'Creating account…' : 'Create account'}
          </button>
        </form>

        <p className="mt-6 text-center text-sm text-gray-500">
          Already have an account?{' '}
          <Link to="/login" className="text-primary-600 font-medium hover:underline">
            Log in
          </Link>
        </p>
      </div>
    </div>
  )
}

export default SignupPage
