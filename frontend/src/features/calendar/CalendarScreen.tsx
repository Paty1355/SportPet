import { Ionicons } from '@expo/vector-icons'
import { useMemo, useState } from 'react'
import { Pressable, StyleSheet, Text, useWindowDimensions, View } from 'react-native'
import { Screen } from '../../components/Screen'
import { WIDE_BREAKPOINT } from '../../lib/layout'
import { buildMonthGrid, formatDayTitle, formatMonthTitle, parseISODate, toISODate } from '../../lib/dates'
import { useAuth } from '../../lib/auth'
import { useTheme } from '../../lib/theme'
import { useTraining } from '../../lib/training'
import type { WorkoutStatus } from '../../lib/types'
import { CheckInModal } from '../checkin/CheckInModal'
import { markWorkoutDone, type CheckIn } from '../checkin/checkInApi'
import { addPlanToCalendar } from '../plan/planCalendar'
import { fetchPlan, generatePlan } from '../plan/planApi'
import { AddWorkoutModal } from './AddWorkoutModal'
import { DayDetails } from './DayDetails'
import { GreetingCard } from './GreetingCard'
import { MonthGrid } from './MonthGrid'

interface OpenCheckIn {
  checkIn: CheckIn
  // True when the plan had no workouts left after this one. Then the next plan is ours to generate if the check-in is not finished.
  planEmpty: boolean
}

export function CalendarScreen() {
  const { colors } = useTheme()
  const { width } = useWindowDimensions()
  const wide = width >= WIDE_BREAKPOINT
  const { calendar, addWorkout, setWorkoutStatus, setPlan } = useTraining()
  const { token } = useAuth()

  const today = new Date()
  const [year, setYear] = useState(today.getFullYear())
  const [month, setMonth] = useState(today.getMonth())
  const [selectedISO, setSelectedISO] = useState(toISODate(today))
  const [modalVisible, setModalVisible] = useState(false)
  const [openCheckIn, setOpenCheckIn] = useState<OpenCheckIn | null>(null)
  const [notice, setNotice] = useState<string | null>(null)

  const cells = useMemo(() => buildMonthGrid(year, month), [year, month])
  const todaysWorkouts = calendar[toISODate(today)]?.workouts ?? []
  const todaysPlanned = todaysWorkouts.filter((w) => w.status === 'planned').length
  const todaysDone = todaysWorkouts.filter((w) => w.status === 'done').length

  function shiftMonth(delta: number) {
    const next = new Date(year, month + delta, 1)
    setYear(next.getFullYear())
    setMonth(next.getMonth())
  }

  async function toggleDone(workoutId: string, status: WorkoutStatus) {
    const workout = calendar[selectedISO]?.workouts.find((w) => w.id === workoutId)
    if (!workout) return
    // Plan workouts go through the backend, which removes them from the plan and opens a check-in.
    if (status === 'done' && workout.source === 'agent' && token) {
      try {
        const { plan, checkIn } = await markWorkoutDone(token, selectedISO)
        setPlan(plan)
        setWorkoutStatus(selectedISO, workoutId, 'done')
        setOpenCheckIn({ checkIn, planEmpty: plan.workouts.length === 0 })
        setNotice(null)
      } catch (caught) {
        setNotice(caught instanceof Error ? caught.message : 'Could not mark the workout as done')
      }
      return
    }
    setWorkoutStatus(selectedISO, workoutId, status)
  }

  async function finishCheckIn(completed: boolean) {
    const state = openCheckIn
    setOpenCheckIn(null)
    if (!token || !state) return
    try {
      if (completed) {
        // Confirming the last check-in makes the backend build the next plan. Fetch it and show it in the calendar.
        const plan = await fetchPlan(token)
        if (plan) {
          setPlan(plan)
          addPlanToCalendar(plan, calendar, addWorkout)
        }
      } else if (state.planEmpty) {
        // The check-in was left unfinished, so the backend will not build the next plan. Ask for it.
        const plan = await generatePlan(token, toISODate(new Date()))
        setPlan(plan)
        addPlanToCalendar(plan, calendar, addWorkout)
      }
    } catch (caught) {
      setNotice(caught instanceof Error ? caught.message : 'Could not refresh the plan')
    }
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
            onToggleDone={(workoutId, status) => toggleDone(workoutId, status)}
          />
          {notice && <Text style={[styles.notice, { color: colors.warn }]}>{notice}</Text>}
        </View>
      </View>

      <AddWorkoutModal
        visible={modalVisible}
        onClose={() => setModalVisible(false)}
        onSubmit={(workout) => addWorkout(selectedISO, workout)}
      />

      {token && openCheckIn && (
        <CheckInModal token={token} initial={openCheckIn.checkIn} onClose={(completed) => finishCheckIn(completed)} />
      )}
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
  notice: { fontSize: 13 },
})
