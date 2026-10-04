import { useEffect, useState } from 'react'
import { Pressable, StyleSheet, Text, View } from 'react-native'
import { useAuth } from '../../lib/auth'
import { useTheme } from '../../lib/theme'
import { DietScreen } from '../diet/DietScreen'
import { MachinesScreen } from '../machines/MachinesScreen'
import { PlanScreen } from '../plan/PlanScreen'
import { fetchQuestionnaire } from '../training/agentApi'
import { TrainingChatScreen } from '../training/TrainingChatScreen'

type Agent = 'training' | 'plan' | 'machines' | 'diet'

const AGENTS: { id: Agent; label: string }[] = [
  { id: 'training', label: 'Training' },
  { id: 'plan', label: 'Plan' },
  { id: 'machines', label: 'Machines' },
  { id: 'diet', label: 'Diet' },
]

export function AgentsScreen() {
  const { colors } = useTheme()
  const { token } = useAuth()
  const [agent, setAgent] = useState<Agent>('training')
  // Training is only needed until the questionnaire is done; after that its tab is hidden.
  const [questionnaireDone, setQuestionnaireDone] = useState(false)

  function refreshQuestionnaire() {
    if (!token) return
    fetchQuestionnaire(token)
      .then((status) => setQuestionnaireDone(status.completed))
      .catch(() => {})
  }

  useEffect(() => {
    refreshQuestionnaire()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token])

  useEffect(() => {
    if (questionnaireDone && agent === 'training') setAgent('plan')
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [questionnaireDone])

  function select(id: Agent) {
    setAgent(id)
    refreshQuestionnaire()
  }

  const visible = AGENTS.filter((item) => !(item.id === 'training' && questionnaireDone))

  return (
    <View style={styles.root}>
      <View style={styles.switcher}>
        {visible.map((item) => {
          const active = item.id === agent
          return (
            <Pressable
              key={item.id}
              onPress={() => select(item.id)}
              accessibilityRole="tab"
              accessibilityState={{ selected: active }}
              style={[
                styles.segment,
                { backgroundColor: active ? colors.primary : colors.surface, borderColor: colors.border },
              ]}
            >
              <Text style={[styles.segmentText, { color: active ? '#ffffff' : colors.text }]}>{item.label}</Text>
            </Pressable>
          )
        })}
      </View>

      <View style={styles.content}>
        {agent === 'training' && <TrainingChatScreen />}
        {agent === 'plan' && <PlanScreen />}
        {agent === 'machines' && <MachinesScreen />}
        {agent === 'diet' && <DietScreen />}
      </View>
    </View>
  )
}

const styles = StyleSheet.create({
  root: { flex: 1, paddingTop: 12, gap: 12 },
  switcher: { flexDirection: 'row', gap: 8, paddingHorizontal: 16, width: '100%', maxWidth: 800, alignSelf: 'center' },
  segment: { flex: 1, paddingVertical: 9, borderRadius: 999, borderWidth: StyleSheet.hairlineWidth, alignItems: 'center' },
  segmentText: { fontSize: 13, fontWeight: '700' },
  content: { flex: 1 },
})
