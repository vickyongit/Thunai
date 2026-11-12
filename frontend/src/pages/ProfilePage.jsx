import React, { useState, useEffect } from 'react'
import { useAuth } from '../context/AuthContext.jsx'
import { updateProfile } from '../services/profileService.js'
import LoadingSpinner from '../components/LoadingSpinner.jsx'

const LANGUAGES = [
  { value: 'en', label: 'English' },
  { value: 'ta', label: 'Tamil' },
]

const GENDERS = [
  { value: '', label: 'Prefer not to say' },
  { value: 'male', label: 'Male' },
  { value: 'female', label: 'Female' },
  { value: 'other', label: 'Other' },
]

function ProfilePage() {
  const { user, refreshUser } = useAuth()

  const [form, setForm] = useState({
    name: '',
    phone: '',
    age: '',
    gender: '',
    language: 'en',
    elder_mode: false,
  })
  const [errors, setErrors] = useState({})
  const [saving, setSaving] = useState(false)
  const [successMsg, setSuccessMsg] = useState('')
  const [serverError, setServerError] = useState('')

  // Populate form from user object
  useEffect(() => {
    if (user) {
      setForm({
        name: user.name || '',
        phone: user.phone || '',
        age: user.age != null ? String(user.age) : '',
        gender: user.gender || '',
        language: user.language || 'en',
        elder_mode: user.elder_mode || false,
      })
    }
  }, [user])

  // Apply elder mode to <html> element
  useEffect(() => {
    if (form.elder_mode) {
      document.documentElement.classList.add('elder-mode')
    } else {
      document.documentElement.classList.remove('elder-mode')
    }
  }, [form.elder_mode])

  function validate() {
    const e = {}
    const name = form.name.trim()
    if (!name || name.length < 2 || name.length > 60) e.name = 'Name must be 2–60 characters.'
    if (form.phone && !/^\+?\d{10,15}$/.test(form.phone.trim())) e.phone = 'Phone must be 10–15 digits, optionally starting with +.'
    if (form.age && (isNaN(Number(form.age)) || Number(form.age) < 1 || Number(form.age) > 120)) e.age = 'Age must be between 1 and 120.'
    return e
  }

  async function handleSubmit(evt) {
    evt.preventDefault()
    setSuccessMsg('')
    setServerError('')
    const e = validate()
    setErrors(e)
    if (Object.keys(e).length > 0) return

    setSaving(true)
    try {
      const payload = {
        name: form.name.trim(),
        language: form.language,
        elder_mode: form.elder_mode,
      }
      if (form.phone.trim()) payload.phone = form.phone.trim()
      if (form.age.trim()) payload.age = Number(form.age)
      if (form.gender) payload.gender = form.gender

      await updateProfile(payload)
      await refreshUser()
      setSuccessMsg('Profile saved successfully.')
    } catch (err) {
      setServerError(err.message || 'Failed to save profile.')
    } finally {
      setSaving(false)
    }
  }

  function handleChange(evt) {
    const { name, value, type, checked } = evt.target
    setForm((f) => ({ ...f, [name]: type === 'checkbox' ? checked : value }))
    setErrors((e) => ({ ...e, [name]: '' }))
    setSuccessMsg('')
  }

  if (!user) return <div className="flex justify-center py-16"><LoadingSpinner size="lg" /></div>

  return (
    <div className="max-w-xl mx-auto space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Your Profile</h1>

      <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6">
        {serverError && (
          <div className="mb-5 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
            {serverError}
          </div>
        )}
        {successMsg && (
          <div className="mb-5 p-3 bg-green-50 border border-green-200 rounded-lg text-green-700 text-sm">
            ✓ {successMsg}
          </div>
        )}

        <form onSubmit={handleSubmit} noValidate className="space-y-5">
          {/* Read-only email */}
          <div>
            <label className="block text-sm font-medium text-gray-500 mb-1">Email (cannot be changed)</label>
            <div className="px-4 py-2.5 bg-gray-50 border border-gray-200 rounded-lg text-sm text-gray-600">
              {user.email}
            </div>
          </div>

          {/* Name */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1" htmlFor="name">Full Name</label>
            <input
              id="name" name="name" type="text"
              value={form.name} onChange={handleChange} disabled={saving}
              className={`w-full px-4 py-2.5 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 transition ${errors.name ? 'border-red-400 bg-red-50' : 'border-gray-300'}`}
            />
            {errors.name && <p className="mt-1 text-xs text-red-600">{errors.name}</p>}
          </div>

          {/* Phone */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1" htmlFor="phone">Phone</label>
            <input
              id="phone" name="phone" type="tel"
              value={form.phone} onChange={handleChange} disabled={saving}
              placeholder="+91xxxxxxxxxx"
              className={`w-full px-4 py-2.5 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 transition ${errors.phone ? 'border-red-400 bg-red-50' : 'border-gray-300'}`}
            />
            {errors.phone && <p className="mt-1 text-xs text-red-600">{errors.phone}</p>}
          </div>

          {/* Age */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1" htmlFor="age">Age</label>
            <input
              id="age" name="age" type="number" min="1" max="120"
              value={form.age} onChange={handleChange} disabled={saving}
              className={`w-full px-4 py-2.5 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 transition ${errors.age ? 'border-red-400 bg-red-50' : 'border-gray-300'}`}
            />
            {errors.age && <p className="mt-1 text-xs text-red-600">{errors.age}</p>}
          </div>

          {/* Gender */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1" htmlFor="gender">Gender</label>
            <select
              id="gender" name="gender"
              value={form.gender} onChange={handleChange} disabled={saving}
              className="w-full px-4 py-2.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 transition bg-white"
            >
              {GENDERS.map((g) => <option key={g.value} value={g.value}>{g.label}</option>)}
            </select>
          </div>

          {/* Language */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1" htmlFor="language">Language</label>
            <select
              id="language" name="language"
              value={form.language} onChange={handleChange} disabled={saving}
              className="w-full px-4 py-2.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 transition bg-white"
            >
              {LANGUAGES.map((l) => <option key={l.value} value={l.value}>{l.label}</option>)}
            </select>
          </div>

          {/* Elder Mode */}
          <div className="flex items-center justify-between p-4 bg-amber-50 border border-amber-200 rounded-xl">
            <div>
              <p className="text-sm font-semibold text-amber-900">Elder Mode</p>
              <p className="text-xs text-amber-700 mt-0.5">Larger text and higher contrast for easier reading</p>
            </div>
            <button
              type="button"
              role="switch"
              aria-checked={form.elder_mode}
              onClick={() => setForm((f) => ({ ...f, elder_mode: !f.elder_mode }))}
              disabled={saving}
              className={`relative inline-flex h-7 w-13 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-primary-500 ${form.elder_mode ? 'bg-primary-600' : 'bg-gray-300'}`}
              style={{ width: '3.25rem' }}
            >
              <span
                className={`inline-block h-5 w-5 transform rounded-full bg-white shadow transition-transform ${form.elder_mode ? 'translate-x-7' : 'translate-x-1'}`}
              />
            </button>
          </div>

          <button
            type="submit" disabled={saving}
            className="w-full py-2.5 bg-primary-600 hover:bg-primary-700 disabled:bg-primary-300 text-white font-semibold rounded-lg transition text-sm"
          >
            {saving ? 'Saving…' : 'Save Profile'}
          </button>
        </form>
      </div>
    </div>
  )
}

export default ProfilePage
