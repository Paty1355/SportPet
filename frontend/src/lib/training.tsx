import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from 'react'
import { mockCalendar } from '../mocks/calendar'
import type { TrainingCalendar, Workout, WorkoutStatus } from './types'

interface TrainingContextValue {
  calendar: TrainingCalendar
  addWorkout: (iso: string, workout: Omit<Workout, 'id'>) => void
  setWorkoutStatus: (iso: string, workoutId: string, status: WorkoutStatus) => void
}

const TrainingContext = createContext<TrainingContextValue | null>(null)

export function TrainingProvider({ children }: { children: ReactNode }) {
  const [calendar, setCalendar] = useState<TrainingCalendar>(mockCalendar)

  const addWorkout = useCallback((iso: string, workout: Omit<Workout, 'id'>) => {
    setCalendar((prev) => {
      const day = prev[iso] ?? { workouts: [] }
      const newWorkout: Workout = { ...workout, id: `w-${Date.now()}` }
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
    () => ({ calendar, addWorkout, setWorkoutStatus }),
    [calendar, addWorkout, setWorkoutStatus],
  )

  return <TrainingContext.Provider value={value}>{children}</TrainingContext.Provider>
}

export function useTraining(): TrainingContextValue {
  const context = useContext(TrainingContext)
  if (!context) throw new Error('useTraining must be used inside TrainingProvider')
  return context
}
