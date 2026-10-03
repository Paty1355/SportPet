import type { ReactNode } from 'react'
import { ScrollView, StyleSheet, View } from 'react-native'

export function Screen({ children }: { children: ReactNode }) {
  return (
    <ScrollView contentContainerStyle={styles.scroll} keyboardShouldPersistTaps="handled">
      <View style={styles.inner}>{children}</View>
    </ScrollView>
  )
}

const styles = StyleSheet.create({
  scroll: { padding: 16, paddingBottom: 32 },
  inner: { width: '100%', maxWidth: 1100, alignSelf: 'center', gap: 16 },
})
