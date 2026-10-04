import { Ionicons } from '@expo/vector-icons'
import { StyleSheet, Text, View } from 'react-native'
import { useTheme } from '../lib/theme'

export function AiNotice({ text = 'AI assistant. It can make mistakes, so check important information.' }: { text?: string }) {
  const { colors } = useTheme()
  return (
    <View style={styles.row} accessibilityRole="text">
      <Ionicons name="sparkles-outline" size={13} color={colors.muted} />
      <Text style={[styles.text, { color: colors.muted }]}>{text}</Text>
    </View>
  )
}

const styles = StyleSheet.create({
  row: { flexDirection: 'row', alignItems: 'center', gap: 6, justifyContent: 'center', paddingVertical: 4 },
  text: { fontSize: 12, textAlign: 'center', flexShrink: 1 },
})
