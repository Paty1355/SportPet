import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from 'react'
import type { TrainingPlan } from '../features/plan/planApi'
import type { TrainingCalendar, Workout, WorkoutStatus } from './types'

interface TrainingContextValue {
  calendar: TrainingCalendar
  addWorkout: (iso: string, workout: Omit<Workout, 'id'>) => void
  setWorkoutStatus: (iso: string, workoutId: string, status: WorkoutStatus) => void
  // The backend plan, shared by the Plan screen and the calendar so both show the same workouts.
  plan: TrainingPlan | null
  setPlan: (plan: TrainingPlan | null) => void
}

const TrainingContext = createContext<TrainingContextValue | null>(null)

export function TrainingProvider({ children }: { children: ReactNode }) {
  const [calendar, setCalendar] = useState<TrainingCalendar>({})
  const [plan, setPlan] = useState<TrainingPlan | null>(null)

  const addWorkout = useCallback((iso: string, workout: Omit<Workout, 'id'>) => {
    setCalendar((prev) => {
      const day = prev[iso] ?? { workouts: [] }
      // Random suffix: several workouts can be added in the same millisecond (e.g. a whole plan at once).
      const newWorkout: Workout = { ...workout, id: `w-${Date.now()}-${Math.random().toString(36).slice(2, 8)}` }
      return { ...prev, [iso]: { workouts: [...day.workouts, newWorkout] } }
    })
  }, [])

  const setWorkoutStatus = useCallback((iso: string, workoutId: string, status: WorkoutStatus) => {
    setCalendar((prev) => {
      const day = prev[iso]
      if (!day) return prev
      return {
        ...prev,
        [iso]: { workouts: day.workouts.map((w) => (w.id === workoutId ? { ...w, status } : w)) },
      }
    })
  }, [])

  const value = useMemo(
    () => ({ calendar, addWorkout, setWorkoutStatus, plan, setPlan }),
    [calendar, addWorkout, setWorkoutStatus, plan],
  )

  return <TrainingContext.Provider value={value}>{children}</TrainingContext.Provider>
}

export function useTraining(): TrainingContextValue {
  const context = useContext(TrainingContext)
  if (!context) throw new Error('useTraining must be used inside TrainingProvider')
  return context
}
