import { Ionicons } from '@expo/vector-icons'
import { useState } from 'react'
import { Image, Modal, Pressable, StyleSheet, Text, View, type ImageStyle, type StyleProp } from 'react-native'
import { useTheme } from '../lib/theme'

interface LightboxProps {
  uri: string
  style: StyleProp<ImageStyle>
  caption?: string
}

// Shows a picture as a thumbnail; tapping it opens the full-size view. Works for animated GIFs too.
export function Lightbox({ uri, style, caption }: LightboxProps) {
  const [open, setOpen] = useState(false)
  const { colors } = useTheme()

  return (
    <>
      <Pressable onPress={() => setOpen(true)} accessibilityRole="imagebutton" accessibilityLabel={caption ?? 'Enlarge picture'}>
        <Image source={{ uri }} style={style} resizeMode="cover" />
      </Pressable>

      <Modal visible={open} transparent animationType="fade" onRequestClose={() => setOpen(false)}>
        <View style={styles.backdrop}>
          <Pressable style={StyleSheet.absoluteFill} onPress={() => setOpen(false)} accessibilityLabel="Close" />
          <Pressable onPress={() => setOpen(false)} accessibilityRole="button" accessibilityLabel="Close" style={styles.close}>
            <Ionicons name="close" size={26} color="#ffffff" />
          </Pressable>
          <Image source={{ uri }} style={styles.full} resizeMode="contain" />
          {caption ? <Text style={[styles.caption, { color: colors.surface }]}>{caption}</Text> : null}
        </View>
      </Modal>
    </>
  )
}

const styles = StyleSheet.create({
  backdrop: { flex: 1, backgroundColor: 'rgba(0,0,0,0.9)', alignItems: 'center', justifyContent: 'center', padding: 16 },
  close: { position: 'absolute', top: 48, right: 20, zIndex: 2, padding: 8 },
  full: { width: '100%', height: '75%' },
  caption: { marginTop: 12, fontSize: 15, fontWeight: '600', textAlign: 'center' },
})
