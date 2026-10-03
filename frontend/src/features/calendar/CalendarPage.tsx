import { useMemo, useState } from 'react'
import { ChevronLeft, ChevronRight } from 'lucide-react'
import { buildMonthGrid, formatDayTitle, formatMonthTitle, parseISODate, toISODate } from '../../lib/dates'
import type { TrainingCalendar, Workout } from '../../lib/types'
import { mockCalendar } from '../../mocks/calendar'
import { AddWorkoutSheet } from './AddWorkoutSheet'
import { DayDetails } from './DayDetails'
import { MonthGrid } from './MonthGrid'

export function CalendarPage() {
  const today = new Date()
  const [year, setYear] = useState(today.getFullYear())
  const [month, setMonth] = useState(today.getMonth())
  const [selectedISO, setSelectedISO] = useState(toISODate(today))
  const [calendar, setCalendar] = useState<TrainingCalendar>(mockCalendar)
  const [sheetOpen, setSheetOpen] = useState(false)

  const cells = useMemo(() => buildMonthGrid(year, month), [year, month])

  function shiftMonth(delta: number) {
    const next = new Date(year, month + delta, 1)
    setYear(next.getFullYear())
    setMonth(next.getMonth())
  }

  function addWorkout(workout: Omit<Workout, 'id'>) {
    const newWorkout: Workout = { ...workout, id: crypto.randomUUID() }
    setCalendar((prev) => {
      const day = prev[selectedISO] ?? { workouts: [] }
      return { ...prev, [selectedISO]: { workouts: [...day.workouts, newWorkout] } }
    })
  }

  const selectedDate = parseISODate(selectedISO)

  return (
    <div className="md:grid md:grid-cols-2 md:items-start md:gap-8">
      <section className="space-y-4 rounded-3xl bg-white p-4 shadow-sm ring-1 ring-slate-200/70 dark:bg-slate-900 dark:ring-slate-800">
        <header className="flex items-center justify-between">
          <button
            type="button"
            onClick={() => shiftMonth(-1)}
            aria-label="Previous month"
            className="rounded-lg p-2 transition hover:bg-slate-100 dark:hover:bg-slate-800"
          >
            <ChevronLeft size={20} />
          </button>
          <h1 className="text-lg font-semibold capitalize">{formatMonthTitle(year, month)}</h1>
          <button
            type="button"
            onClick={() => shiftMonth(1)}
            aria-label="Next month"
            className="rounded-lg p-2 transition hover:bg-slate-100 dark:hover:bg-slate-800"
          >
            <ChevronRight size={20} />
          </button>
        </header>

        <MonthGrid cells={cells} calendar={calendar} selectedISO={selectedISO} onSelect={setSelectedISO} />
      </section>

      <section className="mt-8 md:mt-0">
        <p className="mb-3 text-sm font-medium capitalize text-slate-500 dark:text-slate-400">
          {formatDayTitle(selectedDate)}
        </p>
        <DayDetails plan={calendar[selectedISO]} onAdd={() => setSheetOpen(true)} />
      </section>

      <AddWorkoutSheet open={sheetOpen} onClose={() => setSheetOpen(false)} onSubmit={addWorkout} />
    </div>
  )
}
