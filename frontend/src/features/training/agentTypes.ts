export interface ProposedExercise {
  title: string
  imageUrl: string
  description: string
  sets: number
  reps: number
  estimatedTimeMinutes: number
}

export type AgentReply =
  | { type: 'message'; text: string }
  | { type: 'plan'; exercises: ProposedExercise[] }
