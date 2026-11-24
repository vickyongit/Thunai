import { request } from './api.js'

export async function getToday() {
  return request('/api/doses/today')
}

export async function takeDose(id) {
  return request(`/api/doses/${id}/take`, { method: 'POST' })
}

export async function undoDose(id) {
  return request(`/api/doses/${id}/undo`, { method: 'POST' })
}
