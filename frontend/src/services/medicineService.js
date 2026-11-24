import { request } from './api.js'

export async function getMedicines(activeOnly = false) {
  const qs = activeOnly ? '?active=true' : ''
  return request(`/api/medicines/${qs}`)
}

export async function getMedicine(id) {
  return request(`/api/medicines/${id}`)
}

export async function createMedicine(data) {
  return request('/api/medicines/', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateMedicine(id, data) {
  return request(`/api/medicines/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function deleteMedicine(id) {
  return request(`/api/medicines/${id}`, {
    method: 'DELETE',
  })
}
