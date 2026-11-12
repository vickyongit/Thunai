const BASE_URL = import.meta.env.VITE_API_BASE_URL || ''

let _logoutCallback = null

/** Called once by AuthProvider so api.js can trigger logout on 401 */
export function registerLogoutCallback(cb) {
  _logoutCallback = cb
}

function getToken() {
  try {
    return localStorage.getItem('thunai_token')
  } catch {
    return null
  }
}

export async function request(path, options = {}) {
  const url = `${BASE_URL}${path}`
  const token = getToken()
  const headers = {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...options.headers,
  }

  let res
  try {
    res = await fetch(url, { ...options, headers })
  } catch (networkErr) {
    throw new Error('Network error — please check your connection.')
  }

  // 401: token invalid/expired — trigger logout + redirect
  if (res.status === 401) {
    if (_logoutCallback) _logoutCallback()
    // Don't throw the redirect; throw an auth error
    const json = await res.json().catch(() => ({}))
    throw new Error(json?.error?.message || 'Session expired. Please log in again.')
  }

  let json
  try {
    json = await res.json()
  } catch {
    throw new Error(`Server returned non-JSON response (status ${res.status}).`)
  }

  if (!res.ok || !json.success) {
    const msg = json?.error?.message || `Request failed with status ${res.status}`
    throw new Error(msg)
  }

  return json
}

export async function getHealthStatus() {
  return request('/api/health')
}
