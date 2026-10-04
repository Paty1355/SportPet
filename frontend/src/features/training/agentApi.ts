import { authGet, authPost } from '../../lib/api'
import type { ChatReply, QuestionnaireStatus } from './agentTypes'

// Training and diet agents share the same questionnaire and chat contract, only the path differs.
export type AgentKind = 'training' | 'diet'

const BASE_PATH: Record<AgentKind, string> = {
  training: '/agents/training',
  diet: '/agents/diet',
}

export function fetchQuestionnaire(token: string, agent: AgentKind = 'training') {
  return authGet<QuestionnaireStatus>(`${BASE_PATH[agent]}/questionnaire`, token)
}

export function askAgent(token: string, agent: AgentKind, message: string) {
  return authPost<ChatReply>(`${BASE_PATH[agent]}/chat`, token, { message })
}
