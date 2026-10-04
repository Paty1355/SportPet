import { Ionicons } from '@expo/vector-icons'
import { useEffect, useRef, useState } from 'react'
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
import { AiNotice } from '../../components/AiNotice'
import { RichText } from '../../components/RichText'
import { useAuth } from '../../lib/auth'
import { useTheme } from '../../lib/theme'
import { askAgent, fetchQuestionnaire, type AgentKind } from './agentApi'
import type { ProposedExercise, Question, QuestionOption } from './agentTypes'
import { BunAvatar } from './BunAvatar'

type PlanStatus = 'pending' | 'accepted' | 'rejected'

// Fixed colour, so "Send selection" never looks like the theme-coloured option chips, in light or dark mode.
const SUBMIT_COLOR = '#d97706'

// Keeps only the text before the question, so the question is not repeated with its options.
function textBeforeQuestion(reply: string, question: { text: string } | null): string {
  if (!question) return reply.trim()
  const index = reply.indexOf(question.text)
  return (index >= 0 ? reply.slice(0, index) : reply).trim()
}
type ActiveQuestion = Question & { answered: boolean }

type ChatMessage =
  | { id: string; from: 'user'; kind: 'text'; text: string }
  | { id: string; from: 'bot'; kind: 'text'; text: string; question?: ActiveQuestion }
  | { id: string; from: 'bot'; kind: 'plan'; exercises: ProposedExercise[]; status: PlanStatus }

export function TrainingChatScreen({ agent = 'training' }: { agent?: AgentKind }) {
  const { colors } = useTheme()
  const { token } = useAuth()
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [draft, setDraft] = useState('')
  const [busy, setBusy] = useState(false)
  const [selection, setSelection] = useState<string[]>([])
  const scrollRef = useRef<ScrollView>(null)
  const canSend = draft.trim().length > 0 && !busy

  useEffect(() => {
    if (!token) return
    let cancelled = false
    fetchQuestionnaire(token, agent)
      .then((status) => {
        if (cancelled || status.completed || !status.question) return
        const question = status.question
        setMessages((prev) => [
          ...prev,
          { id: `question-${question.key}`, from: 'bot', kind: 'text', text: question.text, question: { ...question, answered: false } },
        ])
      })
      .catch(() => {})
    return () => {
      cancelled = true
    }
  }, [token, agent])

  function append(message: ChatMessage) {
    setMessages((prev) => [...prev, message])
  }

  function setPlanStatus(id: string, status: PlanStatus) {
    setMessages((prev) =>
      prev.map((message) => (message.id === id && message.kind === 'plan' ? { ...message, status } : message)),
    )
  }

  async function send(text: string, display?: string) {
    if (!text.trim() || busy || !token) return
    setDraft('')
    setSelection([])
    setBusy(true)
    setMessages((prev) =>
      prev.map((message) =>
        message.from === 'bot' && message.kind === 'text' && message.question
          ? { ...message, question: { ...message.question, answered: true } }
          : message,
      ),
    )
    append({ id: `user-${Date.now()}`, from: 'user', kind: 'text', text: display ?? text })
    try {
      const reply = await askAgent(token, agent, text)
      if (reply.plan) {
        append({ id: `plan-${Date.now()}`, from: 'bot', kind: 'plan', exercises: reply.plan, status: 'pending' })
      } else {
        // The reply already contains the next question with its numbered options; the question bubble shows them as buttons.
        const lead = textBeforeQuestion(reply.reply, reply.question)
        if (lead) append({ id: `bot-${Date.now()}`, from: 'bot', kind: 'text', text: lead })
        if (reply.question) {
          append({
            id: `question-${reply.question.key}-${Date.now()}`,
            from: 'bot',
            kind: 'text',
            text: reply.question.text,
            question: { ...reply.question, answered: false },
          })
        }
      }
    } catch {
      append({ id: `error-${Date.now()}`, from: 'bot', kind: 'text', text: 'Something went wrong. Please try again.' })
    } finally {
      setBusy(false)
    }
  }

  function pickOption(question: ActiveQuestion, option: QuestionOption) {
    if (!question.multi) {
      send(option.value, option.label)
      return
    }
    setSelection((prev) => (prev.includes(option.value) ? prev.filter((v) => v !== option.value) : [...prev, option.value]))
  }

  function submitSelection(question: ActiveQuestion) {
    const labels = question.options.filter((o) => selection.includes(o.value)).map((o) => o.label)
    send(selection.join(', '), labels.join(', '))
  }

  const activeQuestion = [...messages]
    .reverse()
    .find((m): m is Extract<ChatMessage, { kind: 'text'; from: 'bot' }> & { question: ActiveQuestion } =>
      m.from === 'bot' && m.kind === 'text' && !!m.question && !m.question.answered,
    )?.question

  return (
    // On Android the root view in _layout.tsx makes room for the keyboard; this handles iOS.
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
                onAccept={() => {
                  setPlanStatus(message.id, 'accepted')
                  append({ id: `accepted-${Date.now()}`, from: 'bot', kind: 'text', text: 'Great, plan accepted. Adding it to your calendar comes next.' })
                }}
                onReject={() => {
                  setPlanStatus(message.id, 'rejected')
                  append({ id: `rejected-${Date.now()}`, from: 'bot', kind: 'text', text: 'No problem. Tell me what you would like to change.' })
                }}
              />
            )
          }
          if (message.from === 'bot') {
            return (
              <View key={message.id} style={styles.botBlock}>
                <BotBubble text={message.text} />
                {message.question && !message.question.answered && (
                  <View style={styles.options}>
                    {message.question.options.map((option) => (
                      <OptionChip
                        key={option.value}
                        label={option.label}
                        selected={selection.includes(option.value)}
                        disabled={busy}
                        onPress={() => pickOption(message.question as ActiveQuestion, option)}
                      />
                    ))}
                    {message.question.multi && selection.length > 0 && (
                      <Pressable
                        onPress={() => submitSelection(message.question as ActiveQuestion)}
                        disabled={busy}
                        accessibilityRole="button"
                        style={[styles.submit, { backgroundColor: SUBMIT_COLOR }]}
                      >
                        <Text style={styles.submitText}>Send selection</Text>
                      </Pressable>
                    )}
                  </View>
                )}
              </View>
            )
          }
          return <UserBubble key={message.id} text={message.text} />
        })}
        {busy && <BotBubble text="..." />}
      </ScrollView>

      <AiNotice />

      <View style={[styles.inputBar, { backgroundColor: colors.surface, borderColor: colors.border }]}>
        <TextInput
          value={draft}
          onChangeText={setDraft}
          onSubmitEditing={() => send(draft.trim())}
          placeholder={activeQuestion ? 'Or type your answer...' : agent === 'diet' ? 'Ask your dietitian...' : 'Write to Bun...'}
          placeholderTextColor={colors.muted}
          returnKeyType="send"
          style={[styles.input, { color: colors.text, borderColor: colors.border, backgroundColor: colors.bg }]}
        />
        <Pressable
          onPress={() => send(draft.trim())}
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
            <Pressable onPress={onReject} accessibilityRole="button" style={[styles.actionButton, { borderColor: colors.border }]}>
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

