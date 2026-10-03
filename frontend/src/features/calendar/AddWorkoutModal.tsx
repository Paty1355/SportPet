import { useState } from 'react'
import { Modal, Pressable, StyleSheet, Text, TextInput, View } from 'react-native'
import type { Workout } from '../../lib/types'
import { useTheme } from '../../lib/theme'

interface AddWorkoutModalProps {
  visible: boolean
  onClose: () => void
  onSubmit: (workout: Omit<Workout, 'id'>) => void
}

export function AddWorkoutModal({ visible, onClose, onSubmit }: AddWorkoutModalProps) {
  const { colors } = useTheme()
  const [title, setTitle] = useState('')
  const [startTime, setStartTime] = useState('18:00')
  const [duration, setDuration] = useState('60')

  const inputStyle = [
    styles.input,
    { color: colors.text, borderColor: colors.border, backgroundColor: colors.bg },
  ]

  function submit() {
    const name = title.trim()
    if (!name) return
    onSubmit({
      title: name,
      startTime,
      durationMin: Number(duration) || 60,
      exercises: [],
      source: 'user',
      status: 'planned',
    })
    setTitle('')
    onClose()
  }

  return (
    <Modal visible={visible} transparent animationType="slide" onRequestClose={onClose}>
      <View style={styles.backdrop}>
        <Pressable style={StyleSheet.absoluteFill} onPress={onClose} accessibilityLabel="Close" />
        <View style={[styles.sheet, { backgroundColor: colors.surface }]}>
          <Text style={[styles.title, { color: colors.text }]}>New workout</Text>

          <Text style={[styles.label, { color: colors.muted }]}>Name</Text>
          <TextInput
            value={title}
            onChangeText={setTitle}
            placeholder="e.g. Legs"
            placeholderTextColor={colors.muted}
            style={inputStyle}
            autoFocus
          />

          <View style={styles.row}>
            <View style={styles.half}>
              <Text style={[styles.label, { color: colors.muted }]}>Time</Text>
              <TextInput
                value={startTime}
                onChangeText={setStartTime}
                placeholder="18:00"
                placeholderTextColor={colors.muted}
                style={inputStyle}
              />
            </View>
            <View style={styles.half}>
              <Text style={[styles.label, { color: colors.muted }]}>Duration (min)</Text>
              <TextInput
                value={duration}
                onChangeText={setDuration}
                keyboardType="number-pad"
                style={inputStyle}
              />
            </View>
          </View>

          <View style={styles.actions}>
            <Pressable onPress={onClose} style={styles.cancel} accessibilityRole="button">
              <Text style={{ color: colors.muted, fontWeight: '600' }}>Cancel</Text>
            </Pressable>
            <Pressable
              onPress={submit}
              accessibilityRole="button"
              style={[styles.save, { backgroundColor: colors.primary }]}
            >
              <Text style={styles.saveText}>Save</Text>
            </Pressable>
          </View>
        </View>
      </View>
    </Modal>
  )
}

const styles = StyleSheet.create({
  backdrop: { flex: 1, justifyContent: 'flex-end', alignItems: 'center', backgroundColor: 'rgba(0,0,0,0.4)' },
  sheet: {
    width: '100%',
    maxWidth: 480,
    borderTopLeftRadius: 24,
    borderTopRightRadius: 24,
    padding: 20,
    gap: 8,
  },
  title: { fontSize: 18, fontWeight: '700', marginBottom: 8 },
  label: { fontSize: 13, marginTop: 8, marginBottom: 4 },
  input: { borderWidth: 1, borderRadius: 12, paddingHorizontal: 12, paddingVertical: 10, fontSize: 15 },
  row: { flexDirection: 'row', gap: 12 },
  half: { flex: 1 },
  actions: { flexDirection: 'row', justifyContent: 'flex-end', alignItems: 'center', gap: 8, marginTop: 16 },
  cancel: { paddingHorizontal: 16, paddingVertical: 10 },
  save: { paddingHorizontal: 20, paddingVertical: 10, borderRadius: 12 },
  saveText: { color: '#ffffff', fontWeight: '700' },
})
