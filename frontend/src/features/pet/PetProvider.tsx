import AsyncStorage from '@react-native-async-storage/async-storage'
import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import { useTraining } from '../../lib/training'
import {
  applyDecay,
  createPet,
  doneWorkoutIds,
  feed as feedPet,
  receiveAffection,
  rewardWorkouts,
  type PetState,
} from './petLogic'

const STORAGE_KEY = 'pet-state-v3'
const DECAY_INTERVAL_MS = 60_000

interface PetContextValue {
  pet: PetState | null
  feed: () => void
  affection: () => void
}

const PetContext = createContext<PetContextValue | null>(null)

export function PetProvider({ children }: { children: ReactNode }) {
  const { calendar } = useTraining()
  const [pet, setPet] = useState<PetState | null>(null)

  useEffect(() => {
    let cancelled = false
    AsyncStorage.getItem(STORAGE_KEY)
      .then((raw) => {
        const stored: PetState | null = raw ? JSON.parse(raw) : null
        const now = Date.now()
        if (!cancelled) setPet(applyDecay(stored ?? createPet(now), now))
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
      feed: () => setPet((current) => (current ? feedPet(current) : current)),
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
