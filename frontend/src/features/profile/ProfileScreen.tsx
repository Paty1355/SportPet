import { Pressable, StyleSheet, Text, View } from 'react-native'
import { Screen } from '../../components/Screen'
import { useAuth } from '../../lib/auth'
import { useTheme } from '../../lib/theme'

export function ProfileScreen() {
  const { colors } = useTheme()
  const { user, signOut } = useAuth()

  return (
    <Screen>
      <View style={[styles.card, { backgroundColor: colors.surface, borderColor: colors.border }]}>
        <Text style={[styles.name, { color: colors.text }]}>{user?.name || 'Athlete'}</Text>
        <Text style={[styles.email, { color: colors.muted }]}>{user?.email}</Text>

        <Pressable
          onPress={signOut}
          accessibilityRole="button"
          style={[styles.signOut, { borderColor: colors.border }]}
        >
          <Text style={[styles.signOutText, { color: colors.warn }]}>Log out</Text>
        </Pressable>
      </View>
    </Screen>
  )
}

const styles = StyleSheet.create({
  card: { borderRadius: 24, borderWidth: StyleSheet.hairlineWidth, padding: 20, gap: 6, marginTop: 24 },
  name: { fontSize: 20, fontWeight: '700' },
  email: { fontSize: 14 },
  signOut: { marginTop: 16, paddingVertical: 12, borderRadius: 12, borderWidth: 1, alignItems: 'center' },
  signOutText: { fontSize: 15, fontWeight: '700' },
})
