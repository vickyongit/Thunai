import React, { useState, useEffect, useCallback, useRef } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext.jsx'
import { getContacts } from '../services/contactService.js'
import { getToday, takeDose, undoDose } from '../services/doseService.js'
import LoadingSpinner from '../components/LoadingSpinner.jsx'

// ── Helpers ──────────────────────────────────────────────────────────────────

function formatDate(dateStr) {
  if (!dateStr) return ''
  const [y, m, d] = dateStr.split('-').map(Number)
  const date = new Date(y, m - 1, d)
  return date.toLocaleDateString('en-IN', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })
}

function formatTime12(timeStr) {
  if (!timeStr) return ''
  const [hStr, mStr] = timeStr.split(':')
  const h = parseInt(hStr, 10)
  const m = mStr
  const ampm = h >= 12 ? 'PM' : 'AM'
  const h12 = h % 12 || 12
  return `${h12}:${m} ${ampm}`
}

function formatTakenAt(isoStr) {
  if (!isoStr) return ''
  const d = new Date(isoStr)
  return d.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', hour12: true })
}

function formatCountdown(scheduledAt, status, wasLate, takenAt, serverTimeOffset) {
  if (status === 'taken') {
    const takenStr = takenAt ? formatTakenAt(takenAt) : '—'
    return `Taken at ${takenStr}${wasLate ? ' · Late' : ''}`
  }

  const adjustedNow = new Date(Date.now() - serverTimeOffset)
  const scheduled = new Date(scheduledAt)
  const diffMs = scheduled - adjustedNow

  if (diffMs > 5 * 60 * 1000) {
    const totalMins = Math.round(diffMs / 60000)
    if (totalMins >= 60) {
      const h = Math.floor(totalMins / 60)
      const min = totalMins % 60
      return min > 0 ? `in ${h}h ${min}min` : `in ${h}h`
    }
    return `in ${totalMins} min`
  } else if (diffMs >= 0) {
    return 'Due now'
  } else {
    const overdueMins = Math.floor(-diffMs / 60000)
    if (overdueMins < 1) return 'Due now'
    return `Overdue by ${overdueMins} min`
  }
}

const FOOD_LABELS = {
  before_food: 'Before food',
  after_food: 'After food',
  with_food: 'With food',
  any: '',
}

const STATUS_BADGE = {
  taken:   { bg: 'bg-green-100',  text: 'text-green-700',  label: 'Taken' },
  pending: { bg: 'bg-yellow-100', text: 'text-yellow-700', label: 'Pending' },
  missed:  { bg: 'bg-red-100',    text: 'text-red-700',    label: 'Missed' },
}

// ── Summary Card ─────────────────────────────────────────────────────────────

function SummaryCard({ label, count, colorClass }) {
  return (
    <div className={`rounded-xl p-4 flex flex-col items-center justify-center gap-1 ${colorClass}`}>
      <span className="text-2xl font-bold">{count}</span>
      <span className="text-xs font-medium uppercase tracking-wide opacity-80">{label}</span>
    </div>
  )
}

// ── Dose Card ────────────────────────────────────────────────────────────────

