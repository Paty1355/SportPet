import { Ionicons } from '@expo/vector-icons'
import { StyleSheet, Text, View } from 'react-native'
import { useTheme } from '../lib/theme'
import type { IconName } from '../lib/navItems'
import { Screen } from './Screen'

interface ComingSoonProps {
  title: string
  description: string
  icon: IconName
}

export function ComingSoon({ title, description, icon }: ComingSoonProps) {
  const { colors } = useTheme()

  return (
    <Screen>
      <View style={[styles.card, { backgroundColor: colors.surface, borderColor: colors.border }]}>
        <View style={[styles.iconWrap, { backgroundColor: colors.primarySoft }]}>
          <Ionicons name={icon} size={32} color={colors.primary} />
        </View>
        <Text style={[styles.title, { color: colors.text }]}>{title}</Text>
        <Text style={[styles.description, { color: colors.muted }]}>{description}</Text>
        <View style={[styles.badge, { backgroundColor: colors.warnSoft }]}>
          <Text style={[styles.badgeText, { color: colors.warn }]}>Coming soon</Text>
        </View>
      </View>
    </Screen>
  )
}

const styles = StyleSheet.create({
  card: {
    alignItems: 'center',
    padding: 32,
    borderRadius: 24,
    borderWidth: 1,
    borderStyle: 'dashed',
    marginTop: 24,
  },
  iconWrap: { padding: 16, borderRadius: 16, marginBottom: 20 },
  title: { fontSize: 20, fontWeight: '700' },
  description: { fontSize: 14, textAlign: 'center', marginTop: 8, maxWidth: 360 },
  badge: { marginTop: 24, paddingHorizontal: 12, paddingVertical: 4, borderRadius: 999 },
  badgeText: { fontSize: 12, fontWeight: '600' },
})
