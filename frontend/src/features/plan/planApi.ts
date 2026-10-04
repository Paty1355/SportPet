import { API_URL, ApiError, authGet, authRequest } from '../../lib/api'

export interface PlanExercise {
  title: string
  gifUrl: string
  description: string
  sets: number
  reps: number
  estimatedTimeMinutes: number
}

export interface PlanWorkout {
  day: string
  // Calendar date "YYYY-MM-DD" counted from the device's today. Null for plans saved before dates existed.
  date: string | null
  focus: string
  exercises: PlanExercise[]
}

export interface TrainingPlan {
  workouts: PlanWorkout[]
  recentFeedback: unknown[]
}

// Backend serves exercise gifs from the app root, not under /api/v1.
export const SERVER_ORIGIN = API_URL.replace(/\/api\/v1\/?$/, '')

export function gifSource(gifUrl: string): string {
  return `${SERVER_ORIGIN}${gifUrl}`
}

export async function fetchPlan(token: string): Promise<TrainingPlan | null> {
  try {
    return await authGet<TrainingPlan>('/agents/plan', token)
  } catch (caught) {
    if (caught instanceof ApiError && caught.status === 404) return null
    throw caught
  }
}

// `today` is the device's local date, so the backend dates the plan from the user's day, not the server's.
export function generatePlan(token: string, today: string) {
  return authRequest<TrainingPlan>('POST', `/agents/plan?today=${today}`, token)
}
