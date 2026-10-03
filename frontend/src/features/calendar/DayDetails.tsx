import { Ionicons } from '@expo/vector-icons'
import { Pressable, StyleSheet, Text, View } from 'react-native'
import type { DayPlan, Workout, WorkoutStatus } from '../../lib/types'
import { useTheme, type Palette } from '../../lib/theme'

const STATUS_LABEL: Record<WorkoutStatus, string> = {
  planned: 'Planned',
  done: 'Done',
  skipped: 'Skipped',
}

function statusColors(status: WorkoutStatus, colors: Palette) {
  if (status === 'done') return { bg: colors.successSoft, fg: colors.success }
  if (status === 'skipped') return { bg: colors.neutralSoft, fg: colors.neutral }
  return { bg: colors.primarySoft, fg: colors.primary }
}

interface DayDetailsProps {
  plan: DayPlan | undefined
  onAdd: () => void
  onToggleDone: (workoutId: string, status: WorkoutStatus) => void
}

export function DayDetails({ plan, onAdd, onToggleDone }: DayDetailsProps) {
  const { colors } = useTheme()
  const workouts = plan?.workouts ?? []

  return (
    <View style={styles.wrapper}>
      <View style={styles.header}>
        <Text style={[styles.heading, { color: colors.text }]}>Workouts this day</Text>
        <Pressable
          onPress={onAdd}
          accessibilityRole="button"
          style={[styles.addButton, { backgroundColor: colors.primary }]}
        >
          <Text style={styles.addText}>Add workout</Text>
        </Pressable>
      </View>

      {workouts.length === 0 ? (
        <View style={[styles.empty, { borderColor: colors.border }]}>
          <Text style={{ color: colors.muted, textAlign: 'center' }}>
            No workouts yet. Add one or ask the agent for a plan.
          </Text>
        </View>
      ) : (
        workouts.map((workout) => (
          <WorkoutCard key={workout.id} workout={workout} onToggleDone={onToggleDone} />
        ))
      )}
    </View>
  )
}

function WorkoutCard({
  workout,
  onToggleDone,
}: {
  workout: Workout
  onToggleDone: (workoutId: string, status: WorkoutStatus) => void
}) {
  const { colors } = useTheme()
  const badge = statusColors(workout.status, colors)
  const isDone = workout.status === 'done'

  return (
    <View style={[styles.card, { backgroundColor: colors.surface, borderColor: colors.border }]}>
      <View style={styles.cardTop}>
        <View style={{ flex: 1 }}>
          <Text style={[styles.cardTitle, { color: colors.text }]}>{workout.title}</Text>
          <Text style={[styles.cardMeta, { color: colors.muted }]}>
            {workout.startTime} · {workout.durationMin} min · {workout.source === 'agent' ? 'by agent' : 'manual'}
          </Text>
        </View>
        <View style={[styles.badge, { backgroundColor: badge.bg }]}>
          <Text style={[styles.badgeText, { color: badge.fg }]}>{STATUS_LABEL[workout.status]}</Text>
        </View>
      </View>

      {workout.exercises.length > 0 && (
        <View style={styles.exercises}>
          {workout.exercises.map((exercise) => (
            <View key={exercise.name} style={styles.exerciseRow}>
              <Text style={{ color: colors.text, flex: 1 }}>{exercise.name}</Text>
              <Text style={{ color: colors.muted, fontVariant: ['tabular-nums'] }}>
                {exercise.sets}×{exercise.reps}
                {exercise.weightKg !== null ? ` · ${exercise.weightKg} kg` : ''}
              </Text>
            </View>
          ))}
        </View>
      )}

      <Pressable
        onPress={() => onToggleDone(workout.id, isDone ? 'planned' : 'done')}
        accessibilityRole="checkbox"
        accessibilityState={{ checked: isDone }}
        style={[styles.doneButton, { borderColor: colors.border }]}
      >
        <Ionicons
          name={isDone ? 'checkmark-circle' : 'ellipse-outline'}
          size={20}
          color={isDone ? colors.success : colors.muted}
        />
        <Text style={{ color: colors.text, fontWeight: '600' }}>{isDone ? 'Completed' : 'Mark as done'}</Text>
      </Pressable>
    </View>
  )
}

const styles = StyleSheet.create({
  wrapper: { gap: 12 },
  header: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  heading: { fontSize: 15, fontWeight: '700' },
  addButton: { paddingHorizontal: 12, paddingVertical: 8, borderRadius: 10 },
  addText: { color: '#ffffff', fontSize: 14, fontWeight: '600' },
  empty: { borderWidth: 1, borderStyle: 'dashed', borderRadius: 16, padding: 16 },
  card: { borderRadius: 16, borderWidth: StyleSheet.hairlineWidth, padding: 16, gap: 12 },
  cardTop: { flexDirection: 'row', alignItems: 'flex-start', gap: 8 },
  cardTitle: { fontSize: 16, fontWeight: '700' },
  cardMeta: { fontSize: 13, marginTop: 2 },
  badge: { paddingHorizontal: 8, paddingVertical: 2, borderRadius: 999 },
  badgeText: { fontSize: 12, fontWeight: '600' },
  exercises: { gap: 6 },
  exerciseRow: { flexDirection: 'row', justifyContent: 'space-between', gap: 8 },
  doneButton: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    paddingTop: 12,
    borderTopWidth: StyleSheet.hairlineWidth,
  },
})
