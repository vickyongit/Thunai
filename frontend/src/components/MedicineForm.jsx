import React, { useState, useEffect } from 'react'

// ── constants ─────────────────────────────────────────────────────────────────
const FOOD_OPTIONS = [
  { value: 'any', label: 'Any time' },
  { value: 'before_food', label: 'Before food' },
  { value: 'after_food', label: 'After food' },
  { value: 'with_food', label: 'With food' },
]

const DAY_LABELS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

const EMPTY_FORM = {
  name: '',
  dosage: '',
  pills_per_dose: 1,
  times: ['08:00'],
  repeat_type: 'daily',
  days_of_week: [],
  start_date: new Date().toISOString().slice(0, 10),
  end_date: '',
  food_instruction: 'any',
  remarks: '',
  pills_remaining: '',
  is_active: true,
}

// ── helpers ───────────────────────────────────────────────────────────────────
function InputField({ label, error, children }) {
  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-1">{label}</label>
      {children}
      {error && <p className="mt-1 text-xs text-red-600">{error}</p>}
    </div>
  )
}

function cls(...parts) {
  return parts.filter(Boolean).join(' ')
}

// ── MedicineForm ──────────────────────────────────────────────────────────────
function MedicineForm({ initial, onSave, onCancel, saving, serverError }) {
  const [form, setForm] = useState(() => ({
    ...EMPTY_FORM,
    ...(initial || {}),
    times: initial?.times?.length ? [...initial.times] : ['08:00'],
    days_of_week: initial?.days_of_week ? [...initial.days_of_week] : [],
  }))
  const [errors, setErrors] = useState({})

  // ── client-side validation ────────────────────────────────────────────────
  function validate() {
    const e = {}
    if (!form.name.trim() || form.name.trim().length < 2 || form.name.trim().length > 80)
      e.name = 'Name must be 2–80 characters.'
    if (!form.dosage.trim() || form.dosage.trim().length < 1 || form.dosage.trim().length > 50)
      e.dosage = 'Dosage is required (e.g. "500 mg").'
    const ppd = Number(form.pills_per_dose)
    if (!Number.isInteger(ppd) || ppd < 1 || ppd > 20)
      e.pills_per_dose = 'Pills per dose must be an integer 1–20.'
    if (form.times.length === 0 || form.times.length > 6)
      e.times = 'Add 1–6 times.'
    const timeRe = /^([01]\d|2[0-3]):([0-5]\d)$/
    const badTimes = form.times.filter((t) => !timeRe.test(t))
    if (badTimes.length) e.times = `Invalid time(s): ${badTimes.join(', ')}.`
    if (new Set(form.times).size !== form.times.length) e.times = 'Duplicate times are not allowed.'
    if (!['daily', 'specific_days'].includes(form.repeat_type)) e.repeat_type = 'Select a repeat type.'
    if (form.repeat_type === 'specific_days' && form.days_of_week.length === 0)
      e.days_of_week = 'Select at least one day.'
    if (form.start_date && form.end_date && form.end_date < form.start_date)
      e.end_date = 'End date must not be before start date.'
    if (form.pills_remaining !== '' && form.pills_remaining !== null) {
      const pr = Number(form.pills_remaining)
      if (!Number.isInteger(pr) || pr < 0 || pr > 10000)
        e.pills_remaining = 'Pills remaining must be 0–10000.'
    }
    if (form.remarks && form.remarks.length > 300) e.remarks = 'Max 300 characters.'
    return e
  }

  // ── handlers ─────────────────────────────────────────────────────────────
  function set(field, value) {
    setForm((f) => ({ ...f, [field]: value }))
    setErrors((e) => ({ ...e, [field]: '' }))
  }

  function handleChange(evt) {
    const { name, value, type, checked } = evt.target
    set(name, type === 'checkbox' ? checked : value)
  }

  function handleTimeChange(idx, value) {
    const next = [...form.times]
    next[idx] = value
    set('times', next)
  }

  function addTime() {
    if (form.times.length >= 6) return
    set('times', [...form.times, '12:00'])
  }

  function removeTime(idx) {
    if (form.times.length <= 1) return
    set('times', form.times.filter((_, i) => i !== idx))
  }

  function toggleDay(day) {
    const next = form.days_of_week.includes(day)
      ? form.days_of_week.filter((d) => d !== day)
      : [...form.days_of_week, day]
    set('days_of_week', next)
  }

  function handleSubmit(evt) {
    evt.preventDefault()
    const e = validate()
    setErrors(e)
    if (Object.keys(e).length > 0) return

    const payload = {
      name: form.name.trim(),
      dosage: form.dosage.trim(),
      pills_per_dose: Number(form.pills_per_dose),
      times: [...new Set(form.times)].sort(),
      repeat_type: form.repeat_type,
      days_of_week: form.repeat_type === 'specific_days' ? form.days_of_week.sort((a, b) => a - b) : [],
      start_date: form.start_date || new Date().toISOString().slice(0, 10),
      end_date: form.end_date || null,
      food_instruction: form.food_instruction,
      remarks: form.remarks.trim() || null,
      pills_remaining: form.pills_remaining !== '' && form.pills_remaining !== null
        ? Number(form.pills_remaining) : null,
      is_active: Boolean(form.is_active),
    }
    onSave(payload)
  }

  const inputCls = (field) =>
    cls(
      'w-full px-3 py-2 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 transition',
      errors[field] ? 'border-red-400 bg-red-50' : 'border-gray-300'
    )

  return (
    <form onSubmit={handleSubmit} noValidate className="space-y-5">
      {serverError && (
        <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">{serverError}</div>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {/* Name */}
        <InputField label="Medicine Name *" error={errors.name}>
          <input name="name" value={form.name} onChange={handleChange} disabled={saving}
            className={inputCls('name')} placeholder="e.g. Metformin" />
        </InputField>

        {/* Dosage */}
        <InputField label="Dosage *" error={errors.dosage}>
          <input name="dosage" value={form.dosage} onChange={handleChange} disabled={saving}
            className={inputCls('dosage')} placeholder="e.g. 500 mg" />
        </InputField>

        {/* Pills per dose */}
        <InputField label="Pills per Dose *" error={errors.pills_per_dose}>
          <input name="pills_per_dose" type="number" min="1" max="20"
            value={form.pills_per_dose} onChange={handleChange} disabled={saving}
            className={inputCls('pills_per_dose')} />
        </InputField>

        {/* Food instruction */}
        <InputField label="Food Instruction" error={errors.food_instruction}>
          <select name="food_instruction" value={form.food_instruction}
            onChange={handleChange} disabled={saving}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-primary-500 transition">
            {FOOD_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
        </InputField>
      </div>

      {/* Times */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Dose Times * <span className="text-xs text-gray-400">(1–6)</span>
        </label>
        <div className="flex flex-wrap gap-2 mb-2">
          {form.times.map((t, idx) => (
            <div key={idx} className="flex items-center gap-1">
              <input type="time" value={t} disabled={saving}
                onChange={(e) => handleTimeChange(idx, e.target.value)}
                className="border border-gray-300 rounded-lg px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500" />
              {form.times.length > 1 && (
                <button type="button" onClick={() => removeTime(idx)} disabled={saving}
                  className="text-red-400 hover:text-red-600 text-lg leading-none select-none px-1">×</button>
              )}
            </div>
          ))}
          {form.times.length < 6 && (
            <button type="button" onClick={addTime} disabled={saving}
              className="text-sm px-3 py-1.5 border border-dashed border-primary-400 text-primary-600 rounded-lg hover:bg-primary-50 transition">
              + Add time
            </button>
          )}
        </div>
        {errors.times && <p className="text-xs text-red-600">{errors.times}</p>}
      </div>

      {/* Repeat type */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">Repeat *</label>
        <div className="flex gap-3 mb-3">
          {['daily', 'specific_days'].map((rt) => (
            <label key={rt} className="flex items-center gap-2 cursor-pointer text-sm">
              <input type="radio" name="repeat_type" value={rt} checked={form.repeat_type === rt}
                onChange={handleChange} disabled={saving} className="text-primary-600" />
              {rt === 'daily' ? 'Every day' : 'Specific days'}
            </label>
          ))}
        </div>
        {form.repeat_type === 'specific_days' && (
          <div className="flex flex-wrap gap-2">
            {DAY_LABELS.map((label, idx) => (
              <button key={idx} type="button" disabled={saving}
                onClick={() => toggleDay(idx)}
                className={cls(
                  'px-3 py-1.5 rounded-lg text-xs font-medium border transition',
                  form.days_of_week.includes(idx)
                    ? 'bg-primary-600 text-white border-primary-600'
                    : 'bg-white text-gray-600 border-gray-300 hover:border-primary-400'
                )}>
                {label}
              </button>
            ))}
          </div>
        )}
        {errors.days_of_week && <p className="mt-1 text-xs text-red-600">{errors.days_of_week}</p>}
      </div>

      {/* Dates */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <InputField label="Start Date *" error={errors.start_date}>
          <input name="start_date" type="date" value={form.start_date}
            onChange={handleChange} disabled={saving} className={inputCls('start_date')} />
        </InputField>
        <InputField label="End Date (optional)" error={errors.end_date}>
          <input name="end_date" type="date" value={form.end_date}
            onChange={handleChange} disabled={saving} className={inputCls('end_date')} />
        </InputField>
      </div>

      {/* Pills remaining + is_active */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <InputField label="Pills Remaining (optional)" error={errors.pills_remaining}>
          <input name="pills_remaining" type="number" min="0" max="10000"
            value={form.pills_remaining} onChange={handleChange} disabled={saving}
            placeholder="Leave blank if unknown"
            className={inputCls('pills_remaining')} />
        </InputField>
        <div className="flex items-end pb-1">
          <label className="flex items-center gap-2 cursor-pointer text-sm text-gray-700 select-none">
            <input type="checkbox" name="is_active" checked={form.is_active}
              onChange={handleChange} disabled={saving} className="rounded text-primary-600 w-4 h-4" />
            Active (taking this medicine)
          </label>
        </div>
      </div>

      {/* Remarks */}
      <InputField label="Remarks (optional)" error={errors.remarks}>
        <textarea name="remarks" rows={2} maxLength={300}
          value={form.remarks} onChange={handleChange} disabled={saving}
          placeholder="Additional notes…"
          className={cls('w-full px-3 py-2 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 transition resize-none',
            errors.remarks ? 'border-red-400 bg-red-50' : 'border-gray-300')} />
      </InputField>

      {/* Actions */}
      <div className="flex gap-3 pt-1">
        <button type="submit" disabled={saving}
          className="px-6 py-2.5 bg-primary-600 hover:bg-primary-700 disabled:bg-primary-300 text-white text-sm font-semibold rounded-lg transition min-h-[44px]">
          {saving ? 'Saving…' : 'Save Medicine'}
        </button>
        <button type="button" onClick={onCancel} disabled={saving}
          className="px-6 py-2.5 border border-gray-300 text-gray-600 text-sm rounded-lg hover:bg-gray-50 transition min-h-[44px]">
          Cancel
        </button>
      </div>
    </form>
  )
}

export default MedicineForm
