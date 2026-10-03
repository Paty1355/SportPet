import { Ionicons } from '@expo/vector-icons'
import { Pressable, Text } from 'react-native'
import { useTheme } from '../lib/theme'

export function ThemeToggle({ showLabel = false }: { showLabel?: boolean }) {
  const { theme, colors, toggle } = useTheme()
  const isDark = theme === 'dark'

  return (
    <Pressable
      onPress={toggle}
      accessibilityRole="button"
      accessibilityLabel={isDark ? 'Switch to light theme' : 'Switch to dark theme'}
      style={{ flexDirection: 'row', alignItems: 'center', gap: 8, padding: 8, borderRadius: 12 }}
    >
      <Ionicons name={isDark ? 'sunny-outline' : 'moon-outline'} size={18} color={colors.muted} />
      {showLabel && (
        <Text style={{ color: colors.muted, fontSize: 14 }}>{isDark ? 'Light theme' : 'Dark theme'}</Text>
      )}
    </Pressable>
  )
}