function DoseCard({ dose, serverTimeOffset, onTake, onUndo, loadingIds }) {
  const [countdown, setCountdown] = useState(() =>
    formatCountdown(dose.scheduled_at, dose.status, dose.was_late, dose.taken_at, serverTimeOffset)
  )

  useEffect(() => {
    const update = () => setCountdown(
      formatCountdown(dose.scheduled_at, dose.status, dose.was_late, dose.taken_at, serverTimeOffset)
    )
    update()
    const timer = setInterval(update, 30_000)
    return () => clearInterval(timer)
  }, [dose.scheduled_at, dose.status, dose.was_late, dose.taken_at, serverTimeOffset])

  const isBusy = loadingIds.has(dose.id)
  const badge = STATUS_BADGE[dose.status] || STATUS_BADGE.pending
  const foodLabel = FOOD_LABELS[dose.food_instruction] || ''

  return (
    <div className={`bg-white rounded-2xl border p-5 shadow-sm transition-all ${
      dose.status === 'taken' ? 'border-green-200 bg-green-50/30' :
      dose.status === 'missed' ? 'border-red-200' : 'border-gray-200'
    }`}>
      <div className="flex items-start justify-between gap-3 flex-wrap">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 flex-wrap">
            <h3 className="font-semibold text-gray-900 text-base truncate">{dose.name}</h3>
            <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${badge.bg} ${badge.text}`}>
              {badge.label}
            </span>
          </div>
          <p className="text-sm text-gray-500 mt-0.5">
            {dose.dosage} · {dose.pills_per_dose} pill{dose.pills_per_dose !== 1 ? 's' : ''}
            {foodLabel ? ` · ${foodLabel}` : ''}
          </p>
        </div>
        <div className="text-right flex-shrink-0">
          <p className="font-mono text-lg font-semibold text-gray-800">{formatTime12(dose.scheduled_time)}</p>
          <p className={`text-xs mt-0.5 ${
            dose.status === 'taken' ? 'text-green-600' :
            countdown.startsWith('Overdue') ? 'text-red-500' :
            countdown === 'Due now' ? 'text-yellow-600 font-semibold' : 'text-gray-500'
          }`}>{countdown}</p>
        </div>
      </div>

      <div className="mt-4 flex gap-2 items-center justify-end">
        {dose.status !== 'taken' && (
          <button
            onClick={() => onTake(dose.id)}
            disabled={isBusy}
            className="min-h-[48px] elder-mode:min-h-[56px] px-5 rounded-xl font-semibold text-sm bg-green-500 hover:bg-green-600 active:scale-95 text-white transition-all disabled:opacity-60 disabled:cursor-not-allowed shadow-sm"
          >
            {isBusy ? <LoadingSpinner size="sm" /> : '✓ Mark as Taken'}
          </button>
        )}
        {dose.status === 'taken' && (
          <button
            onClick={() => onUndo(dose.id)}
            disabled={isBusy}
            className="min-h-[40px] px-4 rounded-xl font-medium text-sm bg-gray-100 hover:bg-gray-200 active:scale-95 text-gray-600 transition-all disabled:opacity-60 disabled:cursor-not-allowed"
          >
            {isBusy ? <LoadingSpinner size="sm" /> : 'Undo'}
          </button>
        )}
      </div>
    </div>
  )
}

// ── Main Page ─────────────────────────────────────────────────────────────────

function DashboardPage() {
  const { user } = useAuth()

  // Contacts banner
  const [contactsState, setContactsState] = useState({ loading: true, count: null, error: null })

  // Today schedule
  const [schedule, setSchedule] = useState(null)      // { date, timezone, server_time, summary, doses }
  const [dosesLoading, setDosesLoading] = useState(true)
  const [dosesError, setDosesError] = useState(null)
  const [serverTimeOffset, setServerTimeOffset] = useState(0)

  // Per-dose loading state (Set of ids in-flight)
  const [loadingIds, setLoadingIds] = useState(new Set())

  // Refs for cleanup
  const cancelledRef = useRef(false)

  // ── fetch contacts count ──
  useEffect(() => {
    let cancelled = false
    async function fetchCount() {
      try {
        const res = await getContacts()
        if (!cancelled) setContactsState({ loading: false, count: res.data?.contacts?.length ?? 0, error: null })
      } catch (err) {
        if (!cancelled) setContactsState({ loading: false, count: null, error: err.message })
      }
    }
    fetchCount()
    return () => { cancelled = true }
  }, [])

  // ── fetch today's schedule ──
  const fetchSchedule = useCallback(async () => {
    try {
      const res = await getToday()
      if (cancelledRef.current) return
      const data = res.data
      setSchedule(data)
      setServerTimeOffset(Date.now() - new Date(data.server_time).getTime())
      setDosesError(null)
    } catch (err) {
      if (!cancelledRef.current) setDosesError(err.message || 'Failed to load today\'s schedule.')
    } finally {
      if (!cancelledRef.current) setDosesLoading(false)
    }
  }, [])

  useEffect(() => {
    cancelledRef.current = false
    fetchSchedule()

    // Refetch every 60 seconds
    const interval = setInterval(fetchSchedule, 60_000)

    // Refetch when tab regains focus
    const handleVisibility = () => {
      if (document.visibilityState === 'visible') fetchSchedule()
    }
    document.addEventListener('visibilitychange', handleVisibility)

    return () => {
      cancelledRef.current = true
      clearInterval(interval)
      document.removeEventListener('visibilitychange', handleVisibility)
    }
  }, [fetchSchedule])

  // ── optimistic take ──
  const handleTake = useCallback(async (doseId) => {
    if (loadingIds.has(doseId)) return
    setLoadingIds(prev => new Set(prev).add(doseId))

    // Optimistic update
    const prevSchedule = schedule
    setSchedule(prev => {
      if (!prev) return prev
      const doses = prev.doses.map(d =>
        d.id === doseId
          ? { ...d, status: 'taken', taken_at: new Date().toISOString(), was_late: false }
          : d
      )
      const taken = doses.filter(d => d.status === 'taken').length
      const missed = doses.filter(d => d.status === 'missed').length
      return { ...prev, doses, summary: { ...prev.summary, taken, pending: doses.length - taken - missed, missed } }
    })

    try {
      const res = await takeDose(doseId)
      // Merge server truth into local state
      if (!cancelledRef.current) {
        setSchedule(prev => {
          if (!prev) return prev
          const doses = prev.doses.map(d => d.id === doseId ? res.data : d)
          const taken = doses.filter(d => d.status === 'taken').length
          const missed = doses.filter(d => d.status === 'missed').length
          return { ...prev, doses, summary: { ...prev.summary, taken, pending: doses.length - taken - missed, missed } }
        })
      }
    } catch (err) {
      // Roll back
      if (!cancelledRef.current) {
        setSchedule(prevSchedule)
        alert(err.message || 'Could not mark dose as taken. Please try again.')
      }
    } finally {
      if (!cancelledRef.current) {
        setLoadingIds(prev => { const s = new Set(prev); s.delete(doseId); return s })
      }
    }
  }, [loadingIds, schedule])

  // ── optimistic undo ──
  const handleUndo = useCallback(async (doseId) => {
    if (loadingIds.has(doseId)) return
    setLoadingIds(prev => new Set(prev).add(doseId))

    const prevSchedule = schedule
    setSchedule(prev => {
      if (!prev) return prev
      const doses = prev.doses.map(d =>
        d.id === doseId ? { ...d, status: 'pending', taken_at: null, was_late: false } : d
      )
      const taken = doses.filter(d => d.status === 'taken').length
      const missed = doses.filter(d => d.status === 'missed').length
      return { ...prev, doses, summary: { ...prev.summary, taken, pending: doses.length - taken - missed, missed } }
    })

    try {
      const res = await undoDose(doseId)
      if (!cancelledRef.current) {
        setSchedule(prev => {
          if (!prev) return prev
          const doses = prev.doses.map(d => d.id === doseId ? res.data : d)
          const taken = doses.filter(d => d.status === 'taken').length
          const missed = doses.filter(d => d.status === 'missed').length
          return { ...prev, doses, summary: { ...prev.summary, taken, pending: doses.length - taken - missed, missed } }
        })
      }
    } catch (err) {
      if (!cancelledRef.current) {
        setSchedule(prevSchedule)
        alert(err.message || 'Could not undo dose. Please try again.')
      }
    } finally {
      if (!cancelledRef.current) {
        setLoadingIds(prev => { const s = new Set(prev); s.delete(doseId); return s })
      }
    }
  }, [loadingIds, schedule])

  // ── render ──
  return (
    <div className="space-y-6">
      {/* Greeting */}
      <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6 md:p-8">
        <div className="flex items-center gap-4">
          <div className="w-14 h-14 rounded-full bg-primary-100 flex items-center justify-center text-2xl font-bold text-primary-600 select-none flex-shrink-0">
            {user?.name?.[0]?.toUpperCase() || '?'}
          </div>
          <div className="min-w-0">
            <h1 className="text-2xl font-bold text-gray-900 truncate">
              Welcome, {user?.name || 'there'}!
            </h1>
            <p className="text-gray-500 text-sm mt-0.5">
              {schedule ? formatDate(schedule.date) : new Date().toLocaleDateString('en-IN', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}
            </p>
          </div>
        </div>
      </div>

      {/* Trusted contacts banner */}
      {contactsState.loading && (
        <div className="flex justify-center py-2"><LoadingSpinner size="sm" /></div>
      )}
      {!contactsState.loading && contactsState.count === 0 && (
        <div className="bg-amber-50 border border-amber-200 rounded-2xl p-5 flex items-start gap-4">
          <span className="text-2xl">👥</span>
          <div>
            <p className="font-semibold text-amber-900 text-sm">Add a trusted contact</p>
            <p className="text-xs text-amber-700 mt-1">
              So that your family can be alerted if you miss a dose.
            </p>
            <Link to="/contacts" className="inline-block mt-3 text-xs font-medium text-primary-600 hover:underline">
              Add trusted contact →
            </Link>
          </div>
        </div>
      )}

      {/* Today's schedule */}
      {dosesLoading && (
        <div className="bg-white rounded-2xl border border-gray-200 p-10 flex justify-center">
          <LoadingSpinner size="lg" />
        </div>
      )}

      {!dosesLoading && dosesError && (
        <div className="bg-red-50 border border-red-200 rounded-2xl p-6 text-center">
          <p className="text-red-700 font-medium text-sm">⚠️ {dosesError}</p>
          <button
            onClick={() => { setDosesLoading(true); setDosesError(null); fetchSchedule() }}
            className="mt-3 text-sm font-medium text-primary-600 hover:underline"
          >
            Retry
          </button>
        </div>
      )}

      {!dosesLoading && !dosesError && schedule && (
        <>
          {/* Summary cards */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <SummaryCard label="Total"   count={schedule.summary.total}   colorClass="bg-gray-100 text-gray-700" />
            <SummaryCard label="Taken"   count={schedule.summary.taken}   colorClass="bg-green-100 text-green-800" />
            <SummaryCard label="Pending" count={schedule.summary.pending} colorClass="bg-yellow-100 text-yellow-800" />
            <SummaryCard label="Missed"  count={schedule.summary.missed}  colorClass="bg-red-100 text-red-800" />
          </div>

          {/* Dose list */}
          {schedule.doses.length === 0 ? (
            <div className="bg-white rounded-2xl border border-gray-200 p-10 text-center text-gray-400">
              <div className="text-4xl mb-3">💊</div>
              <p className="text-sm font-medium text-gray-500">No doses scheduled for today.</p>
              <Link to="/medicines" className="inline-block mt-3 text-sm text-primary-600 hover:underline">
                Add a medicine →
              </Link>
            </div>
          ) : (
            <div className="space-y-3">
              <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide">
                Today's Doses
              </h2>
              {schedule.doses.map(dose => (
                <DoseCard
                  key={dose.id}
                  dose={dose}
                  serverTimeOffset={serverTimeOffset}
                  onTake={handleTake}
                  onUndo={handleUndo}
                  loadingIds={loadingIds}
                />
              ))}
            </div>
          )}
        </>
      )}
    </div>
  )
}

export default DashboardPage
