import { Ionicons } from '@expo/vector-icons'
import { useMemo, useState } from 'react'
import { Pressable, StyleSheet, Text, useWindowDimensions, View } from 'react-native'
import { Screen } from '../../components/Screen'
import { WIDE_BREAKPOINT } from '../../lib/layout'
import { buildMonthGrid, formatDayTitle, formatMonthTitle, parseISODate, toISODate } from '../../lib/dates'
import { useTheme } from '../../lib/theme'
import { useTraining } from '../../lib/training'
import { AddWorkoutModal } from './AddWorkoutModal'
import { DayDetails } from './DayDetails'
import { GreetingCard } from './GreetingCard'
import { MonthGrid } from './MonthGrid'

export function CalendarScreen() {
  const { colors } = useTheme()
  const { width } = useWindowDimensions()
  const wide = width >= WIDE_BREAKPOINT
  const { calendar, addWorkout, setWorkoutStatus } = useTraining()

  const today = new Date()
  const [year, setYear] = useState(today.getFullYear())
  const [month, setMonth] = useState(today.getMonth())
  const [selectedISO, setSelectedISO] = useState(toISODate(today))
  const [modalVisible, setModalVisible] = useState(false)

  const cells = useMemo(() => buildMonthGrid(year, month), [year, month])
  const todaysWorkouts = calendar[toISODate(today)]?.workouts ?? []
  const todaysPlanned = todaysWorkouts.filter((w) => w.status === 'planned').length
  const todaysDone = todaysWorkouts.filter((w) => w.status === 'done').length

  function shiftMonth(delta: number) {
    const next = new Date(year, month + delta, 1)
    setYear(next.getFullYear())
    setMonth(next.getMonth())
  }

  return (
    <Screen>
      <GreetingCard now={today} planned={todaysPlanned} done={todaysDone} />
      <View style={[styles.columns, wide && styles.columnsWide]}>
        <View style={[styles.card, { backgroundColor: colors.surface, borderColor: colors.border }, wide && styles.half]}>
          <View style={styles.monthHeader}>
            <Pressable onPress={() => shiftMonth(-1)} accessibilityLabel="Previous month" hitSlop={8}>
              <Ionicons name="chevron-back" size={22} color={colors.text} />
            </Pressable>
            <Text style={[styles.monthTitle, { color: colors.text }]}>{formatMonthTitle(year, month)}</Text>
            <Pressable onPress={() => shiftMonth(1)} accessibilityLabel="Next month" hitSlop={8}>
              <Ionicons name="chevron-forward" size={22} color={colors.text} />
            </Pressable>
          </View>
          <MonthGrid cells={cells} calendar={calendar} selectedISO={selectedISO} onSelect={setSelectedISO} />
        </View>

        <View style={[styles.dayColumn, wide && styles.half]}>
          <Text style={[styles.dayTitle, { color: colors.muted }]}>{formatDayTitle(parseISODate(selectedISO))}</Text>
          <DayDetails
            plan={calendar[selectedISO]}
            onAdd={() => setModalVisible(true)}
            onToggleDone={(workoutId, status) => setWorkoutStatus(selectedISO, workoutId, status)}
          />
        </View>
      </View>

      <AddWorkoutModal
        visible={modalVisible}
        onClose={() => setModalVisible(false)}
        onSubmit={(workout) => addWorkout(selectedISO, workout)}
      />
    </Screen>
  )
}

const styles = StyleSheet.create({
  columns: { gap: 16 },
  columnsWide: { flexDirection: 'row', alignItems: 'flex-start', gap: 24 },
  half: { flex: 1 },
  card: { borderRadius: 24, borderWidth: StyleSheet.hairlineWidth, padding: 16, gap: 16 },
  monthHeader: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  monthTitle: { fontSize: 18, fontWeight: '700' },
  dayColumn: { gap: 12 },
  dayTitle: { fontSize: 14, fontWeight: '600' },
})
