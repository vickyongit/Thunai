import React, { useState, useEffect, useCallback } from 'react'
import {
  getMedicines, createMedicine, updateMedicine, deleteMedicine,
} from '../services/medicineService.js'
import MedicineForm from '../components/MedicineForm.jsx'
import LoadingSpinner from '../components/LoadingSpinner.jsx'

// ── helpers ───────────────────────────────────────────────────────────────────
const DAY_LABELS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

const FOOD_LABELS = {
  before_food: 'Before food',
  after_food: 'After food',
  with_food: 'With food',
  any: 'Any time',
}

function repeatSummary(med) {
  if (med.repeat_type === 'daily') return 'Every day'
  const days = (med.days_of_week || []).map((d) => DAY_LABELS[d]).join(', ')
  return days || 'Specific days'
}

function cls(...parts) { return parts.filter(Boolean).join(' ') }

// ── MedicineCard ──────────────────────────────────────────────────────────────
function MedicineCard({ med, onEdit, onDelete, onToggleActive }) {
  const [toggling, setToggling] = useState(false)

  async function handleToggle() {
    setToggling(true)
    try {
      await onToggleActive(med)
    } finally {
      setToggling(false)
    }
  }

  return (
    <div className={cls(
      'bg-white rounded-xl border shadow-sm p-5 transition',
      med.is_active ? 'border-gray-200' : 'border-gray-100 opacity-70'
    )}>
      {/* header */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <h3 className="font-semibold text-gray-900 truncate">{med.name}</h3>
            <span className={cls(
              'text-xs px-2 py-0.5 rounded-full font-medium shrink-0',
              med.is_active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'
            )}>
              {med.is_active ? 'Active' : 'Paused'}
            </span>
          </div>
          <p className="text-sm text-gray-500 mt-0.5">{med.dosage} · {med.pills_per_dose} pill{med.pills_per_dose !== 1 ? 's' : ''} per dose</p>
        </div>
        <div className="flex gap-2 shrink-0">
          <button onClick={() => onEdit(med)} title="Edit"
            className="text-xs px-3 py-1.5 border border-gray-300 rounded-lg text-gray-600 hover:bg-gray-50 transition min-h-[36px]">
            Edit
          </button>
          <button onClick={() => onDelete(med)} title="Delete"
            className="text-xs px-3 py-1.5 border border-red-200 rounded-lg text-red-600 hover:bg-red-50 transition min-h-[36px]">
            Delete
          </button>
        </div>
      </div>

      {/* times */}
      <div className="mt-3 flex flex-wrap gap-1.5">
        {(med.times || []).map((t) => (
          <span key={t} className="text-xs bg-primary-50 text-primary-700 border border-primary-200 px-2 py-0.5 rounded-full font-mono">
            {t}
          </span>
        ))}
      </div>

      {/* meta row */}
      <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-xs text-gray-500">
        <span>🔁 {repeatSummary(med)}</span>
        <span>🍽 {FOOD_LABELS[med.food_instruction] || med.food_instruction}</span>
        {med.pills_remaining != null && <span>💊 {med.pills_remaining} left</span>}
        {med.end_date && <span>Until {med.end_date}</span>}
      </div>

      {med.remarks && (
        <p className="mt-2 text-xs text-gray-400 italic truncate">{med.remarks}</p>
      )}

      {/* pause/resume */}
      <div className="mt-4 border-t border-gray-100 pt-3">
        <button onClick={handleToggle} disabled={toggling}
          className={cls(
            'text-xs px-4 py-1.5 rounded-lg border transition font-medium min-h-[36px]',
            med.is_active
              ? 'border-amber-300 text-amber-700 hover:bg-amber-50'
              : 'border-green-300 text-green-700 hover:bg-green-50'
          )}>
          {toggling ? '…' : med.is_active ? 'Pause' : 'Resume'}
        </button>
      </div>
    </div>
  )
}

// ── ConfirmDialog ─────────────────────────────────────────────────────────────
function ConfirmDialog({ name, onConfirm, onCancel, loading }) {
  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 px-4">
      <div className="bg-white rounded-2xl shadow-xl p-6 max-w-sm w-full">
        <h2 className="text-lg font-bold text-gray-900 mb-2">Delete medicine?</h2>
        <p className="text-sm text-gray-500 mb-6">
          Are you sure you want to remove <strong>{name}</strong>?
          Past dose history will be preserved.
        </p>
        <div className="flex gap-3">
          <button onClick={onConfirm} disabled={loading}
            className="flex-1 py-2.5 bg-red-600 hover:bg-red-700 disabled:bg-red-300 text-white text-sm font-semibold rounded-lg transition min-h-[44px]">
            {loading ? 'Deleting…' : 'Delete'}
          </button>
          <button onClick={onCancel} disabled={loading}
            className="flex-1 py-2.5 border border-gray-300 text-gray-600 text-sm rounded-lg hover:bg-gray-50 transition min-h-[44px]">
            Cancel
          </button>
        </div>
      </div>
    </div>
  )
}

