import { useState, type ReactNode } from 'react'
import { ActivityIndicator, Modal, Pressable, StyleSheet, Text, TextInput, View } from 'react-native'
import { ApiError } from '../../lib/api'
import { useTheme } from '../../lib/theme'
import { sendChatTurn, type CheckIn, type CheckInQuestion, type ChatAction } from './checkInApi'

interface CheckInModalProps {
  token: string
  initial: CheckIn
  // completed: the check-in was confirmed, so the backend may have built a new plan.
  onClose: (completed: boolean) => void
}

export function CheckInModal({ token, initial, onClose }: CheckInModalProps) {
  const { colors } = useTheme()
  const [checkIn, setCheckIn] = useState<CheckIn>(initial)
  const [text, setText] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function send(action: ChatAction, message?: string) {
    setBusy(true)
    setError(null)
    try {
      setCheckIn(await sendChatTurn(token, checkIn.sessionId, checkIn.version, action, message))
      setText('')
    } catch (caught) {
      setError(caught instanceof ApiError || caught instanceof Error ? caught.message : 'Something went wrong')
    } finally {
      setBusy(false)
    }
  }

  const finished = checkIn.status === 'completed'
  const question = checkIn.question

  return (
    <Modal visible transparent animationType="slide" onRequestClose={() => onClose(finished)}>
      <View style={styles.backdrop}>
        <Pressable style={StyleSheet.absoluteFill} onPress={() => onClose(finished)} accessibilityLabel="Close" />
        <View style={[styles.sheet, { backgroundColor: colors.surface }]}>
          <View style={styles.header}>
            <Text style={[styles.title, { color: colors.text }]}>Post-workout check-in</Text>
            {!finished && checkIn.total > 0 && (
              <Text style={[styles.meta, { color: colors.muted }]}>
                {Math.min(checkIn.step + 1, checkIn.total)} / {checkIn.total}
              </Text>
            )}
          </View>

          <Text style={[styles.reply, { color: colors.text }]}>{checkIn.reply}</Text>

          {checkIn.notice && (
            <View style={[styles.notice, { backgroundColor: colors.warnSoft }]}>
              <Text style={{ color: colors.warn }}>{checkIn.notice.message}</Text>
            </View>
          )}

          {checkIn.support?.status === 'unavailable' && (
            <Pressable
              onPress={() => send('retry_support')}
              disabled={busy}
              accessibilityRole="button"
              style={[styles.pill, { borderColor: colors.border }]}
            >
              <Text style={{ color: colors.text, fontWeight: '600' }}>Try support again</Text>
            </Pressable>
          )}

          {!finished && question && (
            <QuestionInput
              question={question}
              text={text}
              onTextChange={setText}
              disabled={busy}
              onAnswer={(value) => send('answer', value)}
              onSkip={() => send('skip')}
            />
          )}

          {checkIn.status === 'awaiting_confirmation' && (
            <Pressable
              onPress={() => send('confirm')}
              disabled={busy}
              accessibilityRole="button"
              style={[styles.save, { backgroundColor: busy ? colors.neutralSoft : colors.primary }]}
            >
              <Text style={styles.saveText}>Confirm and save</Text>
            </Pressable>
          )}

          {busy && <ActivityIndicator color={colors.primary} />}
          {error && <Text style={[styles.meta, { color: colors.warn }]}>{error}</Text>}

          <Pressable onPress={() => onClose(finished)} accessibilityRole="button" style={styles.close}>
            <Text style={{ color: colors.muted, fontWeight: '600' }}>{finished ? 'Done' : 'Close for now'}</Text>
          </Pressable>
        </View>
      </View>
    </Modal>
  )
}

