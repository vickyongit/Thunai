import React, { useState, useEffect, useCallback } from 'react'
import { Link } from 'react-router-dom'
import {
  getContacts, createContact, updateContact, deleteContact
} from '../services/contactService.js'
import LoadingSpinner from '../components/LoadingSpinner.jsx'

const PRIORITY_LABELS = { 1: 'Primary', 2: 'Secondary' }
const PRIORITY_COLORS = {
  1: 'bg-primary-100 text-primary-700',
  2: 'bg-blue-100 text-blue-700',
}

const EMPTY_FORM = {
  name: '', phone: '', relationship: '', priority: 3, notify_on_missed: true
}

function ContactForm({ initial, onSave, onCancel, saving, serverError }) {
  const [form, setForm] = useState(initial || EMPTY_FORM)
  const [errors, setErrors] = useState({})

  function validate() {
    const e = {}
    if (!form.name.trim() || form.name.trim().length < 2) e.name = 'Name must be at least 2 characters.'
    if (!/^\+?\d{10,15}$/.test(form.phone.trim())) e.phone = 'Phone must be 10–15 digits, optionally starting with +.'
    if (!form.relationship.trim()) e.relationship = 'Relationship is required.'
    if (!form.priority || Number(form.priority) < 1) e.priority = 'Priority must be a positive number.'
    return e
  }

  function handleChange(evt) {
    const { name, value, type, checked } = evt.target
    setForm((f) => ({ ...f, [name]: type === 'checkbox' ? checked : value }))
    setErrors((e) => ({ ...e, [name]: '' }))
  }

  function handleSubmit(evt) {
    evt.preventDefault()
    const e = validate()
    setErrors(e)
    if (Object.keys(e).length > 0) return
    onSave({
      name: form.name.trim(),
      phone: form.phone.trim(),
      relationship: form.relationship.trim(),
      priority: Number(form.priority),
      notify_on_missed: Boolean(form.notify_on_missed),
    })
  }

  return (
    <form onSubmit={handleSubmit} noValidate className="space-y-4">
      {serverError && (
        <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">{serverError}</div>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Name</label>
          <input name="name" value={form.name} onChange={handleChange} disabled={saving}
            className={`w-full px-3 py-2 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 ${errors.name ? 'border-red-400 bg-red-50' : 'border-gray-300'}`}
            placeholder="Jane Doe" />
          {errors.name && <p className="mt-1 text-xs text-red-600">{errors.name}</p>}
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Phone</label>
          <input name="phone" value={form.phone} onChange={handleChange} disabled={saving}
            className={`w-full px-3 py-2 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 ${errors.phone ? 'border-red-400 bg-red-50' : 'border-gray-300'}`}
            placeholder="+91xxxxxxxxxx" />
          {errors.phone && <p className="mt-1 text-xs text-red-600">{errors.phone}</p>}
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Relationship</label>
          <input name="relationship" value={form.relationship} onChange={handleChange} disabled={saving}
            className={`w-full px-3 py-2 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 ${errors.relationship ? 'border-red-400 bg-red-50' : 'border-gray-300'}`}
            placeholder="son, daughter, doctor…" />
          {errors.relationship && <p className="mt-1 text-xs text-red-600">{errors.relationship}</p>}
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Priority</label>
          <select name="priority" value={form.priority} onChange={handleChange} disabled={saving}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 bg-white">
            <option value={1}>1 — Primary</option>
            <option value={2}>2 — Secondary</option>
            <option value={3}>3 — Other</option>
            <option value={4}>4 — Other</option>
            <option value={5}>5 — Other</option>
          </select>
          {errors.priority && <p className="mt-1 text-xs text-red-600">{errors.priority}</p>}
        </div>
      </div>

      <label className="flex items-center gap-2 text-sm text-gray-700 cursor-pointer">
        <input type="checkbox" name="notify_on_missed" checked={form.notify_on_missed}
          onChange={handleChange} disabled={saving} className="rounded text-primary-600" />
        Notify on missed dose
      </label>

      <div className="flex gap-3 pt-2">
        <button type="submit" disabled={saving}
          className="px-5 py-2 bg-primary-600 hover:bg-primary-700 disabled:bg-primary-300 text-white text-sm font-semibold rounded-lg transition">
          {saving ? 'Saving…' : 'Save'}
        </button>
        <button type="button" onClick={onCancel} disabled={saving}
          className="px-5 py-2 border border-gray-300 text-gray-600 text-sm rounded-lg hover:bg-gray-50 transition">
          Cancel
        </button>
      </div>
    </form>
  )
}

function ContactCard({ contact, onEdit, onDelete }) {
  const priorityLabel = PRIORITY_LABELS[contact.priority]
  const priorityColor = PRIORITY_COLORS[contact.priority] || 'bg-gray-100 text-gray-600'

  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-5">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-primary-100 flex items-center justify-center font-bold text-primary-600 text-sm select-none">
            {contact.name[0]?.toUpperCase()}
          </div>
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <p className="font-semibold text-gray-900 text-sm">{contact.name}</p>
              {priorityLabel && (
                <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${priorityColor}`}>
                  {priorityLabel}
                </span>
              )}
            </div>
            <p className="text-xs text-gray-500 capitalize">{contact.relationship}</p>
            <p className="text-xs text-gray-600 mt-0.5">{contact.phone}</p>
          </div>
        </div>
        <div className="flex gap-2 shrink-0">
          <button onClick={() => onEdit(contact)}
            className="text-xs px-3 py-1.5 border border-gray-300 rounded-lg text-gray-600 hover:bg-gray-50 transition">
            Edit
          </button>
          <button onClick={() => onDelete(contact)}
            className="text-xs px-3 py-1.5 border border-red-200 rounded-lg text-red-600 hover:bg-red-50 transition">
            Delete
          </button>
        </div>
      </div>
      {contact.notify_on_missed && (
        <p className="mt-3 text-xs text-gray-400 flex items-center gap-1">
          <span>🔔</span> Will be notified on missed doses
        </p>
      )}
    </div>
  )
}

function ConfirmDialog({ name, onConfirm, onCancel, loading }) {
  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 px-4">
      <div className="bg-white rounded-2xl shadow-xl p-6 max-w-sm w-full">
        <h2 className="text-lg font-bold text-gray-900 mb-2">Delete contact?</h2>
        <p className="text-sm text-gray-500 mb-6">
          Are you sure you want to remove <strong>{name}</strong>? This cannot be undone.
        </p>
        <div className="flex gap-3">
          <button onClick={onConfirm} disabled={loading}
            className="flex-1 py-2 bg-red-600 hover:bg-red-700 disabled:bg-red-300 text-white text-sm font-semibold rounded-lg transition">
            {loading ? 'Deleting…' : 'Delete'}
          </button>
          <button onClick={onCancel} disabled={loading}
            className="flex-1 py-2 border border-gray-300 text-gray-600 text-sm rounded-lg hover:bg-gray-50 transition">
            Cancel
          </button>
        </div>
      </div>
    </div>
  )
}

function ContactsPage() {
  const [contacts, setContacts] = useState([])
  const [loadState, setLoadState] = useState({ loading: true, error: null })
  const [showForm, setShowForm] = useState(false)
  const [editingContact, setEditingContact] = useState(null)
  const [saving, setSaving] = useState(false)
  const [formError, setFormError] = useState('')
  const [deleteTarget, setDeleteTarget] = useState(null)
  const [deleting, setDeleting] = useState(false)

  const fetchContacts = useCallback(async () => {
    setLoadState({ loading: true, error: null })
    try {
      const res = await getContacts()
      setContacts(res.data?.contacts || [])
      setLoadState({ loading: false, error: null })
    } catch (err) {
      setLoadState({ loading: false, error: err.message })
    }
  }, [])

  useEffect(() => { fetchContacts() }, [fetchContacts])

  async function handleSave(formData) {
    setSaving(true)
    setFormError('')
    try {
      if (editingContact) {
        await updateContact(editingContact.id, formData)
      } else {
        await createContact(formData)
      }
      setShowForm(false)
      setEditingContact(null)
      await fetchContacts()
    } catch (err) {
      setFormError(err.message || 'Failed to save contact.')
    } finally {
      setSaving(false)
    }
  }

  function handleEditClick(contact) {
    setEditingContact(contact)
    setFormError('')
    setShowForm(true)
  }

  function handleAddClick() {
    setEditingContact(null)
    setFormError('')
    setShowForm(true)
  }

  function handleCancel() {
    setShowForm(false)
    setEditingContact(null)
    setFormError('')
  }

  async function handleDeleteConfirm() {
    if (!deleteTarget) return
    setDeleting(true)
    try {
      await deleteContact(deleteTarget.id)
      setDeleteTarget(null)
      await fetchContacts()
    } catch (err) {
      setDeleteTarget(null)
      setLoadState((s) => ({ ...s, error: err.message }))
    } finally {
      setDeleting(false)
    }
  }

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Trusted Contacts</h1>
        {!showForm && contacts.length < 5 && (
          <button onClick={handleAddClick}
            className="px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white text-sm font-semibold rounded-lg transition">
            + Add Contact
          </button>
        )}
      </div>

      {/* Add/Edit form */}
      {showForm && (
        <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-6">
          <h2 className="text-base font-semibold text-gray-800 mb-4">
            {editingContact ? 'Edit Contact' : 'New Contact'}
          </h2>
          <ContactForm
            initial={editingContact ? {
              name: editingContact.name,
              phone: editingContact.phone,
              relationship: editingContact.relationship,
              priority: editingContact.priority,
              notify_on_missed: editingContact.notify_on_missed,
            } : EMPTY_FORM}
            onSave={handleSave}
            onCancel={handleCancel}
            saving={saving}
            serverError={formError}
          />
        </div>
      )}

      {/* Loading */}
      {loadState.loading && (
        <div className="flex justify-center py-12"><LoadingSpinner size="md" message="Loading contacts…" /></div>
      )}

      {/* Error */}
      {!loadState.loading && loadState.error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-xl text-red-700 text-sm">
          {loadState.error}
          <button onClick={fetchContacts} className="ml-3 underline text-red-600">Retry</button>
        </div>
      )}

      {/* Empty state */}
      {!loadState.loading && !loadState.error && contacts.length === 0 && !showForm && (
        <div className="text-center py-16 bg-white rounded-2xl border border-dashed border-gray-300">
          <div className="text-5xl mb-4">👥</div>
          <h2 className="text-lg font-semibold text-gray-700 mb-2">No trusted contacts yet</h2>
          <p className="text-sm text-gray-400 mb-6 max-w-xs mx-auto">
            Add family members or doctors so they can be alerted if you miss a dose.
          </p>
          <button onClick={handleAddClick}
            className="px-5 py-2.5 bg-primary-600 hover:bg-primary-700 text-white text-sm font-semibold rounded-lg transition">
            Add your first contact
          </button>
        </div>
      )}

      {/* Contact list */}
      {!loadState.loading && contacts.length > 0 && (
        <div className="space-y-3">
          {contacts.map((c) => (
            <ContactCard key={c.id} contact={c} onEdit={handleEditClick} onDelete={setDeleteTarget} />
          ))}
          {contacts.length >= 5 && (
            <p className="text-xs text-center text-gray-400">Maximum of 5 contacts reached.</p>
          )}
        </div>
      )}

      {/* Delete confirm dialog */}
      {deleteTarget && (
        <ConfirmDialog
          name={deleteTarget.name}
          onConfirm={handleDeleteConfirm}
          onCancel={() => setDeleteTarget(null)}
          loading={deleting}
        />
      )}
    </div>
  )
}

export default ContactsPage
