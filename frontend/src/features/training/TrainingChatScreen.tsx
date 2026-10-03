import { Ionicons } from '@expo/vector-icons'
import { useRef, useState } from 'react'
import {
  KeyboardAvoidingView,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native'
import { useTheme } from '../../lib/theme'
import { askTrainingAgent } from './agentApi'
import type { ProposedExercise } from './agentTypes'
import { BunAvatar } from './BunAvatar'

type PlanStatus = 'pending' | 'accepted' | 'rejected'

type ChatMessage =
  | { id: string; from: 'user'; kind: 'text'; text: string }
  | { id: string; from: 'bot'; kind: 'text'; text: string }
  | { id: string; from: 'bot'; kind: 'plan'; exercises: ProposedExercise[]; status: PlanStatus }

const GREETING: ChatMessage = {
  id: 'greeting',
  from: 'bot',
  kind: 'text',
  text: "Hi! I'm Bun, your training buddy. Tell me about your goals and I'll put together a plan for you.",
}

export function TrainingChatScreen() {
  const { colors } = useTheme()
  const [messages, setMessages] = useState<ChatMessage[]>([GREETING])
  const [draft, setDraft] = useState('')
  const [busy, setBusy] = useState(false)
  const scrollRef = useRef<ScrollView>(null)
  const canSend = draft.trim().length > 0 && !busy

  function append(message: ChatMessage) {
    setMessages((prev) => [...prev, message])
  }

  function setPlanStatus(id: string, status: PlanStatus) {
    setMessages((prev) =>
      prev.map((message) => (message.id === id && message.kind === 'plan' ? { ...message, status } : message)),
    )
  }

  async function send() {
    const text = draft.trim()
    if (!text || busy) return
    setDraft('')
    setBusy(true)
    append({ id: `user-${Date.now()}`, from: 'user', kind: 'text', text })
    try {
      const reply = await askTrainingAgent(text)
      if (reply.type === 'plan') {
        append({ id: `plan-${Date.now()}`, from: 'bot', kind: 'plan', exercises: reply.exercises, status: 'pending' })
      } else {
        append({ id: `bot-${Date.now()}`, from: 'bot', kind: 'text', text: reply.text })
      }
    } catch {
      append({ id: `error-${Date.now()}`, from: 'bot', kind: 'text', text: 'Something went wrong. Please try again.' })
    } finally {
      setBusy(false)
    }
  }

  function accept(id: string) {
    setPlanStatus(id, 'accepted')
    append({
      id: `accepted-${Date.now()}`,
      from: 'bot',
      kind: 'text',
      text: 'Great, plan accepted. Adding it to your calendar comes next.',
    })
  }

  function reject(id: string) {
    setPlanStatus(id, 'rejected')
    append({
      id: `rejected-${Date.now()}`,
      from: 'bot',
      kind: 'text',
      text: 'No problem. Tell me what you would like to change.',
    })
  }

  return (
    <KeyboardAvoidingView style={styles.root} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
      <ScrollView
        ref={scrollRef}
        style={styles.list}
        contentContainerStyle={styles.listContent}
        onContentSizeChange={() => scrollRef.current?.scrollToEnd({ animated: true })}
        keyboardShouldPersistTaps="handled"
      >
        {messages.map((message) => {
          if (message.kind === 'plan') {
            return (
              <PlanCard
                key={message.id}
                exercises={message.exercises}
                status={message.status}
                onAccept={() => accept(message.id)}
                onReject={() => reject(message.id)}
              />
            )
          }
          return message.from === 'bot' ? (
            <BotBubble key={message.id} text={message.text} />
          ) : (
            <UserBubble key={message.id} text={message.text} />
          )
        })}
        {busy && <BotBubble text="..." />}
      </ScrollView>

      <View style={[styles.inputBar, { backgroundColor: colors.surface, borderColor: colors.border }]}>
        <TextInput
          value={draft}
          onChangeText={setDraft}
          onSubmitEditing={send}
          placeholder="Write to Bun..."
          placeholderTextColor={colors.muted}
          returnKeyType="send"
          style={[styles.input, { color: colors.text, borderColor: colors.border, backgroundColor: colors.bg }]}
        />
        <Pressable
          onPress={send}
          disabled={!canSend}
          accessibilityRole="button"
          accessibilityLabel="Send"
          style={[styles.send, { backgroundColor: canSend ? colors.primary : colors.neutralSoft }]}
        >
          <Ionicons name="arrow-up" size={18} color={canSend ? '#ffffff' : colors.muted} />
        </Pressable>
      </View>
    </KeyboardAvoidingView>
  )
}

function PlanCard({
  exercises,
  status,
  onAccept,
  onReject,
}: {
  exercises: ProposedExercise[]
  status: PlanStatus
  onAccept: () => void
  onReject: () => void
}) {
  const { colors } = useTheme()
  const totalMinutes = exercises.reduce((sum, exercise) => sum + exercise.estimatedTimeMinutes, 0)
  const pending = status === 'pending'

  return (
    <View style={styles.botRow}>
      <BunAvatar />
      <View style={[styles.planCard, { backgroundColor: colors.surface, borderColor: colors.border }]}>
        <Text style={[styles.planTitle, { color: colors.text }]}>Your plan · about {totalMinutes} min</Text>

        {exercises.map((exercise) => (
          <View key={exercise.title} style={[styles.exercise, { borderColor: colors.border }]}>
            <View style={styles.exerciseHead}>
              <Text style={[styles.exerciseName, { color: colors.text }]}>{exercise.title}</Text>
              <Text style={[styles.exerciseMeta, { color: colors.primary }]}>
                {exercise.sets}×{exercise.reps} · {exercise.estimatedTimeMinutes} min
              </Text>
            </View>
            <Text style={[styles.exerciseDescription, { color: colors.muted }]}>{exercise.description}</Text>
          </View>
        ))}

        {pending ? (
          <View style={styles.actions}>
            <Pressable
              onPress={onReject}
              accessibilityRole="button"
              style={[styles.actionButton, { borderColor: colors.border }]}
            >
              <Text style={[styles.actionText, { color: colors.muted }]}>Change</Text>
            </Pressable>
            <Pressable
              onPress={onAccept}
              accessibilityRole="button"
              style={[styles.actionButton, { backgroundColor: colors.primary, borderColor: colors.primary }]}
            >
              <Text style={[styles.actionText, { color: '#ffffff' }]}>Accept</Text>
            </Pressable>
          </View>
        ) : (
          <Text style={[styles.statusText, { color: status === 'accepted' ? colors.success : colors.muted }]}>
            {status === 'accepted' ? 'Accepted' : 'Changed'}
          </Text>
        )}
      </View>
    </View>
  )
}

function BotBubble({ text }: { text: string }) {
  const { colors } = useTheme()
  return (
    <View style={styles.botRow}>
      <BunAvatar />
      <View style={[styles.botBubble, { backgroundColor: colors.surface, borderColor: colors.border }]}>
        <Text style={[styles.botText, { color: colors.text }]}>{text}</Text>
      </View>
    </View>
  )
}

function UserBubble({ text }: { text: string }) {
  const { colors } = useTheme()
  return (
    <View style={[styles.userBubble, { backgroundColor: colors.primary }]}>
      <Text style={styles.userText}>{text}</Text>
    </View>
  )
}

const styles = StyleSheet.create({
  root: { flex: 1, width: '100%', maxWidth: 800, alignSelf: 'center', paddingHorizontal: 16 },
  list: { flex: 1 },
  listContent: { paddingTop: 16, paddingBottom: 12, gap: 12 },
  botRow: { flexDirection: 'row', alignItems: 'flex-end', gap: 8, maxWidth: '92%' },
  botBubble: {
    flexShrink: 1,
    borderRadius: 18,
    borderBottomLeftRadius: 6,
    borderWidth: StyleSheet.hairlineWidth,
    paddingHorizontal: 14,
    paddingVertical: 10,
  },
  botText: { fontSize: 15, lineHeight: 21 },
  planCard: {
    flex: 1,
    borderRadius: 18,
    borderBottomLeftRadius: 6,
    borderWidth: StyleSheet.hairlineWidth,
    padding: 14,
    gap: 10,
  },
  planTitle: { fontSize: 15, fontWeight: '700' },
  exercise: { borderTopWidth: StyleSheet.hairlineWidth, paddingTop: 10, gap: 4 },
  exerciseHead: { flexDirection: 'row', justifyContent: 'space-between', gap: 8, alignItems: 'center' },
  exerciseName: { fontSize: 15, fontWeight: '700', flex: 1 },
  exerciseMeta: { fontSize: 13, fontWeight: '700' },
  exerciseDescription: { fontSize: 13, lineHeight: 18 },
  actions: { flexDirection: 'row', justifyContent: 'flex-end', gap: 8, marginTop: 4 },
  actionButton: {
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 12,
    borderWidth: 1,
  },
  actionText: { fontSize: 14, fontWeight: '700' },
  statusText: { fontSize: 13, fontWeight: '700', marginTop: 4 },
  userBubble: {
    alignSelf: 'flex-end',
    maxWidth: '80%',
    borderRadius: 18,
    borderBottomRightRadius: 6,
    paddingHorizontal: 14,
    paddingVertical: 10,
  },
  userText: { color: '#ffffff', fontSize: 15, lineHeight: 21 },
  inputBar: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    padding: 10,
    marginBottom: 12,
    borderRadius: 999,
    borderWidth: StyleSheet.hairlineWidth,
  },
  input: {
    flex: 1,
    borderWidth: 1,
    borderRadius: 999,
    paddingHorizontal: 14,
    paddingVertical: 10,
    fontSize: 15,
  },
  send: { width: 40, height: 40, borderRadius: 20, alignItems: 'center', justifyContent: 'center' },
})
