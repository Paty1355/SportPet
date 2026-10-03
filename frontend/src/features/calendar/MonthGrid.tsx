import { WEEKDAY_LABELS, toISODate } from '../../lib/dates'
import type { TrainingCalendar } from '../../lib/types'

interface MonthGridProps {
  cells: (Date | null)[]
  calendar: TrainingCalendar
  selectedISO: string
  onSelect: (iso: string) => void
}

export function MonthGrid({ cells, calendar, selectedISO, onSelect }: MonthGridProps) {
  const todayISO = toISODate(new Date())

  return (
    <div>
      <div className="grid grid-cols-7 pb-2 text-center text-xs font-medium text-slate-500 dark:text-slate-400">
        {WEEKDAY_LABELS.map((label) => (
          <div key={label}>{label}</div>
        ))}
      </div>

      <div className="grid grid-cols-7 gap-1">
        {cells.map((date, index) => {
          if (!date) return <div key={`empty-${index}`} />

          const iso = toISODate(date)
          const workoutCount = calendar[iso]?.workouts.length ?? 0
          const isSelected = iso === selectedISO
          const isToday = iso === todayISO

          return (
            <button
              key={iso}
              type="button"
              onClick={() => onSelect(iso)}
              aria-pressed={isSelected}
              className={[
                'flex aspect-square flex-col items-center justify-center rounded-xl text-sm transition',
                isSelected
                  ? 'bg-indigo-600 font-semibold text-white shadow-md'
                  : 'hover:bg-slate-200/70 dark:hover:bg-slate-800',
                isToday && !isSelected ? 'ring-1 ring-indigo-500' : '',
              ].join(' ')}
            >
              <span>{date.getDate()}</span>
              {workoutCount > 0 && (
                <span
                  className={[
                    'mt-0.5 h-1.5 w-1.5 rounded-full',
                    isSelected ? 'bg-white' : 'bg-indigo-500',
                  ].join(' ')}
                  aria-label={`${workoutCount} workouts`}
                />
              )}
            </button>
          )
        })}
      </div>
    </div>
  )
}
