import type { DayPlan, Workout, WorkoutStatus } from '../../lib/types'

const STATUS_LABEL: Record<WorkoutStatus, string> = {
  planned: 'Planned',
  done: 'Done',
  skipped: 'Skipped',
}

const STATUS_STYLE: Record<WorkoutStatus, string> = {
  planned: 'bg-indigo-100 text-indigo-700 dark:bg-indigo-500/20 dark:text-indigo-300',
  done: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-300',
  skipped: 'bg-slate-200 text-slate-600 dark:bg-slate-700 dark:text-slate-300',
}

interface DayDetailsProps {
  plan: DayPlan | undefined
  onAdd: () => void
}

export function DayDetails({ plan, onAdd }: DayDetailsProps) {
  const workouts = plan?.workouts ?? []

  return (
    <section className="space-y-3">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-slate-600 dark:text-slate-300">Workouts this day</h2>
        <button
          type="button"
          onClick={onAdd}
          className="rounded-lg bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-500"
        >
          Add workout
        </button>
      </div>

      {workouts.length === 0 ? (
        <p className="rounded-xl border border-dashed border-slate-300 p-4 text-sm text-slate-500 dark:border-slate-700 dark:text-slate-400">
          No workouts yet. Add one or ask the agent for a plan.
        </p>
      ) : (
        <ul className="space-y-2">
          {workouts.map((workout) => (
            <WorkoutCard key={workout.id} workout={workout} />
          ))}
        </ul>
      )}
    </section>
  )
}

function WorkoutCard({ workout }: { workout: Workout }) {
  return (
    <li className="rounded-xl bg-white p-4 shadow-sm dark:bg-slate-900">
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="font-semibold">{workout.title}</p>
          <p className="text-sm text-slate-500 dark:text-slate-400">
            {workout.startTime} · {workout.durationMin} min · {workout.source === 'agent' ? 'by agent' : 'manual'}
          </p>
        </div>
        <span className={`shrink-0 rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_STYLE[workout.status]}`}>
          {STATUS_LABEL[workout.status]}
        </span>
      </div>

      {workout.exercises.length > 0 && (
        <ul className="mt-3 space-y-1 text-sm text-slate-600 dark:text-slate-300">
          {workout.exercises.map((exercise) => (
            <li key={exercise.name} className="flex justify-between gap-2">
              <span>{exercise.name}</span>
              <span className="tabular-nums text-slate-500 dark:text-slate-400">
                {exercise.sets}×{exercise.reps}
                {exercise.weightKg !== null && ` · ${exercise.weightKg} kg`}
              </span>
            </li>
          ))}
        </ul>
      )}
    </li>
  )
}
