import { authPost, authRequest } from '../../lib/api'
import type { TrainingPlan } from '../plan/planApi'

export interface QuestionOption {
  value: string
  label: string
}

export interface CheckInQuestion {
  key: string
  text: string
  type: 'scale' | 'choice' | 'text'
  options: QuestionOption[]
  minValue: number | null
  maxValue: number | null
  skippable: boolean
}

export interface SafetyNotice {
  level: 'consultation' | 'urgent'
  codes: string[]
  message: string
}

export interface Support {
  status: 'pending' | 'available' | 'unavailable'
  message: string
  observations: string[]
  startedAt: string | null
}

export interface CheckIn {
  sessionId: string
  version: number
  status: 'in_progress' | 'awaiting_confirmation' | 'completed' | 'interrupted'
  step: number
  total: number
  reply: string
  question: CheckInQuestion | null
  notice: SafetyNotice | null
  support: Support | null
  reportId: string | null
}

export interface WorkoutDone {
  plan: TrainingPlan
  checkIn: CheckIn
}

export type ChatAction = 'answer' | 'skip' | 'confirm' | 'retry_support'

// Marks the plan's workout on this date as done. The backend removes it from the plan and opens a check-in.
export function markWorkoutDone(token: string, isoDate: string) {
  return authRequest<WorkoutDone>('POST', `/agents/plan/workouts/${isoDate}/done`, token)
}

export function sendChatTurn(
  token: string,
  sessionId: string,
  expectedVersion: number,
  action: ChatAction,
  message?: string,
) {
  return authPost<CheckIn>(`/agents/post-workout/sessions/${sessionId}/chat`, token, {
    requestId: newRequestId(),
    expectedVersion,
    action,
    ...(message !== undefined ? { message } : {}),
  })
}

// The backend requires a UUID per request so retries are idempotent.
function newRequestId(): string {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (char) => {
    const random = (Math.random() * 16) | 0
    const value = char === 'x' ? random : (random & 0x3) | 0x8
    return value.toString(16)
  })
}
