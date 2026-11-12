const BASE_URL = import.meta.env.VITE_API_BASE_URL || ''

async function request(path, options = {}) {
  const url = `${BASE_URL}${path}`
  const headers = { 'Content-Type': 'application/json', ...options.headers }

  const res = await fetch(url, { ...options, headers })
  const json = await res.json()

  if (!res.ok || !json.success) {
    const msg = json?.error?.message || `Request failed with status ${res.status}`
    throw new Error(msg)
  }

  return json
}

export async function getHealthStatus() {
  return request('/api/health')
}
