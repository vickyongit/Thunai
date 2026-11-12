import { request } from './api.js'

export async function getProfile() {
  return request('/api/profile/')
}

export async function updateProfile(data) {
  return request('/api/profile/', {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}
