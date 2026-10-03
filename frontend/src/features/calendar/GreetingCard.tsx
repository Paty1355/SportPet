import { StyleSheet, Text, View } from 'react-native'
import { BunAvatar } from '../training/BunAvatar'
import { useTheme } from '../../lib/theme'

const ACCENT = '#8b5cf6'

function timeGreeting(date: Date): string {
  const hour = date.getHours()
  if (hour < 12) return 'Good morning'
  if (hour < 18) return 'Good afternoon'
  return 'Good evening'
}

export function GreetingCard({ now, planned, done }: { now: Date; planned: number; done: number }) {
  const { colors } = useTheme()

  let subtitle = 'No workout today. Want to plan one?'
  if (planned > 0) {
    subtitle = `You have ${planned} workout${planned > 1 ? 's' : ''} planned today.`
  } else if (done > 0) {
    subtitle = 'All done for today. Nice work!'
  }

  return (
    <View style={[styles.card, { backgroundColor: `${ACCENT}1F`, borderColor: `${ACCENT}33` }]}>
      <BunAvatar />
      <View style={styles.text}>
        <Text style={[styles.title, { color: colors.text }]}>{timeGreeting(now)}!</Text>
        <Text style={[styles.subtitle, { color: colors.muted }]}>{subtitle}</Text>
      </View>
    </View>
  )
}

const styles = StyleSheet.create({
  card: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 14,
    padding: 16,
    borderRadius: 24,
    borderWidth: StyleSheet.hairlineWidth,
  },
  text: { flex: 1, gap: 2 },
  title: { fontSize: 18, fontWeight: '700' },
  subtitle: { fontSize: 14 },
})