function OptionChip({
  label,
  selected,
  disabled,
  onPress,
}: {
  label: string
  selected: boolean
  disabled: boolean
  onPress: () => void
}) {
  const { colors } = useTheme()
  const [hovered, setHovered] = useState(false)
  const highlighted = selected || hovered

  return (
    <Pressable
      onPress={onPress}
      onHoverIn={() => setHovered(true)}
      onHoverOut={() => setHovered(false)}
      disabled={disabled}
      accessibilityRole="button"
      accessibilityState={{ selected }}
      style={[
        styles.option,
        {
          borderColor: colors.primary,
          backgroundColor: highlighted ? colors.primary : colors.surface,
          transform: [{ scale: hovered && !disabled ? 1.04 : 1 }],
        },
      ]}
    >
      <Text style={[styles.optionText, { color: highlighted ? '#ffffff' : colors.primary }]}>{label}</Text>
    </Pressable>
  )
}

function BotBubble({ text }: { text: string }) {
  const { colors } = useTheme()
  return (
    <View style={styles.botRow}>
      <BunAvatar />
      <View style={[styles.botBubble, { backgroundColor: colors.surface, borderColor: colors.border }]}>
        <RichText text={text} style={styles.botText} color={colors.text} />
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
  botBlock: { gap: 8 },
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
  options: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, paddingLeft: 52 },
  option: { paddingHorizontal: 12, paddingVertical: 8, borderRadius: 999, borderWidth: 1 },
  optionText: { fontSize: 14, fontWeight: '600' },
  submit: { paddingHorizontal: 14, paddingVertical: 8, borderRadius: 999 },
  submitText: { color: '#ffffff', fontSize: 14, fontWeight: '700' },
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
  actionButton: { paddingHorizontal: 16, paddingVertical: 8, borderRadius: 12, borderWidth: 1 },
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
  input: { flex: 1, borderWidth: 1, borderRadius: 999, paddingHorizontal: 14, paddingVertical: 10, fontSize: 15 },
  send: { width: 40, height: 40, borderRadius: 20, alignItems: 'center', justifyContent: 'center' },
})
