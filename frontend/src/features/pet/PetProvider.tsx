import AsyncStorage from '@react-native-async-storage/async-storage'
import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import { useAccentSync } from '../../lib/theme'
import { useTraining } from '../../lib/training'
import { findCosmetic, type CosmeticItem } from './cosmetics'
import {
  applyDecay,
  buyCosmetic as buyCosmeticItem,
  buyFood as buyFoodItem,
  createPet,
  doneWorkoutIds,
  equipCosmetic as equipCosmeticItem,
  feed as feedPet,
  normalizePet,
  receiveAffection,
  rewardWorkouts,
  type PetState,
} from './petLogic'
import type { FoodItem } from './shop'

const STORAGE_KEY = 'pet-state-v5'
const DECAY_INTERVAL_MS = 60_000

interface PetContextValue {
  pet: PetState | null
  feed: (food: FoodItem) => void
  buy: (food: FoodItem) => void
  buyCosmetic: (item: CosmeticItem) => void
  equipCosmetic: (item: CosmeticItem) => void
  affection: () => void
}

const PetContext = createContext<PetContextValue | null>(null)

export function PetProvider({ children }: { children: ReactNode }) {
  const { calendar } = useTraining()
  const [pet, setPet] = useState<PetState | null>(null)
  useAccentSync(pet ? (findCosmetic(pet.equipped.theme)?.palette?.[0] ?? null) : null)

  useEffect(() => {
    let cancelled = false
    AsyncStorage.getItem(STORAGE_KEY)
      .then((raw) => {
        const now = Date.now()
        const base = raw ? normalizePet(JSON.parse(raw), now) : createPet(now)
        if (!cancelled) setPet(applyDecay(base, now))
      })
      .catch(() => {
        if (!cancelled) setPet(createPet(Date.now()))
      })
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    const timer = setInterval(() => {
      setPet((current) => (current ? applyDecay(current, Date.now()) : current))
    }, DECAY_INTERVAL_MS)
    return () => clearInterval(timer)
  }, [])

  const doneIds = useMemo(() => doneWorkoutIds(calendar), [calendar])

  useEffect(() => {
    setPet((current) => (current ? rewardWorkouts(current, doneIds) : current))
  }, [doneIds])

  useEffect(() => {
    if (!pet) return
    AsyncStorage.setItem(STORAGE_KEY, JSON.stringify(pet)).catch(() => {})
  }, [pet])

  const value = useMemo<PetContextValue>(
    () => ({
      pet,
      feed: (food) => setPet((current) => (current ? feedPet(current, food) : current)),
      buy: (food) => setPet((current) => (current ? buyFoodItem(current, food) : current)),
      buyCosmetic: (item) => setPet((current) => (current ? buyCosmeticItem(current, item) : current)),
      equipCosmetic: (item) => setPet((current) => (current ? equipCosmeticItem(current, item) : current)),
      affection: () => setPet((current) => (current ? receiveAffection(current) : current)),
    }),
    [pet],
  )

  return <PetContext.Provider value={value}>{children}</PetContext.Provider>
}

export function usePet(): PetContextValue {
  const context = useContext(PetContext)
  if (!context) throw new Error('usePet must be used inside PetProvider')
  return context
}
