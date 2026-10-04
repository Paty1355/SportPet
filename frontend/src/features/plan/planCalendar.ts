import type { TrainingCalendar, Workout } from '../../lib/types'
import type { TrainingPlan } from './planApi'

// Adds the plan's workouts to the calendar on their dates. Skips workouts that are already there.
// Returns how many were added.
export function addPlanToCalendar(
  plan: TrainingPlan,
  calendar: TrainingCalendar,
  addWorkout: (iso: string, workout: Omit<Workout, 'id'>) => void,
): number {
  let added = 0
  for (const workout of plan.workouts) {
    if (!workout.date) continue
    const existing = calendar[workout.date]?.workouts ?? []
    if (existing.some((w) => w.source === 'agent' && w.title === workout.focus)) continue
    addWorkout(workout.date, {
      title: workout.focus,
      startTime: '18:00',
      durationMin: workout.exercises.reduce((sum, e) => sum + e.estimatedTimeMinutes, 0) || 60,
      exercises: workout.exercises.map((e) => ({ name: e.title, sets: e.sets, reps: e.reps, weightKg: null })),
      source: 'agent',
      status: 'planned',
    })
    added += 1
  }
  return added
}
