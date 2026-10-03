import { useState, type FormEvent } from 'react'
import type { Workout } from '../../lib/types'

interface AddWorkoutSheetProps {
  open: boolean
  onClose: () => void
  onSubmit: (workout: Omit<Workout, 'id'>) => void
}

export function AddWorkoutSheet({ open, onClose, onSubmit }: AddWorkoutSheetProps) {
  const [title, setTitle] = useState('')
  const [startTime, setStartTime] = useState('18:00')
  const [durationMin, setDurationMin] = useState(60)

  if (!open) return null

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!title.trim()) return

    onSubmit({
      title: title.trim(),
      startTime,
      durationMin,
      exercises: [],
      source: 'user',
      status: 'planned',
    })
    setTitle('')
    onClose()
  }

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/40 md:items-center" onClick={onClose}>
      <form
        onSubmit={handleSubmit}
        onClick={(event) => event.stopPropagation()}
        className="w-full space-y-4 rounded-t-2xl bg-white p-5 shadow-xl md:max-w-md md:rounded-2xl dark:bg-slate-900"
      >
        <h3 className="text-lg font-semibold">New workout</h3>

        <label className="block space-y-1 text-sm">
          <span className="text-slate-600 dark:text-slate-300">Name</span>
          <input
            value={title}
            onChange={(event) => setTitle(event.target.value)}
            placeholder="e.g. Legs"
            className="w-full rounded-lg border border-slate-300 bg-transparent px-3 py-2 outline-none focus:border-indigo-500 dark:border-slate-700"
            autoFocus
          />
        </label>

        <div className="grid grid-cols-2 gap-3">
          <label className="block space-y-1 text-sm">
            <span className="text-slate-600 dark:text-slate-300">Time</span>
            <input
              type="time"
              value={startTime}
              onChange={(event) => setStartTime(event.target.value)}
              className="w-full rounded-lg border border-slate-300 bg-transparent px-3 py-2 outline-none focus:border-indigo-500 dark:border-slate-700"
            />
          </label>
          <label className="block space-y-1 text-sm">
            <span className="text-slate-600 dark:text-slate-300">Duration (min)</span>
            <input
              type="number"
              min={5}
              step={5}
              value={durationMin}
              onChange={(event) => setDurationMin(Number(event.target.value))}
              className="w-full rounded-lg border border-slate-300 bg-transparent px-3 py-2 outline-none focus:border-indigo-500 dark:border-slate-700"
            />
          </label>
        </div>

        <div className="flex justify-end gap-2 pt-2">
          <button type="button" onClick={onClose} className="rounded-lg px-4 py-2 text-sm text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800">
            Cancel
          </button>
          <button type="submit" className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-500">
            Save
          </button>
        </div>
      </form>
    </div>
  )
}
