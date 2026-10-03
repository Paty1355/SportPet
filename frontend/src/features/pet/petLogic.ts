import type { TrainingCalendar } from '../../lib/types'

export interface PetState {
  name: string
  xp: number
  fullness: number
  happiness: number
  carrots: number
  rewardedWorkoutIds: string[]
  updatedAt: number
}

export const XP_PER_LEVEL = 100

const XP_PER_WORKOUT = 25
const CARROTS_PER_WORKOUT = 1
const FULLNESS_PER_CARROT = 10
const HAPPINESS_PER_CARROT = 10
const HAPPINESS_PER_PET = 5
const FULLNESS_DECAY_PER_HOUR = 2
const HAPPINESS_DECAY_PER_HOUR = 1

const clamp = (value: number) => Math.min(100, Math.max(0, value))

export function createPet(now: number): PetState {
  return {
    name: 'Bun',
    xp: 0,
    fullness: 80,
    happiness: 60,
    carrots: 20,
    rewardedWorkoutIds: [],
    updatedAt: now,
  }
}

export function applyDecay(pet: PetState, now: number): PetState {
  const hours = Math.max(0, (now - pet.updatedAt) / 3_600_000)
  return {
    ...pet,
    fullness: clamp(pet.fullness - hours * FULLNESS_DECAY_PER_HOUR),
    happiness: clamp(pet.happiness - hours * HAPPINESS_DECAY_PER_HOUR),
    updatedAt: now,
  }
}

export function doneWorkoutIds(calendar: TrainingCalendar): string[] {
  return Object.values(calendar).flatMap((day) =>
    day.workouts.filter((w) => w.status === 'done').map((w) => w.id),
  )
}

export function rewardWorkouts(pet: PetState, workoutIds: string[]): PetState {
  const fresh = workoutIds.filter((id) => !pet.rewardedWorkoutIds.includes(id))
  if (fresh.length === 0) return pet
  return {
    ...pet,
    xp: pet.xp + fresh.length * XP_PER_WORKOUT,
    carrots: pet.carrots + fresh.length * CARROTS_PER_WORKOUT,
    rewardedWorkoutIds: [...pet.rewardedWorkoutIds, ...fresh],
  }
}

export function feed(pet: PetState): PetState {
  if (pet.carrots === 0 || pet.fullness >= 100) return pet
  return {
    ...pet,
    carrots: pet.carrots - 1,
    fullness: clamp(pet.fullness + FULLNESS_PER_CARROT),
    happiness: clamp(pet.happiness + HAPPINESS_PER_CARROT),
  }
}

export function receiveAffection(pet: PetState): PetState {
  return { ...pet, happiness: clamp(pet.happiness + HAPPINESS_PER_PET) }
}

export function levelOf(xp: number): number {
  return Math.floor(xp / XP_PER_LEVEL) + 1
}

export type PetMood = 'hungry' | 'sad' | 'content' | 'happy'

export function moodOf(pet: PetState): PetMood {
  if (pet.fullness < 30) return 'hungry'
  if (pet.happiness < 30) return 'sad'
  if (pet.happiness >= 70 && pet.fullness >= 60) return 'happy'
  return 'content'
}
