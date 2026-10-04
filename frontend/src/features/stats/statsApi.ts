import { authGet } from '../../lib/api'

export interface LatestValue {
  ts: string
  value: number
}

export interface Overview {
  user_id: number
  name: string | null
  sex: string | null
  age: number | null
  weight_kg: number | null
  height_cm: number | null
  bmi: number | null
  latest: {
    heart_rate: LatestValue | null
    spo2: LatestValue | null
    stress: LatestValue | null
  }
  daily: DailySummary[]
  blood_pressure: BloodPressure[]
}

export interface SeriesPoint {
  ts: string
  value: number
  min: number | null
  max: number | null
}

export interface Series {
  metric: string
  unit: string
  bucket: string
  points: SeriesPoint[]
}

export interface DailySummary {
  date: string
  steps: number | null
  sleep_minutes: number | null
}

export interface BloodPressure {
  ts: string
  systolic: number
  diastolic: number
}

// One call for the profile: profile, latest vitals, daily summaries and blood pressure of the last 60 days.
export function fetchDashboard(token: string) {
  return authGet<Overview>('/health/dashboard', token)
}

export function fetchHeartRateDay(token: string) {
  const end = new Date()
  const start = new Date(end.getTime() - 24 * 60 * 60 * 1000)
  return authGet<Series>('/health/series', token, {
    metric: 'heart_rate',
    bucket: '1h',
    start: start.toISOString(),
    end: end.toISOString(),
  })
}

