import { useEffect, useState } from 'react'
import { ActivityIndicator, Pressable, StyleSheet, Text, View } from 'react-native'
import { Lightbox } from '../../components/Lightbox'
import { Screen } from '../../components/Screen'
import { toISODate } from '../../lib/dates'
import { ApiError } from '../../lib/api'
import { useAuth } from '../../lib/auth'
import { useTheme } from '../../lib/theme'
import { useTraining } from '../../lib/training'
import { addPlanToCalendar } from './planCalendar'
import { fetchPlan, generatePlan, gifSource } from './planApi'

export function PlanScreen() {
  const { colors } = useTheme()
  const { token } = useAuth()
  const { calendar, addWorkout, plan, setPlan } = useTraining()
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [note, setNote] = useState<string | null>(null)

  function addToCalendar() {
    if (!plan) return
    const added = addPlanToCalendar(plan, calendar, addWorkout)
    const hasDates = plan.workouts.some((w) => w.date)
    setNote(
      !hasDates
        ? 'This plan was saved without dates. Generate a new plan to add it to the calendar.'
        : added > 0
          ? `Added ${added} workout${added > 1 ? 's' : ''} to the calendar.`
          : 'These workouts are already in the calendar.',
    )
  }

  useEffect(() => {
    if (!token) return
    let cancelled = false
    fetchPlan(token)
      .then((saved) => {
        if (!cancelled) setPlan(saved)
      })
      .catch((caught) => {
        if (!cancelled) setError(messageOf(caught))
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [token])

  async function generate() {
    if (!token) return
    setBusy(true)
    setError(null)
    try {
      setPlan(await generatePlan(token, toISODate(new Date())))
      setNote(null)
    } catch (caught) {
      if (caught instanceof ApiError && caught.status === 409) {
        setError('Complete the training questionnaire in the Training tab first.')
      } else {
        setError(messageOf(caught))
      }
    } finally {
      setBusy(false)
    }
  }

  return (
    <Screen>
      <View style={[styles.card, { backgroundColor: colors.surface, borderColor: colors.border }]}>
        <Text style={[styles.title, { color: colors.text }]}>Your training plan</Text>
        <Text style={[styles.meta, { color: colors.muted }]}>
          Built from your questionnaire, recent health data and how your workouts felt.
        </Text>
        <Pressable
          onPress={generate}
          disabled={busy}
          accessibilityRole="button"
          style={[styles.button, { backgroundColor: busy ? colors.neutralSoft : colors.primary }]}
        >
          {busy ? (
            <ActivityIndicator color={colors.muted} />
          ) : (
            <Text style={styles.buttonText}>{plan ? 'Generate a new plan' : 'Generate plan'}</Text>
          )}
        </Pressable>
        {plan && (
          <Pressable
            onPress={addToCalendar}
            accessibilityRole="button"
            style={[styles.button, { borderWidth: 1, borderColor: colors.primary, backgroundColor: colors.surface }]}
          >
            <Text style={[styles.buttonText, { color: colors.primary }]}>Add to calendar</Text>
          </Pressable>
        )}
        {note && <Text style={[styles.meta, { color: colors.text }]}>{note}</Text>}
        {busy && <Text style={[styles.meta, { color: colors.muted }]}>This can take up to a minute.</Text>}
        {error && <Text style={[styles.meta, { color: colors.warn }]}>{error}</Text>}
      </View>

      {loading && <ActivityIndicator color={colors.primary} />}

      {plan?.workouts.map((workout) => (
        <View key={workout.day} style={[styles.card, { backgroundColor: colors.surface, borderColor: colors.border }]}>
          <Text style={[styles.meta, { color: colors.primary, fontWeight: '700' }]}>{workout.date ?? workout.day}</Text>
          <Text style={[styles.title, { color: colors.text }]}>{workout.focus}</Text>
          {workout.exercises.map((exercise) => (
            <View key={exercise.title} style={[styles.exercise, { borderColor: colors.border }]}>
              <Lightbox uri={gifSource(exercise.gifUrl)} style={styles.gif} caption={exercise.title} />
              <View style={styles.exerciseText}>
                <Text style={[styles.exerciseTitle, { color: colors.text }]}>{exercise.title}</Text>
                <Text style={[styles.meta, { color: colors.muted }]}>
                  {exercise.sets}×{exercise.reps} · {exercise.estimatedTimeMinutes} min
                </Text>
                {exercise.description ? (
                  <Text style={[styles.meta, { color: colors.text }]}>{exercise.description}</Text>
                ) : null}
              </View>
            </View>
          ))}
        </View>
      ))}
    </Screen>
  )
}

function messageOf(caught: unknown): string {
  return caught instanceof Error ? caught.message : 'Something went wrong'
}

const styles = StyleSheet.create({
  card: { borderRadius: 24, borderWidth: StyleSheet.hairlineWidth, padding: 18, gap: 10 },
  title: { fontSize: 16, fontWeight: '700' },
  meta: { fontSize: 13 },
  button: { paddingVertical: 12, borderRadius: 12, alignItems: 'center' },
  buttonText: { color: '#ffffff', fontSize: 15, fontWeight: '700' },
  exercise: { flexDirection: 'row', gap: 12, paddingTop: 10, borderTopWidth: StyleSheet.hairlineWidth },
  gif: { width: 88, height: 88, borderRadius: 12, backgroundColor: '#00000010' },
  exerciseText: { flex: 1, gap: 4 },
  exerciseTitle: { fontSize: 15, fontWeight: '600' },
})
