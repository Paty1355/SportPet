import type { TrainingCalendar } from '../../lib/types'
import { DEFAULT_OWNED, type CosmeticItem } from './cosmetics'
import { findSpecies, SPECIES } from './species'
import type { FoodItem } from './shop'

export interface Equipped {
  hat: string | null
  background: string
  body: string
  decor: string[]
  theme: string
}

export interface PetState {
  name: string
  species: string
  xp: number
  fullness: number
  happiness: number
  coins: number
  inventory: Record<string, number>
  owned: string[]
  equipped: Equipped
  rewardedWorkoutIds: string[]
  updatedAt: number
}

export const XP_PER_LEVEL = 100

const XP_PER_WORKOUT = 25
const COINS_PER_WORKOUT = 10
const CARROTS_PER_WORKOUT = 1
const HAPPINESS_PER_PET = 5
const FULLNESS_DECAY_PER_HOUR = 2
const HAPPINESS_DECAY_PER_HOUR = 1

const clamp = (value: number) => Math.min(100, Math.max(0, value))

export function createPet(now: number): PetState {
  return {
    name: 'Bun',
    species: 'bunny',
    xp: 0,
    fullness: 80,
    happiness: 60,
    coins: 500,
    inventory: { carrot: 20 },
    owned: [...DEFAULT_OWNED],
    equipped: { hat: null, background: 'bg-plain', body: 'body-peach', decor: [], theme: 'theme-indigo' },
    rewardedWorkoutIds: [],
    updatedAt: now,
  }
}

export function normalizePet(stored: Partial<PetState>, now: number): PetState {
  const base = createPet(now)
  return {
    ...base,
    ...stored,
    inventory: { ...base.inventory, ...stored.inventory },
    owned: stored.owned ?? base.owned,
    equipped: { ...base.equipped, ...stored.equipped },
  }
}

export function ownedCount(pet: PetState, itemId: string): number {
  return pet.inventory[itemId] ?? 0
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
    coins: pet.coins + fresh.length * COINS_PER_WORKOUT,
    inventory: {
      ...pet.inventory,
      carrot: ownedCount(pet, 'carrot') + fresh.length * CARROTS_PER_WORKOUT,
    },
    rewardedWorkoutIds: [...pet.rewardedWorkoutIds, ...fresh],
  }
}

export function receiveAffection(pet: PetState): PetState {
  return { ...pet, happiness: clamp(pet.happiness + HAPPINESS_PER_PET) }
}

export function feed(pet: PetState, food: FoodItem): PetState {
  const count = ownedCount(pet, food.id)
  if (count === 0 || pet.fullness >= 100) return pet
  return {
    ...pet,
    inventory: { ...pet.inventory, [food.id]: count - 1 },
    fullness: clamp(pet.fullness + food.fullness),
    happiness: clamp(pet.happiness + food.happiness),
  }
}

export function buyFood(pet: PetState, food: FoodItem): PetState {
  if (pet.coins < food.price) return pet
  return {
    ...pet,
    coins: pet.coins - food.price,
    inventory: { ...pet.inventory, [food.id]: ownedCount(pet, food.id) + 1 },
  }
}

export function ownsCosmetic(pet: PetState, itemId: string): boolean {
  return pet.owned.includes(itemId)
}

export function buyCosmetic(pet: PetState, item: CosmeticItem): PetState {
  if (ownsCosmetic(pet, item.id) || pet.coins < item.price) return pet
  return { ...pet, coins: pet.coins - item.price, owned: [...pet.owned, item.id] }
}

export function equipCosmetic(pet: PetState, item: CosmeticItem): PetState {
  if (!ownsCosmetic(pet, item.id)) return pet
  if (item.kind === 'hat') {
    const hat = pet.equipped.hat === item.id ? null : item.id
    return { ...pet, equipped: { ...pet.equipped, hat } }
  }
  if (item.kind === 'background') {
    return { ...pet, equipped: { ...pet.equipped, background: item.id } }
  }
  if (item.kind === 'theme') {
    return { ...pet, equipped: { ...pet.equipped, theme: item.id } }
  }
  if (item.kind === 'species') {
    const species = item.id.replace('species-', '')
    const usesDefaultBody = SPECIES.some((s) => s.defaultBody === pet.equipped.body)
    return {
      ...pet,
      species,
      equipped: {
        ...pet.equipped,
        body: usesDefaultBody ? findSpecies(species).defaultBody : pet.equipped.body,
      },
    }
  }
  if (item.kind === 'decor') {
    const decor = pet.equipped.decor.includes(item.id)
      ? pet.equipped.decor.filter((id) => id !== item.id)
      : [...pet.equipped.decor, item.id]
    return { ...pet, equipped: { ...pet.equipped, decor } }
  }
  return { ...pet, equipped: { ...pet.equipped, body: item.id } }
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
