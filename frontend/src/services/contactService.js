import { request } from './api.js'

export async function getContacts() {
  return request('/api/contacts/')
}

export async function createContact(data) {
  return request('/api/contacts/', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateContact(id, data) {
  return request(`/api/contacts/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function deleteContact(id) {
  return request(`/api/contacts/${id}`, {
    method: 'DELETE',
  })
}
