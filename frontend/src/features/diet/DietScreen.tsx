import { useState } from 'react'
import { Pressable, StyleSheet, Text, View } from 'react-native'
import { useTheme } from '../../lib/theme'
import { TrainingChatScreen } from '../training/TrainingChatScreen'
import { DietPlanScreen } from './DietPlanScreen'

type DietView = 'chat' | 'plan'

const VIEWS: { id: DietView; label: string }[] = [
  { id: 'chat', label: 'Chat' },
  { id: 'plan', label: 'Plan' },
]

// The dietitian chat (questionnaire first, then free chat) and the weekly meal plan.
export function DietScreen() {
  const { colors } = useTheme()
  const [view, setView] = useState<DietView>('chat')

  return (
    <View style={styles.root}>
      <View style={styles.switcher}>
        {VIEWS.map((item) => {
          const active = item.id === view
          return (
            <Pressable
              key={item.id}
              onPress={() => setView(item.id)}
              accessibilityRole="tab"
              accessibilityState={{ selected: active }}
              style={[
                styles.pill,
                { backgroundColor: active ? colors.primary : colors.surface, borderColor: colors.border },
              ]}
            >
              <Text style={[styles.pillText, { color: active ? '#ffffff' : colors.text }]}>{item.label}</Text>
            </Pressable>
          )
        })}
      </View>
      <View style={styles.content}>
        {view === 'chat' ? <TrainingChatScreen agent="diet" /> : <DietPlanScreen />}
      </View>
    </View>
  )
}

const styles = StyleSheet.create({
  root: { flex: 1, gap: 10 },
  switcher: { flexDirection: 'row', gap: 8, paddingHorizontal: 16, width: '100%', maxWidth: 800, alignSelf: 'center' },
  pill: { flex: 1, paddingVertical: 8, borderRadius: 999, borderWidth: StyleSheet.hairlineWidth, alignItems: 'center' },
  pillText: { fontSize: 13, fontWeight: '700' },
  content: { flex: 1 },
})
