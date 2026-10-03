import type { TrainingCalendar } from '../lib/types'
import { toISODate } from '../lib/dates'

const today = new Date()

function dayOffset(offset: number): string {
  const d = new Date(today.getFullYear(), today.getMonth(), today.getDate() + offset)
  return toISODate(d)
}

export const mockCalendar: TrainingCalendar = {
  [dayOffset(-2)]: {
    workouts: [
      {
        id: 'w-001',
        title: 'Back and biceps',
        startTime: '18:00',
        durationMin: 60,
        exercises: [
          { name: 'Pull-ups', sets: 4, reps: 8, weightKg: null },
          { name: 'Dumbbell rows', sets: 3, reps: 10, weightKg: 20 },
        ],
        source: 'agent',
        status: 'done',
      },
    ],
  },
  [dayOffset(1)]: {
    workouts: [
      {
        id: 'w-002',
        title: 'Legs',
        startTime: '17:30',
        durationMin: 75,
        exercises: [
          { name: 'Barbell squat', sets: 4, reps: 6, weightKg: 60 },
          { name: 'Lunges', sets: 3, reps: 12, weightKg: null },
        ],
        source: 'agent',
        status: 'planned',
      },
    ],
  },
  [dayOffset(4)]: {
    workouts: [
      {
        id: 'w-003',
        title: 'Chest and triceps',
        startTime: '19:00',
        durationMin: 50,
        exercises: [{ name: 'Bench press', sets: 4, reps: 8, weightKg: 70 }],
        source: 'user',
        status: 'planned',
      },
    ],
  },
}
