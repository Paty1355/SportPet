export interface ProposedExercise {
  title: string
  imageUrl: string
  description: string
  sets: number
  reps: number
  estimatedTimeMinutes: number
}

export interface QuestionOption {
  value: string
  label: string
}

export interface Question {
  key: string
  text: string
  options: QuestionOption[]
  multi: boolean
}

export interface QuestionnaireStatus {
  step: number
  total: number
  completed: boolean
  question: Question | null
}

export interface ChatReply {
  reply: string
  memories_used: string[]
  question: Question | null
  plan?: ProposedExercise[]
}
