import { Ionicons } from '@expo/vector-icons'
import * as ImagePicker from 'expo-image-picker'
import { useState } from 'react'
import { ActivityIndicator, Image, Pressable, StyleSheet, Text, TextInput, View } from 'react-native'
import { Screen } from '../../components/Screen'
import { useAuth } from '../../lib/auth'
import { useTheme } from '../../lib/theme'
import { analyzePhoto, type PickedPhoto } from './photoApi'

const DEFAULT_QUESTION = 'Which machine is this and how should I train on it?'

export function MachinesScreen() {
  const { colors } = useTheme()
  const { token } = useAuth()
  const [photo, setPhoto] = useState<PickedPhoto | null>(null)
  const [question, setQuestion] = useState('')
  const [busy, setBusy] = useState(false)
  const [reply, setReply] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  function take(result: ImagePicker.ImagePickerResult) {
    if (result.canceled || result.assets.length === 0) return
    const asset = result.assets[0]
    setPhoto({ uri: asset.uri, mimeType: asset.mimeType, fileName: asset.fileName })
    setReply(null)
    setError(null)
  }

  async function fromCamera() {
    const permission = await ImagePicker.requestCameraPermissionsAsync()
    if (!permission.granted) {
      setError('Camera permission is needed to take a photo.')
      return
    }
    take(await ImagePicker.launchCameraAsync({ quality: 0.8 }))
  }

  async function fromGallery() {
    take(await ImagePicker.launchImageLibraryAsync({ mediaTypes: ['images'], quality: 0.8 }))
  }

  async function analyze() {
    if (!photo || !token || busy) return
    setBusy(true)
    setError(null)
    try {
      const result = await analyzePhoto(token, photo, question.trim() || DEFAULT_QUESTION)
      setReply(result.reply)
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Something went wrong')
    } finally {
      setBusy(false)
    }
  }

  return (
    <Screen>
      <View style={[styles.card, { backgroundColor: colors.surface, borderColor: colors.border }]}>
        <Text style={[styles.title, { color: colors.text }]}>Machine scanner</Text>
        <Text style={[styles.meta, { color: colors.muted }]}>
          Take a photo of a gym machine or pick one from your gallery. Bun will tell you what it is and how to use it.
        </Text>

        <View style={styles.buttons}>
          <Pressable onPress={fromCamera} accessibilityRole="button" style={[styles.button, { backgroundColor: colors.primary }]}>
            <Ionicons name="camera-outline" size={18} color="#ffffff" />
            <Text style={styles.buttonText}>Camera</Text>
          </Pressable>
          <Pressable
            onPress={fromGallery}
            accessibilityRole="button"
            style={[styles.button, { backgroundColor: colors.primarySoft }]}
          >
            <Ionicons name="images-outline" size={18} color={colors.primary} />
            <Text style={[styles.buttonText, { color: colors.primary }]}>Gallery</Text>
          </Pressable>
        </View>

        {photo && (
          <Image source={{ uri: photo.uri }} style={[styles.preview, { borderColor: colors.border }]} resizeMode="cover" />
        )}

        {photo && (
          <>
            <TextInput
              value={question}
              onChangeText={setQuestion}
              placeholder="Ask something (optional)"
              placeholderTextColor={colors.muted}
              style={[styles.input, { color: colors.text, borderColor: colors.border, backgroundColor: colors.bg }]}
            />
            <Pressable
              onPress={analyze}
              disabled={busy}
              accessibilityRole="button"
              style={[styles.analyze, { backgroundColor: busy ? colors.neutralSoft : colors.primary }]}
            >
              {busy ? (
                <ActivityIndicator color={colors.muted} />
              ) : (
                <Text style={styles.analyzeText}>Analyze photo</Text>
              )}
            </Pressable>
          </>
        )}

        {error && <Text style={[styles.meta, { color: colors.warn }]}>{error}</Text>}

        {reply && (
          <View style={[styles.reply, { backgroundColor: colors.bg, borderColor: colors.border }]}>
            <Text style={[styles.replyText, { color: colors.text }]}>{reply}</Text>
          </View>
        )}
      </View>
    </Screen>
  )
}

const styles = StyleSheet.create({
  card: { borderRadius: 24, borderWidth: StyleSheet.hairlineWidth, padding: 18, gap: 12, marginTop: 8 },
  title: { fontSize: 18, fontWeight: '700' },
  meta: { fontSize: 13, lineHeight: 19 },
  buttons: { flexDirection: 'row', gap: 10 },
  button: { flex: 1, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 8, paddingVertical: 12, borderRadius: 14 },
  buttonText: { color: '#ffffff', fontSize: 15, fontWeight: '700' },
  preview: { width: '100%', height: 220, borderRadius: 18, borderWidth: StyleSheet.hairlineWidth },
  input: { borderWidth: 1, borderRadius: 12, paddingHorizontal: 12, paddingVertical: 10, fontSize: 15 },
  analyze: { paddingVertical: 14, borderRadius: 14, alignItems: 'center' },
  analyzeText: { color: '#ffffff', fontSize: 15, fontWeight: '700' },
  reply: { borderRadius: 16, borderWidth: StyleSheet.hairlineWidth, padding: 14 },
  replyText: { fontSize: 15, lineHeight: 22 },
})