function QuestionInput({
  question,
  text,
  onTextChange,
  disabled,
  onAnswer,
  onSkip,
}: {
  question: CheckInQuestion
  text: string
  onTextChange: (value: string) => void
  disabled: boolean
  onAnswer: (value: string) => void
  onSkip: () => void
}) {
  const { colors } = useTheme()

  let input: ReactNode
  if (question.type === 'scale') {
    const min = question.minValue ?? 0
    const max = question.maxValue ?? 10
    const values = Array.from({ length: max - min + 1 }, (_, i) => min + i)
    input = (
      <View style={styles.chips}>
        {values.map((value) => (
          <Pressable
            key={value}
            onPress={() => onAnswer(String(value))}
            disabled={disabled}
            accessibilityRole="button"
            style={[styles.chip, { borderColor: colors.border, backgroundColor: colors.bg }]}
          >
            <Text style={{ color: colors.text, fontWeight: '600', fontVariant: ['tabular-nums'] }}>{value}</Text>
          </Pressable>
        ))}
      </View>
    )
  } else if (question.type === 'choice') {
    input = (
      <View style={styles.chips}>
        {question.options.map((option) => (
          <Pressable
            key={option.value}
            onPress={() => onAnswer(option.value)}
            disabled={disabled}
            accessibilityRole="button"
            style={[styles.pill, { borderColor: colors.border, backgroundColor: colors.bg }]}
          >
            <Text style={{ color: colors.text, fontWeight: '600', fontSize: 13 }}>{option.label}</Text>
          </Pressable>
        ))}
      </View>
    )
  } else {
    input = (
      <View style={styles.textRow}>
        <TextInput
          value={text}
          onChangeText={onTextChange}
          placeholder="Your answer"
          placeholderTextColor={colors.muted}
          editable={!disabled}
          style={[styles.input, { color: colors.text, borderColor: colors.border, backgroundColor: colors.bg }]}
        />
        <Pressable
          onPress={() => text.trim() && onAnswer(text.trim())}
          disabled={disabled || !text.trim()}
          accessibilityRole="button"
          style={[styles.save, { backgroundColor: colors.primary }]}
        >
          <Text style={styles.saveText}>Send</Text>
        </Pressable>
      </View>
    )
  }

  return (
    <View style={styles.group}>
      <Text style={[styles.question, { color: colors.text }]}>{question.text}</Text>
      {input}
      {question.skippable && (
        <Pressable onPress={onSkip} disabled={disabled} accessibilityRole="button" style={styles.skip}>
          <Text style={{ color: colors.muted, fontWeight: '600' }}>Skip</Text>
        </Pressable>
      )}
    </View>
  )
}

const styles = StyleSheet.create({
  backdrop: { flex: 1, justifyContent: 'flex-end', alignItems: 'center', backgroundColor: 'rgba(0,0,0,0.4)' },
  sheet: {
    width: '100%',
    maxWidth: 480,
    maxHeight: '90%',
    borderTopLeftRadius: 24,
    borderTopRightRadius: 24,
    padding: 20,
    gap: 12,
  },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  title: { fontSize: 18, fontWeight: '700' },
  meta: { fontSize: 13 },
  reply: { fontSize: 15, lineHeight: 21 },
  notice: { padding: 12, borderRadius: 12 },
  group: { gap: 10 },
  question: { fontSize: 15, fontWeight: '600' },
  chips: { flexDirection: 'row', flexWrap: 'wrap', gap: 6 },
  chip: { minWidth: 34, height: 34, borderRadius: 8, borderWidth: 1, alignItems: 'center', justifyContent: 'center', paddingHorizontal: 4 },
  pill: { paddingHorizontal: 12, paddingVertical: 8, borderRadius: 999, borderWidth: 1, alignSelf: 'flex-start' },
  textRow: { flexDirection: 'row', gap: 8, alignItems: 'center' },
  input: { flex: 1, borderWidth: 1, borderRadius: 12, paddingHorizontal: 12, paddingVertical: 10, fontSize: 15 },
  save: { paddingHorizontal: 20, paddingVertical: 12, borderRadius: 12, alignItems: 'center' },
  saveText: { color: '#ffffff', fontWeight: '700' },
  skip: { alignSelf: 'flex-start', paddingVertical: 4 },
  close: { alignSelf: 'center', paddingVertical: 8 },
})