// ── MedicinesPage ─────────────────────────────────────────────────────────────
function MedicinesPage() {
  const [medicines, setMedicines] = useState([])
  const [loadState, setLoadState] = useState({ loading: true, error: null })
  const [showForm, setShowForm] = useState(false)
  const [editingMed, setEditingMed] = useState(null)
  const [saving, setSaving] = useState(false)
  const [formError, setFormError] = useState('')
  const [deleteTarget, setDeleteTarget] = useState(null)
  const [deleting, setDeleting] = useState(false)

  const fetchMedicines = useCallback(async () => {
    setLoadState({ loading: true, error: null })
    try {
      const res = await getMedicines()
      setMedicines(res.data?.medicines || [])
      setLoadState({ loading: false, error: null })
    } catch (err) {
      setLoadState({ loading: false, error: err.message })
    }
  }, [])

  useEffect(() => { fetchMedicines() }, [fetchMedicines])

  async function handleSave(payload) {
    setSaving(true)
    setFormError('')
    try {
      if (editingMed) {
        await updateMedicine(editingMed.id, payload)
      } else {
        await createMedicine(payload)
      }
      setShowForm(false)
      setEditingMed(null)
      await fetchMedicines()
    } catch (err) {
      setFormError(err.message || 'Failed to save.')
    } finally {
      setSaving(false)
    }
  }

  function handleEditClick(med) {
    setEditingMed(med)
    setFormError('')
    setShowForm(true)
  }

  function handleAddClick() {
    setEditingMed(null)
    setFormError('')
    setShowForm(true)
  }

  function handleCancel() {
    setShowForm(false)
    setEditingMed(null)
    setFormError('')
  }

  async function handleToggleActive(med) {
    try {
      await updateMedicine(med.id, { is_active: !med.is_active })
      await fetchMedicines()
    } catch (err) {
      // Surface the error inline — no white screen
      setLoadState((s) => ({ ...s, error: err.message }))
    }
  }

  async function handleDeleteConfirm() {
    if (!deleteTarget) return
    setDeleting(true)
    try {
      await deleteMedicine(deleteTarget.id)
      setDeleteTarget(null)
      await fetchMedicines()
    } catch (err) {
      setDeleteTarget(null)
      setLoadState((s) => ({ ...s, error: err.message }))
    } finally {
      setDeleting(false)
    }
  }

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      {/* header */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">My Medicines</h1>
        {!showForm && medicines.length < 30 && (
          <button onClick={handleAddClick}
            className="px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white text-sm font-semibold rounded-lg transition min-h-[44px]">
            + Add Medicine
          </button>
        )}
      </div>

      {/* form panel */}
      {showForm && (
        <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-6">
          <h2 className="text-base font-semibold text-gray-800 mb-5">
            {editingMed ? 'Edit Medicine' : 'New Medicine'}
          </h2>
          <MedicineForm
            initial={editingMed}
            onSave={handleSave}
            onCancel={handleCancel}
            saving={saving}
            serverError={formError}
          />
        </div>
      )}

      {/* loading */}
      {loadState.loading && (
        <div className="flex justify-center py-12">
          <LoadingSpinner size="md" message="Loading medicines…" />
        </div>
      )}

      {/* error */}
      {!loadState.loading && loadState.error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-xl text-red-700 text-sm flex justify-between items-center">
          <span>{loadState.error}</span>
          <button onClick={fetchMedicines} className="ml-3 underline text-red-600">Retry</button>
        </div>
      )}

      {/* empty state */}
      {!loadState.loading && !loadState.error && medicines.length === 0 && !showForm && (
        <div className="text-center py-16 bg-white rounded-2xl border border-dashed border-gray-300">
          <div className="text-5xl mb-4">💊</div>
          <h2 className="text-lg font-semibold text-gray-700 mb-2">No medicines yet</h2>
          <p className="text-sm text-gray-400 mb-6 max-w-xs mx-auto">
            Add your first medicine to start tracking your doses.
          </p>
          <button onClick={handleAddClick}
            className="px-5 py-3 bg-primary-600 hover:bg-primary-700 text-white text-sm font-semibold rounded-lg transition min-h-[44px]">
            Add your first medicine
          </button>
        </div>
      )}

      {/* medicine list */}
      {!loadState.loading && medicines.length > 0 && (
        <div className="space-y-3">
          {medicines.map((m) => (
            <MedicineCard
              key={m.id}
              med={m}
              onEdit={handleEditClick}
              onDelete={setDeleteTarget}
              onToggleActive={handleToggleActive}
            />
          ))}
          {medicines.length >= 30 && (
            <p className="text-xs text-center text-gray-400 py-2">Maximum of 30 medicines reached.</p>
          )}
        </div>
      )}

      {/* delete confirm */}
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

export default MedicinesPage
