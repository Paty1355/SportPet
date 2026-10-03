import { Ionicons } from '@expo/vector-icons'
import { StyleSheet, Text, View } from 'react-native'
import { useTheme } from '../lib/theme'
import type { NavItem } from '../lib/navItems'

interface NavItemContentProps {
  item: NavItem
  active: boolean
  wide: boolean
}

export function NavItemContent({ item, active, wide }: NavItemContentProps) {
  const { colors } = useTheme()

  if (item.primary && !wide) {
    return (
      <View
        style={[
          styles.fab,
          { backgroundColor: colors.primary, shadowColor: colors.primary },
          active && { borderWidth: 4, borderColor: colors.primarySoft },
        ]}
      >
        <Ionicons name={item.icon} size={26} color="#ffffff" />
      </View>
    )
  }

  const selectedOnWide = wide && active
  const tint = selectedOnWide ? '#ffffff' : active ? colors.primary : colors.muted

  return (
    <View
      style={[
        styles.item,
        wide && styles.itemWide,
        selectedOnWide && { backgroundColor: colors.primary },
      ]}
    >
      <Ionicons name={item.icon} size={wide ? 18 : 22} color={tint} />
      <Text style={[styles.label, wide && styles.labelWide, { color: tint }]}>{item.label}</Text>
    </View>
  )
}

const styles = StyleSheet.create({
  fab: {
    width: 56,
    height: 56,
    borderRadius: 28,
    marginTop: -24,
    alignItems: 'center',
    justifyContent: 'center',
    shadowOpacity: 0.4,
    shadowRadius: 10,
    shadowOffset: { width: 0, height: 4 },
    elevation: 6,
  },
  item: {
    alignItems: 'center',
    gap: 2,
    paddingVertical: 10,
  },
  itemWide: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    paddingVertical: 10,
    paddingHorizontal: 12,
    borderRadius: 12,
  },
  label: { fontSize: 11, fontWeight: '600' },
  labelWide: { fontSize: 14 },
})
