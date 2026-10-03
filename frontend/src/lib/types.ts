export type WorkoutStatus = 'planned' | 'done' | 'skipped'

export type WorkoutSource = 'agent' | 'user'

export interface Exercise {
  name: string
  sets: number
  reps: number
  weightKg: number | null
}

export interface Workout {
  id: string
  title: string
  startTime: string
  durationMin: number
  exercises: Exercise[]
  source: WorkoutSource
  status: WorkoutStatus
}

export interface DayPlan {
  workouts: Workout[]
}

// Klucz: data w formacie ISO "YYYY-MM-DD"
export type TrainingCalendar = Record<string, DayPlan>
