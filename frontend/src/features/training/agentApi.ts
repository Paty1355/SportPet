// Placeholder until the training agent endpoint is available.
import type { AgentReply } from './agentTypes'

let mockTurns = 0

export async function askTrainingAgent(message: string): Promise<AgentReply> {
  await new Promise((resolve) => setTimeout(resolve, 700))
  mockTurns += 1

  if (mockTurns === 1) {
    return { type: 'message', text: `Thanks, "${message}". What is your main goal?` }
  }
  if (mockTurns === 2) {
    return { type: 'message', text: 'How many days a week can you train, and for how long?' }
  }

  mockTurns = 0
  return {
    type: 'plan',
    exercises: [
      {
        title: 'Goblet Squat',
        imageUrl: 'https://example.com/img/goblet-squat.jpg',
        description:
          'Hold the weight close to your chest, keep your back straight, and squat down until your thighs are parallel to the floor.',
        sets: 3,
        reps: 12,
        estimatedTimeMinutes: 5,
      },
      {
        title: 'Glute Bridge',
        imageUrl: 'https://example.com/img/glute-bridge.jpg',
        description:
          'Lie on your back with knees bent. Push through your heels to raise your hips and squeeze your glutes at the top.',
        sets: 3,
        reps: 15,
        estimatedTimeMinutes: 4,
      },
    ],
  }
}
