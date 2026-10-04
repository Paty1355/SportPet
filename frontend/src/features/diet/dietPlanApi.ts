import { ApiError, authGet, authRequest } from '../../lib/api'
import { SERVER_ORIGIN } from '../plan/planApi'

export interface DietMeal {
  name: string
  title: string
  description: string
  calories: number
  proteinGrams: number
  carbsGrams: number
  fatGrams: number
  prepTimeMinutes: number
  // Relative to the server root, e.g. "/static/meals/...". Empty when the dish has no photo.
  imageUrl: string
}

export interface DietDay {
  day: string
  meals: DietMeal[]
}

export interface DietPlan {
  dailyCalories: number
  days: DietDay[]
}

export function mealImageSource(imageUrl: string): string {
  return `${SERVER_ORIGIN}${imageUrl}`
}

export async function fetchDietPlan(token: string): Promise<DietPlan | null> {
  try {
    return await authGet<DietPlan>('/agents/diet-plan', token)
  } catch (caught) {
    if (caught instanceof ApiError && caught.status === 404) return null
    throw caught
  }
}

export function generateDietPlan(token: string) {
  return authRequest<DietPlan>('POST', '/agents/diet-plan', token)
}
