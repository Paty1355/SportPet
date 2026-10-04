import { Ionicons } from '@expo/vector-icons'
import * as ImagePicker from 'expo-image-picker'
import { useState, type ReactNode } from 'react'
import { ActivityIndicator, Image, Pressable, StyleSheet, Text, View } from 'react-native'
import { AiNotice } from '../../components/AiNotice'
import { Screen } from '../../components/Screen'
import { useTheme } from '../../lib/theme'
import { BodyMap } from '../muscles/BodyMap'
import { labelOf } from '../muscles/muscleRegions'
import { analyzeMachine, type PickedPhoto, type VisionResponse } from './photoApi'

export function MachinesScreen() {
  const { colors } = useTheme()
  const [photo, setPhoto] = useState<PickedPhoto | null>(null)
  const [busy, setBusy] = useState(false)
  const [result, setResult] = useState<VisionResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  function take(picked: ImagePicker.ImagePickerResult) {
    if (picked.canceled || picked.assets.length === 0) return
    const asset = picked.assets[0]
    setPhoto({ uri: asset.uri, mimeType: asset.mimeType, fileName: asset.fileName })
    setResult(null)
    setError(null)
  }

  async function fromCamera() {
    const permission = await ImagePicker.requestCameraPermissionsAsync()
    if (!permission.granted) {
      setError('Camera permission is needed to take a photo.')
      return
    }
    // The backend scales photos to 2048 px anyway; lower quality keeps full-resolution phone shots under the 10 MB limit.
    take(await ImagePicker.launchCameraAsync({ quality: 0.5 }))
  }

  async function fromGallery() {
    take(await ImagePicker.launchImageLibraryAsync({ mediaTypes: ['images'], quality: 0.5 }))
  }

  async function analyze() {
    if (!photo || busy) return
    setBusy(true)
    setError(null)
    setResult(null)
    try {
      setResult(await analyzeMachine(photo))
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
          Take a photo of a gym machine or pick one from your gallery. We'll show how to use it.
        </Text>
        <AiNotice text="AI-generated guidance. It can make mistakes, so follow the machine's own instructions too." />

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
          <Pressable
            onPress={analyze}
            disabled={busy}
            accessibilityRole="button"
            style={[styles.analyze, { backgroundColor: busy ? colors.neutralSoft : colors.primary }]}
          >
            {busy ? <ActivityIndicator color={colors.muted} /> : <Text style={styles.analyzeText}>Analyze machine</Text>}
          </Pressable>
        )}

        {error && <Text style={[styles.meta, { color: colors.warn }]}>{error}</Text>}
      </View>

      {result && <MachineResult result={result} />}
    </Screen>
  )
}

function MachineResult({ result }: { result: VisionResponse }) {
  const { colors } = useTheme()
  return (
    <View style={[styles.card, { backgroundColor: colors.surface, borderColor: colors.border }]}>
      <Text style={[styles.title, { color: colors.text }]}>{result.machine_name}</Text>
      <Text style={[styles.meta, { color: colors.muted }]}>{result.category}</Text>
      <Text style={[styles.body, { color: colors.text }]}>{result.description}</Text>

      <Section title="Primary muscles">
        <Chips items={result.primary_muscles.map(labelOf)} />
      </Section>
      <Section title="Secondary muscles">
        <Chips items={result.secondary_muscles.map(labelOf)} />
      </Section>
      <Section title="Body map">
        <BodyMap primary={result.primary_muscles} secondary={result.secondary_muscles} />
      </Section>
      <Section title="Setup">
        <Steps items={result.setup_steps} />
      </Section>
      <Section title="How to exercise">
        <Steps items={result.exercise_steps} />
      </Section>
      <Section title="Tips">
        <Bullets items={result.tips} />
      </Section>

      <Text style={[styles.sources, { color: colors.muted }]}>Sources: {result.sources.join(', ')}</Text>
    </View>
  )
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  const { colors } = useTheme()
  return (
    <View style={styles.section}>
      <Text style={[styles.sectionTitle, { color: colors.primary }]}>{title}</Text>
      {children}
    </View>
  )
}

function Chips({ items }: { items: string[] }) {
  const { colors } = useTheme()
  return (
    <View style={styles.chips}>
      {items.map((item) => (
        <View key={item} style={[styles.chip, { backgroundColor: colors.primarySoft }]}>
          <Text style={[styles.chipText, { color: colors.primary }]}>{item}</Text>
        </View>
      ))}
    </View>
  )
}

function Steps({ items }: { items: string[] }) {
  const { colors } = useTheme()
  return (
    <View style={styles.list}>
      {items.map((item, index) => (
        <View key={item} style={styles.listRow}>
          <Text style={[styles.listMarker, { color: colors.primary }]}>{index + 1}.</Text>
          <Text style={[styles.body, { color: colors.text, flex: 1 }]}>{item}</Text>
        </View>
      ))}
    </View>
  )
}

function Bullets({ items }: { items: string[] }) {
  const { colors } = useTheme()
  return (
    <View style={styles.list}>
      {items.map((item) => (
        <View key={item} style={styles.listRow}>
          <Text style={[styles.listMarker, { color: colors.primary }]}>•</Text>
          <Text style={[styles.body, { color: colors.text, flex: 1 }]}>{item}</Text>
        </View>
      ))}
    </View>
  )
}

const styles = StyleSheet.create({
  card: { borderRadius: 24, borderWidth: StyleSheet.hairlineWidth, padding: 18, gap: 12, marginTop: 8 },
  title: { fontSize: 18, fontWeight: '700' },
  meta: { fontSize: 13, lineHeight: 19 },
  body: { fontSize: 15, lineHeight: 22 },
  buttons: { flexDirection: 'row', gap: 10 },
  button: { flex: 1, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 8, paddingVertical: 12, borderRadius: 14 },
  buttonText: { color: '#ffffff', fontSize: 15, fontWeight: '700' },
  preview: { width: '100%', height: 220, borderRadius: 18, borderWidth: StyleSheet.hairlineWidth },
  analyze: { paddingVertical: 14, borderRadius: 14, alignItems: 'center' },
  analyzeText: { color: '#ffffff', fontSize: 15, fontWeight: '700' },
  section: { gap: 6 },
  sectionTitle: { fontSize: 14, fontWeight: '700' },
  chips: { flexDirection: 'row', flexWrap: 'wrap', gap: 6 },
  chip: { paddingHorizontal: 10, paddingVertical: 4, borderRadius: 999 },
  chipText: { fontSize: 13, fontWeight: '600' },
  list: { gap: 6 },
  listRow: { flexDirection: 'row', gap: 8 },
  listMarker: { fontSize: 15, fontWeight: '700', minWidth: 18 },
  sources: { fontSize: 12, marginTop: 4 },
})
