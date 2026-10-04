import { Ionicons } from '@expo/vector-icons'
import { useState } from 'react'
import { Modal, Pressable, StyleSheet, Text, View } from 'react-native'
import { useTheme } from '../lib/theme'

export function CoinBadge({ coins }: { coins: number }) {
  const { colors } = useTheme()
  const [infoVisible, setInfoVisible] = useState(false)

  return (
    <>
      <View style={[styles.chip, { backgroundColor: colors.warnSoft }]}>
        <Ionicons name="barbell" size={16} color={colors.warn} />
        <Text style={[styles.text, { color: colors.warn }]}>{coins}</Text>
        <Pressable
          onPress={() => setInfoVisible(true)}
          accessibilityRole="button"
          accessibilityLabel="Get more dumbbells"
          hitSlop={6}
          style={[styles.plus, { backgroundColor: colors.warn }]}
        >
          <Ionicons name="add" size={14} color="#ffffff" />
        </Pressable>
      </View>

      <Modal visible={infoVisible} transparent animationType="fade" onRequestClose={() => setInfoVisible(false)}>
        <Pressable style={styles.backdrop} onPress={() => setInfoVisible(false)}>
          <View style={[styles.popup, { backgroundColor: colors.surface, borderColor: colors.border }]}>
            <Ionicons name="barbell" size={28} color={colors.warn} />
            <Text style={[styles.popupText, { color: colors.text }]}>
              In the future you'll be able to buy more dumbbells here.
            </Text>
            <Pressable
              onPress={() => setInfoVisible(false)}
              accessibilityRole="button"
              style={[styles.close, { backgroundColor: colors.primary }]}
            >
              <Text style={styles.closeText}>Got it</Text>
            </Pressable>
          </View>
        </Pressable>
      </Modal>
    </>
  )
}

const styles = StyleSheet.create({
  chip: { flexDirection: 'row', alignItems: 'center', gap: 6, paddingLeft: 12, paddingRight: 4, paddingVertical: 4, borderRadius: 999 },
  text: { fontSize: 15, fontWeight: '700' },
  plus: { width: 22, height: 22, borderRadius: 11, alignItems: 'center', justifyContent: 'center' },
  backdrop: { flex: 1, backgroundColor: 'rgba(0,0,0,0.35)', alignItems: 'center', justifyContent: 'center', padding: 24 },
  popup: { width: '100%', maxWidth: 320, borderRadius: 20, borderWidth: StyleSheet.hairlineWidth, padding: 22, alignItems: 'center', gap: 12 },
  popupText: { fontSize: 15, textAlign: 'center', lineHeight: 22 },
  close: { marginTop: 4, paddingHorizontal: 22, paddingVertical: 10, borderRadius: 12 },
  closeText: { color: '#ffffff', fontSize: 15, fontWeight: '700' },
})
